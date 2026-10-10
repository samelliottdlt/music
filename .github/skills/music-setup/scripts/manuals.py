#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf>=1.24", "pyyaml>=6"]
# ///
"""Official manuals for Sam's gear: list, fetch, check, search and cite them.

The registry of official links is gear/manuals.yaml. Files are downloaded on
demand into a cache OUTSIDE the repo (~/.cache/music-manuals, override with
MUSIC_MANUALS_CACHE) and are never committed.

  uv run .github/skills/music-setup/scripts/manuals.py list
  uv run .github/skills/music-setup/scripts/manuals.py fetch <manual-id|gear-id|all> [--refresh]
  uv run .github/skills/music-setup/scripts/manuals.py check [manual-id|gear-id ...]
  uv run .github/skills/music-setup/scripts/manuals.py search <manual-id|gear-id|all> "terms"
  uv run .github/skills/music-setup/scripts/manuals.py text <manual-id> <page>

Statuses: OK; NEW (entry has no `verified` block yet); CHANGED (the file at the
official URL differs from the verified one); NEWER (the vendor publishes a
newer version); MOVED (the link redirects); BROKEN (dead link, not a PDF, or
the discovery page/pattern stopped working).
Exit codes: 0 ok, 1 usage/registry error, 2 something is BROKEN, 3 drift
(NEW/CHANGED/NEWER/MOVED). On 2 or 3: tell Sam and update gear/manuals.yaml.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]  # .github/skills/music-setup/scripts -> repo root
REGISTRY_PATH = REPO_ROOT / "gear" / "manuals.yaml"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 60
REVALIDATE_AFTER = dt.timedelta(days=7)
KINDS = ("pdf", "image-guide", "web")
METHODS = ("te-assets", "link", "text-version", "none")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEVERITY = {"OK": 0, "NEW": 1, "MOVED": 2, "NEWER": 3, "CHANGED": 4, "BROKEN": 5}
EXIT_OK, EXIT_USAGE, EXIT_BROKEN, EXIT_DRIFT = 0, 1, 2, 3


class RegistryError(Exception):
    """gear/manuals.yaml is missing or malformed, or a target id is unknown."""


class FetchError(Exception):
    def __init__(self, url: str, reason: str, status: int | None = None):
        super().__init__(f"{reason}: {url}")
        self.url, self.reason, self.status = url, reason, status


def out(*parts: object) -> None:
    print(*parts, flush=True)


def note(*parts: object) -> None:
    print(*parts, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- time/text --

def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t: dt.datetime) -> str:
    return t.isoformat().replace("+00:00", "Z")


def parse_iso(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def ago(stamp: str | None) -> str:
    try:
        secs = (now_utc() - parse_iso(stamp)).total_seconds()
    except (TypeError, ValueError):
        return "at an unknown time"
    if secs < 90:
        return "just now"
    if secs < 5400:
        return f"{secs / 60:.0f} min ago"
    if secs < 129600:
        return f"{secs / 3600:.0f} h ago"
    return f"{secs / 86400:.0f} days ago"


_FOLD = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
                       "\u2015": "-", "\u2212": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"',
                       "\u201d": '"', "\u00a0": " "})


def norm(text: str) -> str:
    """NFKC (expands ligatures like 'ﬁ') and fold dashes/quotes so 'OP-XY' finds 'OP–XY'."""
    return unicodedata.normalize("NFKC", text).translate(_FOLD)


def natural_key(s: str) -> list:
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.split(r"(\d+)", str(s)) if p]


def html_to_text(page_html: str) -> str:
    t = re.sub(r"(?is)<(script|style|svg|noscript|template|head)\b.*?</\1\s*>", " ", page_html)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|td|th|section|article|header|footer|ul|ol|table|blockquote)\s*>",
               "\n", t)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t))
    lines: list[str] = []
    for line in t.splitlines():
        line = " ".join(line.split())
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return "\n".join(lines)


def same_url(a: str, b: str) -> bool:
    def key(u: str) -> str:
        u = urllib.parse.unquote(html.unescape(u.strip()))
        u = re.sub(r"^https?://", "", u, flags=re.I)
        host, _, rest = u.partition("/")
        return host.lower() + "/" + rest.rstrip("/")
    return key(a) == key(b)


# ----------------------------------------------------------------- registry --

def registry_path(override: str | None = None) -> Path:
    if override:
        return Path(override)
    if os.environ.get("MUSIC_MANUALS_REGISTRY"):
        return Path(os.environ["MUSIC_MANUALS_REGISTRY"])
    if REGISTRY_PATH.exists():
        return REGISTRY_PATH
    for d in [Path.cwd(), *Path.cwd().parents]:
        if (d / "gear" / "manuals.yaml").exists():
            return d / "gear" / "manuals.yaml"
    return REGISTRY_PATH


def gear_of(entry: dict) -> list[str]:
    g = entry.get("gear")
    return [g] if isinstance(g, str) else [str(x) for x in (g or [])]


def short(entry: dict) -> str:
    return entry.get("short") or entry["title"]


def inventory_ids(reg: Path) -> set[str] | None:
    inv = reg.parent / "inventory.yaml"
    if not inv.exists():
        return None
    data = yaml.safe_load(inv.read_text(encoding="utf-8")) or {}
    return {g["id"] for g in data.get("gear", []) if isinstance(g, dict) and "id" in g}


def validate(entries: list, known_gear: set[str] | None) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            problems.append(f"manuals[{i}]: not a mapping")
            continue
        mid = e.get("id")
        where = f"manuals[{i}] ({mid})"
        if not isinstance(mid, str) or not ID_RE.match(mid):
            problems.append(f"{where}: id must be kebab-case")
        elif mid in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(str(mid))
        gear = gear_of(e)
        if not gear:
            problems.append(f"{where}: gear is required")
        for g in gear if known_gear is not None else []:
            if g not in known_gear:
                problems.append(f"{where}: gear {g!r} is not an id in gear/inventory.yaml")
        required = ("title", "publisher", "url") + (("version",) if e.get("kind") != "web" else ())
        for k in required:
            if not isinstance(e.get(k), (str, int, float)) or not str(e[k]).strip():
                problems.append(f"{where}: {k} is required")
        if e.get("kind") not in KINDS:
            problems.append(f"{where}: kind must be one of {', '.join(KINDS)}")
        if isinstance(e.get("url"), str) and not e["url"].startswith("https://"):
            problems.append(f"{where}: url must start with https://")
        disc = e.get("discover") or {"method": "none"}
        if not isinstance(disc, dict) or disc.get("method") not in METHODS:
            problems.append(f"{where}: discover.method must be one of {', '.join(METHODS)}")
        else:
            m = disc["method"]
            if m in ("te-assets", "link") and not disc.get("page"):
                problems.append(f"{where}: discover.page is required for method {m}")
            if m != "none" and not disc.get("match"):
                problems.append(f"{where}: discover.match is required for method {m}")
            elif m != "none":
                try:
                    re.compile(disc["match"])
                except re.error as x:
                    problems.append(f"{where}: discover.match is not a valid regex ({x})")
        if e.get("kind") == "image-guide":
            pi = e.get("page_images") or {}
            for k in ("list", "image", "thumb"):
                if not pi.get(k):
                    problems.append(f"{where}: page_images.{k} is required for image guides")
        if e.get("verified") is not None and not isinstance(e["verified"], dict):
            problems.append(f"{where}: verified must be a mapping")
    return problems


def load_registry(path: str | None = None) -> list[dict]:
    reg = registry_path(path)
    if not reg.exists():
        raise RegistryError(f"registry not found: {reg}")
    try:
        data = yaml.safe_load(reg.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise RegistryError(f"{reg} is not valid YAML: {e}") from None
    entries = data.get("manuals") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise RegistryError(f"{reg}: expected a top-level `manuals:` list")
    problems = validate(entries, inventory_ids(reg))
    if problems:
        raise RegistryError(f"{reg} has problems:\n  " + "\n  ".join(problems))
    return entries


def resolve(entries: list[dict], targets: list[str] | None) -> list[dict]:
    targets = [t for t in (targets or []) if t]
    if not targets or "all" in targets:
        return list(entries)
    picked: list[dict] = []
    for t in targets:
        hits = [e for e in entries if e["id"] == t] or [e for e in entries if t in gear_of(e)]
        if not hits:
            gear = sorted({g for e in entries for g in gear_of(e)})
            raise RegistryError(f"unknown manual or gear id {t!r}\n  manual ids: "
                                + ", ".join(e["id"] for e in entries) + "\n  gear ids: " + ", ".join(gear))
        picked += [h for h in hits if h not in picked]
    return picked


def resolve_one(entries: list[dict], target: str) -> dict:
    hits = resolve(entries, [target])
    if len(hits) > 1:
        raise RegistryError(f"{target!r} matches several manuals: {', '.join(e['id'] for e in hits)}; "
                            "pass a manual id")
    return hits[0]


# --------------------------------------------------------------------- http --

class _RedirectRecorder(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        self.chain: list[tuple[int, str]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        self.chain.append((code, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url: str, headers: dict | None = None):
    """GET url -> (response, redirect chain). A 304 comes back as a response whose .code is 304."""
    rec = _RedirectRecorder()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*",
                                               "Accept-Language": "en", **(headers or {})})
    try:
        resp = urllib.request.build_opener(rec).open(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return e, rec.chain
        e.close()
        raise FetchError(url, f"HTTP {e.code} {e.reason}", e.code) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FetchError(url, f"network error ({getattr(e, 'reason', e)})") from None
    return resp, rec.chain


def get_html(url: str) -> tuple[str, str, list]:
    resp, chain = open_url(url, {"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
    with resp:
        try:
            raw = resp.read()
        except (OSError, TimeoutError) as e:
            raise FetchError(url, f"network error ({e})") from None
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace"), resp.geturl(), chain


_PAGES: dict[str, tuple[str, str, list]] = {}


def get_html_cached(url: str) -> tuple[str, str, list]:
    """Fetch an HTML page once per run (check and discovery often need the same page)."""
    if url not in _PAGES:
        _PAGES[url] = get_html(url)
    return _PAGES[url]


def probe(url: str) -> dict:
    """Request url but read only the first bytes: redirects, validators, magic."""
    resp, chain = open_url(url)
    with resp:
        try:
            head = resp.read(2048)
        except (OSError, TimeoutError) as e:
            raise FetchError(url, f"network error ({e})") from None
        length = resp.headers.get("Content-Length")
        return {"final_url": resp.geturl(), "redirects": chain, "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "content_type": resp.headers.get("Content-Type", ""),
                "length": int(length) if length and length.isdigit() else None, "head": head}


def download(url: str, dest: Path, headers: dict | None = None, expect_pdf: bool = True) -> dict | None:
    """Stream url into dest atomically. Returns metadata, or None on 304 Not Modified."""
    resp, chain = open_url(url, headers)
    if getattr(resp, "code", None) == 304 or getattr(resp, "status", None) == 304:
        resp.close()
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest, size, head = hashlib.sha256(), 0, b""
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as f, resp:
            while True:
                try:
                    chunk = resp.read(1 << 20)
                except (OSError, TimeoutError) as e:
                    raise FetchError(url, f"download interrupted ({e})") from None
                if not chunk:
                    break
                if len(head) < 1024:
                    head += chunk[: 1024 - len(head)]
                f.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        ctype = resp.headers.get("Content-Type", "")
        expected = resp.headers.get("Content-Length")
        if expected and expected.isdigit() and int(expected) != size:
            raise FetchError(url, f"truncated download ({size} of {expected} bytes)")
        if expect_pdf and b"%PDF-" not in head:
            raise FetchError(url, f"not a PDF (Content-Type {ctype or '?'}, starts with {head[:24]!r})")
        os.replace(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return {"final_url": resp.geturl(), "redirects": [list(c) for c in chain],
            "etag": resp.headers.get("ETag"), "last_modified": resp.headers.get("Last-Modified"),
            "content_type": ctype, "sha256": digest.hexdigest(), "bytes": size}


# ------------------------------------------------------------------- cache --

def cache_dir() -> Path:
    d = Path(os.environ.get("MUSIC_MANUALS_CACHE") or (Path.home() / ".cache" / "music-manuals")).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def cpath(entry: dict, suffix: str) -> Path:
    return cache_dir() / f"{entry['id']}{suffix}"


def read_meta(entry: dict) -> dict | None:
    try:
        return json.loads(cpath(entry, ".json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_meta(entry: dict, meta: dict) -> None:
    p = cpath(entry, ".json")
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def _fresh(meta: dict) -> bool:
    try:
        return now_utc() - parse_iso(meta["validated"]) < REVALIDATE_AFTER
    except (KeyError, TypeError, ValueError):
        return False


@dataclass
class Cached:
    entry: dict
    path: Path
    meta: dict
    how: str
    warning: str | None = None


def ensure(entry: dict, refresh: bool = False) -> Cached:
    """Make sure the manual is in the local cache (revalidated weekly) and say where it is."""
    return {"pdf": _ensure_pdf, "image-guide": _ensure_image_guide, "web": _ensure_web}[entry["kind"]](
        entry, refresh)


def _offline(entry: dict, path: Path, meta: dict, e: FetchError) -> Cached:
    return Cached(entry, path, meta, "cached", warning=(
        f"couldn't reach the official URL ({e.reason}); using the copy cached {ago(meta.get('fetched'))}"))


def _ensure_pdf(entry: dict, refresh: bool) -> Cached:
    path, meta = cpath(entry, ".pdf"), read_meta(entry)
    usable = bool(meta) and path.exists() and meta.get("url") == entry["url"] and "sha256" in meta
    if usable and not refresh and _fresh(meta):
        return Cached(entry, path, meta, f"cached, checked upstream {ago(meta.get('validated'))}")
    headers = {}
    if usable and not refresh:
        if meta.get("etag"):
            headers["If-None-Match"] = meta["etag"]
        if meta.get("last_modified"):
            headers["If-Modified-Since"] = meta["last_modified"]
    note(f"… fetching {entry['id']} from {entry['url']}")
    try:
        got = download(entry["url"], path, headers)
    except FetchError as e:
        if usable:
            return _offline(entry, path, meta, e)
        raise
    stamp = iso(now_utc())
    if got is None:
        meta["validated"] = stamp
        write_meta(entry, meta)
        return Cached(entry, path, meta, "cached, not modified upstream")
    got.update(pdf_info(path))
    meta = {"url": entry["url"], **got, "fetched": stamp, "validated": stamp}
    write_meta(entry, meta)
    return Cached(entry, path, meta, "downloaded")


def pdf_info(path: Path) -> dict:
    with pymupdf.open(path) as doc:
        pages, title = doc.page_count, ((doc.metadata or {}).get("title") or "").strip()
    # many vendor PDFs carry a file name as their "title" (e.g. "TU-3_ejgfispd", "x.indd"); drop those
    if re.search(r"(^file:|[\\/]|\.(jpe?g|png|tiff?|indd|ai|pdf|docx?|qxd)$)", title, re.I) or (
            "_" in title and " " not in title):
        title = ""
    return {"pages": pages, "doc_title": title}


def page_image_ids(entry: dict, page_html: str) -> list[str]:
    rx = re.compile(entry["page_images"]["list"])
    return list(dict.fromkeys(m.group(1) if rx.groups else m.group(0) for m in rx.finditer(page_html)))


def ids_hash(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode()).hexdigest()


def page_image_url(entry: dict, image_id: str, which: str = "image") -> str:
    return entry["page_images"][which].format(id=image_id)


def _ensure_image_guide(entry: dict, refresh: bool) -> Cached:
    folder, meta = cache_dir() / entry["id"], read_meta(entry)
    usable = bool(meta) and meta.get("url") == entry["url"] and bool(meta.get("ids"))
    if usable and not refresh and _fresh(meta):
        return Cached(entry, folder, meta, f"cached page list, checked upstream {ago(meta.get('validated'))}")
    note(f"… fetching {entry['id']} page list from {entry['url']}")
    try:
        page_html, final, chain = get_html_cached(entry["url"])
    except FetchError as e:
        if usable:
            return _offline(entry, folder, meta, e)
        raise
    ids = page_image_ids(entry, page_html)
    if not ids:
        raise FetchError(entry["url"], "no page images found on the guide page "
                                       "(layout changed? fix page_images.list in gear/manuals.yaml)")
    stamp = iso(now_utc())
    meta = {"url": entry["url"], "final_url": final, "redirects": [list(c) for c in chain], "ids": ids,
            "pages": len(ids), "ids_sha256": ids_hash(ids), "fetched": stamp, "validated": stamp}
    write_meta(entry, meta)
    return Cached(entry, folder, meta, "downloaded page list")


def _ensure_web(entry: dict, refresh: bool) -> Cached:
    path, meta = cpath(entry, ".txt"), read_meta(entry)
    usable = bool(meta) and path.exists() and meta.get("url") == entry["url"]
    if usable and not refresh and _fresh(meta):
        return Cached(entry, path, meta, f"cached page text, checked upstream {ago(meta.get('validated'))}")
    note(f"… fetching {entry['id']} from {entry['url']}")
    try:
        page_html, final, chain = get_html_cached(entry["url"])
    except FetchError as e:
        if usable:
            return _offline(entry, path, meta, e)
        raise
    text = html_to_text(page_html)
    path.write_text(text, encoding="utf-8")
    stamp = iso(now_utc())
    meta = {"url": entry["url"], "final_url": final, "redirects": [list(c) for c in chain],
            "chars": len(text), "fetched": stamp, "validated": stamp}
    write_meta(entry, meta)
    return Cached(entry, path, meta, "downloaded page text")


# ----------------------------------------------------------------- findings --

@dataclass
class Finding:
    status: str
    lines: list[str] = field(default_factory=list)
    updates: dict = field(default_factory=dict)


def verified_block(meta: dict, kind: str) -> dict:
    v: dict = {"date": dt.date.today()}
    if kind == "pdf":
        v.update(sha256=meta["sha256"], bytes=meta["bytes"], pages=meta["pages"])
        if meta.get("etag"):
            v["etag"] = meta["etag"]
        if meta.get("last_modified"):
            v["last_modified"] = meta["last_modified"]
    elif kind == "image-guide":
        v.update(pages=meta["pages"], ids_sha256=meta["ids_sha256"])
    return v


def compare(entry: dict, c: Cached) -> list[Finding]:
    """Compare what's in the cache (= what the official URL serves) with the registry."""
    kind, ver, found = entry["kind"], entry.get("verified") or {}, []
    if c.meta.get("redirects"):
        found.append(Finding("MOVED", [f"{entry['url']} now redirects to {c.meta['final_url']}"],
                             {"url": c.meta["final_url"]}))
    key = {"pdf": "sha256", "image-guide": "ids_sha256", "web": "date"}[kind]
    if not ver.get(key):
        found.append(Finding("NEW", ["gear/manuals.yaml has no `verified` block for this entry yet"],
                             {"verified": verified_block(c.meta, kind)}))
    elif kind == "pdf" and c.meta["sha256"] != ver["sha256"]:
        title = f", PDF title now \"{c.meta['doc_title']}\"" if c.meta.get("doc_title") else ""
        found.append(Finding("CHANGED", [
            f"the file at the official URL is not the one verified on {ver.get('date')} "
            f"(sha256 {str(ver['sha256'])[:12]}… → {c.meta['sha256'][:12]}…, "
            f"{ver.get('pages')} → {c.meta['pages']} pages{title})"], {"verified": verified_block(c.meta, kind)}))
    elif kind == "image-guide" and c.meta["ids_sha256"] != ver["ids_sha256"]:
        found.append(Finding("CHANGED", [
            f"the guide's page images changed since {ver.get('date')} ({ver.get('pages')} → "
            f"{c.meta['pages']} pages): page numbers cited from it may have shifted"],
            {"verified": verified_block(c.meta, kind)}))
    return found


