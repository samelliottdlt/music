# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest>=8", "pymupdf>=1.24", "pyyaml>=6"]
# ///
"""Offline smoke tests for the music-setup scripts (no network needed).

    uv run .github/skills/music-setup/scripts/tests/test_offline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manuals  # noqa: E402


def entry(**kw):
    base = {"id": "x-guide", "gear": "op-1-field", "title": "X", "publisher": "TE", "kind": "pdf",
            "url": "https://example.com/x.pdf", "version": "1.0"}
    base.update(kw)
    return base


def offline_download(url, *args, **kwargs):
    raise manuals.FetchError(url, "offline test")


def test_registry_is_valid_and_complete():
    entries = manuals.load_registry()
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids))
    for e in entries:
        ver = e.get("verified") or {}
        assert ver.get("date"), e["id"]
        if e["kind"] == "pdf":
            assert len(ver.get("sha256", "")) == 64 and ver.get("pages") and ver.get("bytes"), e["id"]
        if e["kind"] == "image-guide":
            assert ver.get("pages") and ver.get("ids_sha256"), e["id"]


def test_inventory_has_no_manual_links_left():
    inv = yaml.safe_load((manuals.REPO_ROOT / "gear" / "inventory.yaml").read_text(encoding="utf-8"))
    assert not [g["id"] for g in inv["gear"] if "manual_pdf" in g]


def test_validate_reports_problems():
    known = {"op-1-field"}
    bad = [
        entry(id="Bad_ID"),
        entry(id="a", gear="nope"),
        entry(id="b", kind="video"),
        entry(id="c", url="http://example.com/x.pdf"),
        entry(id="d", discover={"method": "link", "page": "https://example.com", "match": "("}),
        entry(id="e", kind="image-guide"),
        entry(id="e"),
    ]
    problems = "\n".join(manuals.validate(bad, known))
    for needle in ("kebab-case", "not an id in gear/inventory.yaml", "kind must be", "https://",
                   "not a valid regex", "page_images.list", "duplicate id"):
        assert needle in problems
    assert manuals.validate([entry()], known) == []


def test_resolve_by_manual_id_gear_id_and_all():
    entries = manuals.load_registry()
    assert [e["id"] for e in manuals.resolve(entries, ["op-1-field-guide"])] == ["op-1-field-guide"]
    assert len(manuals.resolve(entries, ["jaguar"])) >= 2
    assert len(manuals.resolve(entries, ["all"])) == len(entries)
    with pytest.raises(manuals.RegistryError):
        manuals.resolve(entries, ["no-such-thing"])
    with pytest.raises(manuals.RegistryError):
        manuals.resolve_one(entries, "jaguar")


# Shape of teenage.engineering guide pages: asset metadata as JSON, escaped to varying depths.
TE_PAGE = r'''<a href="https://assets.teenage.engineering/_img/69f248938d433104c4dd1846_original.pdf">download</a>
<script>window.x = "{\\\"id\\\":\\\"69414b0928523c19055971b0\\\",\\\"name\\\":\\\"OP-1 field user guide firmware 1.6.0.pdf\\\",\\\"date\\\":\\\"2025-12-16T12:05:29.521Z\\\",\\\"current_id\\\":\\\"69414b094b4b8519058eaf0b\\\",\\\"current_data\\\":{\\\"original\\\":{\\\"suffix\\\":\\\"original.pdf\\\"}},\\\"current\\\":\\\"69414b094b4b8519058eaf0b\\\"}",
"{\"_id\":\"6731bf3f00a5de45d9bd455b\",\"name\":\"OP–XY - declaration of conformity.pdf\",\"current\":\"6731bf3f00a5de45d9bd4559\",\"kind\":\"bin\",\"date\":\"2024-11-11T08:24:31.425Z\"}",
"{\\\"id\\\":\\\"69f24893c79f5104c46f8230\\\",\\\"name\\\":\\\"OP-1 field user guide firmware 1.7.0.pdf\\\",\\\"date\\\":\\\"2026-04-29T18:06:11.511Z\\\",\\\"current_id\\\":\\\"69f248938d433104c4dd1846\\\"}"</script>'''


def test_te_assets_parser_handles_escaping_and_key_order():
    assets = {a["name"]: a for a in manuals.te_assets(TE_PAGE)}
    assert assets["OP-1 field user guide firmware 1.7.0.pdf"]["url"] == (
        "https://assets.teenage.engineering/_img/69f248938d433104c4dd1846_original.pdf")
    assert assets["OP-1 field user guide firmware 1.6.0.pdf"]["date"].startswith("2025-12-16")
    assert assets["OP–XY - declaration of conformity.pdf"]["url"].endswith("6731bf3f00a5de45d9bd4559_original.pdf")


def test_te_discovery_reports_newer(monkeypatch):
    monkeypatch.setattr(manuals, "get_html_cached", lambda url: (TE_PAGE, url, []))
    monkeypatch.setattr(manuals, "download", offline_download)
    old = entry(url="https://assets.teenage.engineering/_img/69414b094b4b8519058eaf0b_original.pdf",
                discover={"page": "https://teenage.engineering/guides/op-1", "method": "te-assets",
                          "match": r"OP-1 field user guide firmware [\d.]+\.pdf"})
    (finding,) = manuals.discover(old)
    assert finding.status == "NEWER"
    assert finding.updates["url"].endswith("69f248938d433104c4dd1846_original.pdf")
    assert manuals.discover(dict(old, url=finding.updates["url"])) == []


def test_link_discovery_picks_latest_version(monkeypatch):
    page = ('<a href="https://cdn.shopify.com/s/files/1/files/CC_manual_WEB.pdf?v=100">old</a>'
            '<a href="https://cdn.shopify.com/s/files/1/files/CC_manual_WEB.pdf?v=2000">new</a>')
    rx = r"""https://cdn\.shopify\.com/[^"'\s]*CC_manual[^"'\s]*\.pdf\?v=(\d+)"""
    assert [k for _, k in manuals.find_links(page, rx)] == ["100", "2000"]
    monkeypatch.setattr(manuals, "get_html_cached", lambda url: (page, url, []))
    monkeypatch.setattr(manuals, "download", offline_download)
    disc = {"page": "https://example.com/m", "method": "link", "match": rx}
    stale = entry(url="https://cdn.shopify.com/s/files/1/files/CC_manual_WEB.pdf?v=100", discover=disc)
    (finding,) = manuals.discover(stale)
    assert finding.status == "NEWER" and finding.updates["url"].endswith("v=2000")
    assert manuals.discover(dict(stale, url=finding.updates["url"])) == []