def newer_finding(entry: dict, lines: list[str], url: str, name: str | None) -> Finding:
    """NEWER finding with registry fields for the candidate (downloaded once to fill in `verified`)."""
    upd: dict = {"url": url}
    if name:
        upd["version"] = re.sub(r"\.pdf$", "", name, flags=re.I)
    if entry["kind"] == "pdf":
        try:
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / "candidate.pdf"
                note(f"… downloading the candidate to verify it: {url}")
                got = download(url, p)
                got.update(pdf_info(p))
            upd["verified"] = verified_block(got, "pdf")
            lines = lines + [f"candidate: {got['pages']} pages, {got['bytes'] / 1e6:.1f} MB"
                             + (f", PDF title \"{got['doc_title']}\"" if got["doc_title"] else "")]
            if got["doc_title"]:
                upd["version"] = got["doc_title"]
        except FetchError as e:
            upd["verified"] = f"TODO: couldn't download the candidate ({e.reason})"
            lines = lines + [f"candidate didn't download: {e.reason}"]
    return Finding("NEWER", lines, upd)


def te_assets(page_html: str) -> list[dict]:
    """PDF assets embedded (as escaped JSON) in a teenage.engineering page."""
    t = re.sub(r'\\+"', '"', page_html)
    dec, found = json.JSONDecoder(), {}
    for m in re.finditer(r'\{"_?id":"[0-9a-f]{24}"', t):
        try:
            obj, _ = dec.raw_decode(t, m.start())
        except ValueError:
            continue
        name, cur = str(obj.get("name") or ""), str(obj.get("current_id") or obj.get("current") or "")
        if not name.lower().endswith(".pdf") or not re.fullmatch(r"[0-9a-f]{24}", cur):
            continue
        suffix = ((obj.get("current_data") or {}).get("original") or {}).get("suffix") or "original.pdf"
        url = f"https://assets.teenage.engineering/_img/{cur}_{suffix}"
        found[url] = {"name": name, "date": str(obj.get("date") or ""), "url": url}
    return list(found.values())


def find_links(page_html: str, pattern: str) -> list[tuple[str, str | None]]:
    """(url, version key) for every match of pattern; the key is capture group 1 if there is one."""
    t = html.unescape(page_html.replace("\\/", "/"))
    rx = re.compile(pattern)
    found: dict[str, str | None] = {}
    for m in rx.finditer(t):
        found.setdefault(m.group(0), m.group(1) if rx.groups else None)
    return list(found.items())


def discover(entry: dict) -> list[Finding]:
    d = entry.get("discover") or {}
    method = d.get("method", "none")
    if method == "none":
        return []
    page = d.get("page") or entry["url"]
    try:
        page_html, _, _ = get_html_cached(page)
    except FetchError as e:
        return [Finding("BROKEN", [f"discovery page {page}: {e.reason} (fix discover.page)"])]
    if method == "te-assets":
        rx = re.compile(d["match"])
        assets = [a for a in te_assets(page_html) if rx.search(a["name"])]
        if not assets:
            return [Finding("BROKEN", [f"discovery: no PDF named like /{d['match']}/ on {page} "
                                       "(naming changed? fix discover.match)"])]
        newest = max(assets, key=lambda a: a["date"])
        if same_url(newest["url"], entry["url"]):
            return []
        return [newer_finding(entry, [f"{page} now offers \"{newest['name']}\" (uploaded {newest['date'][:10]}):",
                                      newest["url"]], newest["url"], newest["name"])]
    if method == "link":
        links = find_links(page_html, d["match"])
        if not links:
            return [Finding("BROKEN", [f"discovery: no link matching /{d['match']}/ on {page} "
                                       "(page changed? fix discover.match)"])]
        keyed = [x for x in links if x[1] is not None]
        latest = max(keyed, key=lambda x: natural_key(x[1]))[0] if keyed else None
        listed = any(same_url(u, entry["url"]) for u, _ in links)
        if listed and (latest is None or same_url(latest, entry["url"])):
            return []
        target = latest or links[0][0]
        why = "now links to a newer file" if listed else "no longer links to our URL; it links to"
        return [newer_finding(entry, [f"{page} {why}:", target], target, None)]
    m = re.search(d["match"], html_to_text(page_html)) or re.search(d["match"], page_html)
    if not m:
        return [Finding("BROKEN", [f"discovery: version pattern /{d['match']}/ not found on {page} "
                                   "(fix discover.match)"])]
    found_v, have = (m.group(1) if m.groups() else m.group(0)), str(entry.get("version"))
    if found_v == have:
        return []
    status = "NEWER" if natural_key(found_v) > natural_key(have) else "CHANGED"
    return [Finding(status, [f"{page} now says version {found_v} (registry: {have})"], {"version": found_v})]