def test_text_version_discovery(monkeypatch):
    monkeypatch.setattr(manuals, "get_html_cached", lambda url: ("<div>guide</div><div>v.1.3.4</div>", url, []))
    disc = {"method": "text-version", "match": r"v\.(\d+(?:\.\d+)+)"}
    (finding,) = manuals.discover(entry(kind="web", version="1.3.3", discover=disc))
    assert finding.status == "NEWER" and finding.updates == {"version": "1.3.4"}
    assert manuals.discover(entry(kind="web", version="1.3.4", discover=disc)) == []


def test_same_url_ignores_scheme_and_escaping():
    assert manuals.same_url("http://example.com/a%27b.pdf", "https://EXAMPLE.com/a'b.pdf")
    assert not manuals.same_url("https://example.com/a.pdf", "https://example.com/b.pdf")


def test_html_to_text():
    t = manuals.html_to_text("<head><title>t</title></head><script>var a=1</script>"
                             "<div>line&nbsp;in</div><p>one<br>two</p><style>.x{}</style>")
    assert t.splitlines() == ["line in", "one", "two"]


def test_search_ranks_phrase_and_folds_dashes_and_ligatures():
    pages = ["nothing here", manuals.norm("the OP–XY has a line in and an output"),
             manuals.norm("line in, line in: the line input is a 3.5 mm jack \ufb01eld")]
    hits = manuals.search_pages(pages, "line in")
    assert [h["page"] for h in hits] == [3, 2]
    assert "**line** **in**" in hits[0]["snippet"]
    assert [h["page"] for h in manuals.search_pages(pages, "OP-XY")] == [2]
    assert [h["page"] for h in manuals.search_pages(pages, "field")] == [3]


def test_snippet_is_valid_yaml_with_updates():
    e = entry(discover={"page": "https://example.com", "method": "link", "match": r"""x[^"'\s]*\.pdf"""})
    text = manuals.snippet(e, {"url": "https://example.com/y.pdf", "verified": {"sha256": "ab"}})
    (loaded,) = yaml.safe_load("\n".join(line[4:] for line in text.splitlines()))
    assert loaded["url"] == "https://example.com/y.pdf" and loaded["verified"]["sha256"] == "ab"
    assert loaded["discover"]["match"] == e["discover"]["match"]


@pytest.mark.parametrize("title,kept", [("OP-1 field user guide firmware 1.7.0 (REV 10)", True),
                                        ("TU-3_ejgfispd", False), ("acos_guitar_manual_EN.indd", False),
                                        ("file:///C|/OWNER'S MANUALS/Bass VI (1966).jpg", False)])
def test_pdf_info_drops_file_name_titles(tmp_path, title, kept):
    doc = pymupdf.open()
    doc.new_page()
    doc.set_metadata({"title": title})
    doc.save(tmp_path / "t.pdf")
    doc.close()
    info = manuals.pdf_info(tmp_path / "t.pdf")
    assert info["pages"] == 1 and (info["doc_title"] == title) == kept


def test_exit_codes():
    assert manuals.exit_code(["OK", "OK"]) == 0
    assert manuals.exit_code(["OK", "NEWER"]) == 3
    assert manuals.exit_code(["CHANGED", "BROKEN"]) == 2


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