def _validators_match(ver: dict, p: dict) -> bool | None:
    checks = []
    if ver.get("etag") and p["etag"]:
        checks.append(ver["etag"].removeprefix("W/") == p["etag"].removeprefix("W/"))
    if ver.get("last_modified") and p["last_modified"]:
        checks.append(ver["last_modified"] == p["last_modified"])
    if ver.get("bytes") and p["length"] is not None:
        checks.append(int(ver["bytes"]) == p["length"])
    return all(checks) if checks else None


def check_entry(entry: dict) -> list[Finding]:
    """Online check: link alive, content as verified, nothing newer published."""
    kind, url, ver = entry["kind"], entry["url"], entry.get("verified") or {}
    found: list[Finding] = []
    if kind == "pdf":
        try:
            p = probe(url)
        except FetchError as e:
            return [Finding("BROKEN", [f"{url}: {e.reason}"])] + discover(entry)
        if b"%PDF-" not in p["head"]:
            return [Finding("BROKEN", [f"{url} no longer serves a PDF (Content-Type {p['content_type'] or '?'})"])
                    ] + discover(entry)
        if not (_validators_match(ver, p) and ver.get("sha256") and not p["redirects"]):
            try:
                found += compare(entry, ensure(entry, refresh=True))
            except FetchError as e:
                found.append(Finding("BROKEN", [f"{url}: {e.reason}"]))
    elif kind == "image-guide":
        try:
            c = _ensure_image_guide(entry, refresh=True)
            found += compare(entry, c)
            probe(page_image_url(entry, c.meta["ids"][0], "thumb"))
        except FetchError as e:
            found.append(Finding("BROKEN", [f"{e.url}: {e.reason}"]))
    else:
        try:
            found += compare(entry, _ensure_web(entry, refresh=True))
        except FetchError as e:
            found.append(Finding("BROKEN", [f"{url}: {e.reason}"]))
    return found + discover(entry)


# ----------------------------------------------------------------- reporting --

ADVICE = {
    "BROKEN": "Tell Sam this official link is broken. Find the current official URL (start at the entry's "
              "discover.page or the vendor's support site, or web_search the vendor's domain), update "
              "gear/manuals.yaml by hand, then run `fetch {id} --refresh` and `check {id}`.",
    "MOVED": "Tell Sam the link moved. Update `url` in gear/manuals.yaml (snippet below), then `check {id}`.",
    "CHANGED": "Tell Sam the manual was revised upstream. Re-verify facts cited from it in gear/*.md "
               "(page numbers may have shifted), then update the entry in gear/manuals.yaml (snippet below).",
    "NEWER": "Tell Sam a newer version is published. Check it (cover/version), re-verify facts cited "
             "from the old one, update the entry in gear/manuals.yaml (snippet below), then run "
             "`fetch {id} --refresh`.",
    "NEW": "Add the `verified` block below to the entry in gear/manuals.yaml.",
}


def worst(findings: list[Finding]) -> str:
    return max((f.status for f in findings), key=SEVERITY.__getitem__, default="OK")


def snippet(entry: dict, updates: dict) -> str:
    e = copy.deepcopy(entry)
    e.update(updates)
    text = yaml.safe_dump([e], sort_keys=False, allow_unicode=True, width=110, default_flow_style=False)
    return "\n".join("    " + line for line in text.rstrip().splitlines())


def report(entry: dict, findings: list[Finding], summary: str = "", extra: list[str] | None = None) -> str:
    status = worst(findings)
    out(f"{status:<8} {entry['id']:<30} {summary}".rstrip())
    for line in extra or []:
        out(f"{'':<9}{line}")
    for f in findings:
        tag = f"{f.status}: " if f.status != status else ""
        for line in f.lines:
            out(f"{'':<9}{tag}{line}")
    if status != "OK":
        out(f"{'':<9}→ {ADVICE[status].format(id=entry['id'])}")
        updates: dict = {}
        for f in findings:
            updates.update(f.updates)
        if updates:
            out(f"{'':<9}Ready-to-paste replacement for the `id: {entry['id']}` entry "
                "(edit gear/manuals.yaml by hand; keep its comments):")
            out(snippet(entry, updates))
            if "version" in updates:
                out(f"{'':<9}(confirm `version`/`title` against the new document itself)")
    return status


def exit_code(statuses: list[str]) -> int:
    if "BROKEN" in statuses:
        return EXIT_BROKEN
    if any(s in ("NEW", "CHANGED", "NEWER", "MOVED") for s in statuses):
        return EXIT_DRIFT
    return EXIT_OK


def describe(c: Cached) -> str:
    m, kind = c.meta, c.entry["kind"]
    if kind == "pdf":
        title = f" · \"{m['doc_title']}\"" if m.get("doc_title") else ""
        return f"{c.how} · {m.get('pages')} pages · {m.get('bytes', 0) / 1e6:.1f} MB{title}"
    if kind == "image-guide":
        return f"{c.how} · {m.get('pages')} page images"
    return f"{c.how} · {m.get('chars')} chars of text"


# ------------------------------------------------------------------- search --

def is_scanned(pages: list[str]) -> bool:
    return bool(pages) and sum(len(p.strip()) > 30 for p in pages) < 0.2 * len(pages)


def page_texts(entry: dict) -> tuple[list[str], Cached]:
    """Text per PDF page, or the whole web page as one item; [] for image guides."""
    c = ensure(entry)
    if c.warning:
        note(f"warning: {entry['id']}: {c.warning}")
    if entry["kind"] == "web":
        return [norm(c.path.read_text(encoding="utf-8"))], c
    if entry["kind"] != "pdf":
        return [], c
    tp = cpath(entry, ".text.json")
    try:
        cached = json.loads(tp.read_text(encoding="utf-8"))
        if cached.get("sha256") == c.meta["sha256"]:
            return cached["pages"], c
    except (OSError, ValueError):
        pass
    with pymupdf.open(c.path) as doc:
        pages = [norm(page.get_text()) for page in doc]
    tp.write_text(json.dumps({"sha256": c.meta["sha256"], "pages": pages}), encoding="utf-8")
    return pages, c


def cite(entry: dict, page: int | None = None) -> str:
    if page is None or entry["kind"] == "web":
        return f"[{short(entry)}]({entry['url']})"
    return f"[{short(entry)} p{page}]({entry['url']}#page={page})"


def _terms(query: str) -> tuple[str, list[str]]:
    q = " ".join(norm(query).lower().split())
    words = [w.strip(".,;:!?()[]{}\"'") for w in q.split()]
    return q, [w for w in words if w]


def _snippet(text: str, start: int, end: int, words: list[str], width: int = 110) -> str:
    a, b = max(0, start - width), min(len(text), end + width)
    s = " ".join(text[a:b].split())
    for w in sorted(set(words), key=len, reverse=True):
        s = re.sub(rf"(?<![\w*])({re.escape(w)}\w*)", r"**\1**", s, flags=re.I)
    return ("…" if a else "") + s + ("…" if b < len(text) else "")


def search_pages(pages: list[str], query: str) -> list[dict]:
    """Pages containing every query word (word-prefix match); the exact phrase ranks higher."""
    q, words = _terms(query)
    if not words:
        return []
    word_rx = [re.compile(rf"(?<!\w){re.escape(w)}", re.I) for w in words]
    phrase_rx = re.compile(r"\s+".join(re.escape(w) for w in words), re.I) if len(words) > 1 else None
    hits = []
    for n, text in enumerate(pages, 1):
        found = [list(rx.finditer(text)) for rx in word_rx]
        if not all(found):
            continue
        phrases = list(phrase_rx.finditer(text)) if phrase_rx else []
        first = phrases[0] if phrases else min((ms[0] for ms in found), key=lambda m: m.start())
        hits.append({"page": n, "score": 5 * len(phrases) + sum(len(ms) for ms in found),
                     "count": len(phrases) if phrases else len(found[0]),
                     "snippet": _snippet(text, first.start(), first.end(), words),
                     "spans": [(m.start(), m.end()) for m in (phrases or found[0])]})
    hits.sort(key=lambda h: (-h["score"], h["page"]))
    return hits


def visual_hint(entry: dict) -> str:
    if entry["kind"] == "image-guide":
        return (f"{entry['id']}: its text is baked into page images, so there's no text search. Browse it "
                f"visually: open {entry['url']} (page N = the Nth picture on that page).")
    return (f"{entry['id']}: scanned PDF with no text layer, so there's no text search. Browse it "
            f"visually: open {entry['url']}#page=N.")


def cmd_search(args: argparse.Namespace) -> int:
    entries = resolve(load_registry(args.registry), [args.target])
    hints, misses, statuses = [], [], []
    for e in entries:
        if e["kind"] == "image-guide":
            hints.append(visual_hint(e))
            continue
        try:
            pages, _ = page_texts(e)
        except FetchError as x:
            out(f"BROKEN   {e['id']}: {x.reason}: {x.url}  (run `check {e['id']}`)")
            statuses.append("BROKEN")
            continue
        if e["kind"] == "pdf" and is_scanned(pages):
            hints.append(visual_hint(e))
            continue
        hits = search_pages(pages, args.query)
        if not hits:
            misses.append(e["id"])
            continue
        if e["kind"] == "web":
            _, words = _terms(args.query)
            spans = hits[0]["spans"]
            out(f"{e['id']} — {short(e)} (web page): {len(spans)} match(es) for \"{args.query}\"")
            for s, t in spans[: args.limit]:
                out(f"  {_snippet(pages[0], s, t, words)}")
            out(f"  cite: {cite(e)}")
            continue
        out(f"{e['id']} — {short(e)} ({len(pages)} PDF pages): {len(hits)} page(s) match \"{args.query}\"")
        for h in hits[: args.limit]:
            out(f"  p{h['page']:<4} ×{h['count']:<3} {h['snippet']}")
            out(f"  {'':<10} {cite(e, h['page'])}")
        if len(hits) > args.limit:
            out("  more: " + ", ".join(f"p{h['page']}" for h in hits[args.limit:]))
    if misses:
        out(f"no matches in: {', '.join(misses)}")
    for h in hints:
        out(f"hint: {h}")
    return exit_code(statuses)


# ----------------------------------------------------------------- commands --

def cmd_list(args: argparse.Namespace) -> int:
    entries = load_registry(args.registry)
    out(f"{'id':<30} {'kind':<12} {'gear':<26} {'version':<26} cached")
    for e in entries:
        meta = read_meta(e)
        if not meta or meta.get("url") != e["url"]:
            cached = "-"
        elif e["kind"] == "pdf":
            cached = f"{meta.get('pages')} pp, {meta.get('bytes', 0) / 1e6:.1f} MB ({ago(meta.get('validated'))})"
        elif e["kind"] == "image-guide":
            cached = f"{meta.get('pages')} page images ({ago(meta.get('validated'))})"
        else:
            cached = f"{meta.get('chars')} chars ({ago(meta.get('validated'))})"
        version = str(e.get("version") or "-")
        out(f"{e['id']:<30} {e['kind']:<12} {', '.join(gear_of(e)):<26} {version[:26]:<26} {cached}")
        out(f"{'':<4}{e['url']}")
    out(f"cache: {cache_dir()}")
    return EXIT_OK


def cmd_fetch(args: argparse.Namespace) -> int:
    statuses = []
    for e in resolve(load_registry(args.registry), [args.target]):
        try:
            c = ensure(e, refresh=args.refresh)
        except FetchError as x:
            statuses.append(report(e, [Finding("BROKEN", [f"{x.url}: {x.reason}"])]))
            continue
        extra = [f"warning: {c.warning}"] if c.warning else []
        if e["kind"] == "pdf":
            extra.append(str(c.path))
        elif e["kind"] == "image-guide":
            extra.append(f"page images: {e['url']} (`text {e['id']} N` prints page N's image URL)")
        else:
            extra.append(f"{c.path}  (text of {e['url']})")
        statuses.append(report(e, compare(e, c), describe(c), extra))
    return exit_code(statuses)


def cmd_check(args: argparse.Namespace) -> int:
    statuses = []
    for e in resolve(load_registry(args.registry), args.targets):
        findings = check_entry(e)
        has_discovery = (e.get("discover") or {}).get("method", "none") != "none"
        ok_note = "link OK, content as verified" + (", no newer version found" if has_discovery else "")
        statuses.append(report(e, findings, ok_note if worst(findings) == "OK" else ""))
    bad = [s for s in statuses if s != "OK"]
    out(f"\n{len(statuses) - len(bad)} OK, {len(bad)} need attention" if bad else f"\nall {len(statuses)} OK")
    return exit_code(statuses)


def cmd_text(args: argparse.Namespace) -> int:
    e = resolve_one(load_registry(args.registry), args.id)
    if e["kind"] == "image-guide":
        ids = ensure(e).meta["ids"]
        if not args.page or not 1 <= args.page <= len(ids):
            raise RegistryError(f"{e['id']} has pages 1–{len(ids)}")
        out(f"{short(e)} page {args.page} is an image (no text layer); read it visually: "
            f"{page_image_url(e, ids[args.page - 1])}")
        return EXIT_OK
    pages, _ = page_texts(e)
    if e["kind"] == "web":
        out(f"# {short(e)} — cite as {cite(e)}\n")
        out(pages[0])
        return EXIT_OK
    if not args.page or not 1 <= args.page <= len(pages):
        raise RegistryError(f"{e['id']} has PDF pages 1–{len(pages)}; pass one of those")
    out(f"# {short(e)}, PDF page {args.page} of {len(pages)} — cite as {cite(e, args.page)}\n")
    out(pages[args.page - 1].strip() or "(no text layer on this page: it's a scan or a drawing; "
                                        "read it visually)")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--registry", help="registry file (default gear/manuals.yaml; env MUSIC_MANUALS_REGISTRY)")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list", parents=[common], help="registry entries and cache state")
    s.set_defaults(func=cmd_list)
    s = sub.add_parser("fetch", parents=[common], help="download into the local cache and verify")
    s.add_argument("target", help="manual id, gear id, or 'all'")
    s.add_argument("--refresh", action="store_true", help="re-download even if the cache is fresh")
    s.set_defaults(func=cmd_fetch)
    s = sub.add_parser("check", parents=[common], help="online: links alive, unchanged, newest version?")
    s.add_argument("targets", nargs="*", help="manual/gear ids (default: all)")
    s.set_defaults(func=cmd_check)
    s = sub.add_parser("search", parents=[common], help="pages mentioning all the terms, with citations")
    s.add_argument("target", help="manual id, gear id, or 'all'")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=8, help="results per manual (default 8)")
    s.set_defaults(func=cmd_search)
    s = sub.add_parser("text", parents=[common], help="text of one PDF page (or of a whole web page)")
    s.add_argument("id")
    s.add_argument("page", type=int, nargs="?")
    s.set_defaults(func=cmd_text)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except RegistryError as e:
        note(f"error: {e}")
        return EXIT_USAGE
    except FetchError as e:
        note(f"BROKEN: {e.reason}: {e.url}")
        return EXIT_BROKEN


if __name__ == "__main__":
    sys.exit(main())
