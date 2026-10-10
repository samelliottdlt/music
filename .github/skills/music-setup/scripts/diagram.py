#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf>=1.24", "pillow>=10.1", "pyyaml>=6"]
# ///
"""Make simple, useful diagrams: boxes and official drawings joined by labelled arrows.

  uv run .github/skills/music-setup/scripts/diagram.py setup/diagrams/recording-mode.yaml
  uv run .github/skills/music-setup/scripts/diagram.py spec.yaml -o out/visuals/name.png

Writes a PNG (default out/visuals/<spec name>.png, which is gitignored) and prints its path and
file:/// URI. Specs are YAML or JSON ("-" reads stdin). Full examples: setup/diagrams/*.yaml.
Never commit or upload PNGs that contain drawings from manuals; commit the spec instead.

title: Recording mode                  # optional, plus optional `subtitle`
direction: LR                          # auto layout LR (default) or TB, or give nodes col/row
nodes:
  - id: tx6                            # required, unique
    label: TX-6                        # box text, or the caption under an image ("\n" = new line)
    note: mixer                        # optional smaller grey line(s)
    col: 2                             # optional grid cell (0-based); nodes without one are auto-placed
    row: 0
    style: dashed                      # optional dashed outline, e.g. "not connected yet"
    image: {manual: tx-6-guide, page: 113, box: [0.42, 0.6, 0.55, 0.855]}
    #  or image: drawing.png | {file: drawing.png, box: [...]} | {url: https://..., box: [...]}
    #  box = crop as fractions (x0, y0, x1, y1); read it off `manuals.py page <id> <n> --grid`
    height: 200                        # image height in px (or width:); rotate: 90 = degrees clockwise
    highlights:                        # marks on the image, as fractions of the image as shown
      - {box: [0.27, 0.55, 0.43, 0.92], label: audio in, shape: box}   # shape: box | circle
edges:
  - {from: tx6, to: op1, label: "main out → audio in\n3.5 mm stereo"}
  #  style: dashed, color: "#e4572e", arrow: end | both | none, from_side/to_side: left|right|top|bottom
groups:
  - {label: Pedalboard, nodes: [pedals, tuner, chroma]}
sources:                               # footer; manual pages used for images are cited automatically
  - "Connections: setup/signal-chain.md"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from PIL import Image, ImageColor, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manuals  # noqa: E402  (lives next to this script)

INK = (40, 40, 40)
MUTED = (112, 112, 112)
ACCENT = (228, 87, 46)
BOX_FILL = (246, 246, 243)
GROUP_FILL = (240, 244, 250)
GROUP_LINE = (150, 166, 194)
GROUP_TEXT = (85, 100, 130)
IMG_LINE = (212, 212, 212)
WHITE = (255, 255, 255)
SIZE = {"title": 34, "subtitle": 19, "label": 22, "note": 17, "edge": 17, "group": 19, "source": 15, "mark": 17}
PAD_X, PAD_Y = 18, 12        # inside text boxes
CAPTION_GAP = 8              # image → caption
STUB = 20                    # straight run out of / into a node before the first turn
ARROW = 15                   # arrowhead length
LABEL_PAD = (8, 5)           # inside edge labels
MARGIN = 44
GPAD = 22                    # group box padding around its nodes
DIRS = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}


class SpecError(Exception):
    pass


# --------------------------------------------------------------------- text --

@dataclass
class Line:
    text: str
    size: int
    bold: bool = False
    color: tuple = INK


def line_h(size: int) -> int:
    return round(size * 1.28)


def measure(lines: list[Line]) -> tuple[int, int]:
    if not lines:
        return 0, 0
    return (math.ceil(max(manuals.font(ln.size, ln.bold).getlength(ln.text) for ln in lines)),
            sum(line_h(ln.size) for ln in lines))


def draw_lines(d: ImageDraw.ImageDraw, lines: list[Line], cx: float, top: float, align: str = "center") -> None:
    y = top
    for ln in lines:
        f = manuals.font(ln.size, ln.bold)
        x = cx - f.getlength(ln.text) / 2 if align == "center" else cx
        d.text((x, y), ln.text, font=f, fill=ln.color)
        y += line_h(ln.size)


class Texts:
    """Builds text lines and swaps glyphs the font lacks (they'd render as boxes) for '?', with a warning."""

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def lines(self, text, size: int, bold: bool = False, color: tuple = INK) -> list[Line]:
        if text is None or str(text) == "":
            return []
        out = []
        for t in str(text).split("\n"):
            bad = manuals.missing_glyphs(t, bold)
            if bad:
                self.warnings.append(f"font has no glyph for {' '.join(sorted(bad))} in {t!r}; used '?'")
                t = "".join("?" if ch in bad else ch for ch in t)
            out.append(Line(t, size, bold, color))
        return out


def wrap(text: str, size: int, width: float) -> list[str]:
    f, rows, cur = manuals.font(size), [], ""
    for word in str(text).split():
        trial = f"{cur} {word}".strip()
        if cur and f.getlength(trial) > width:
            rows.append(cur)
            cur = word
        else:
            cur = trial
    return rows + ([cur] if cur else [])


def color_of(value, default: tuple = INK) -> tuple:
    if not value:
        return default
    try:
        return ImageColor.getrgb(str(value))[:3]
    except ValueError:
        raise SpecError(f"unknown color {value!r} (use e.g. \"#e4572e\" or \"red\")") from None


# -------------------------------------------------------------------- model --

@dataclass(eq=False)
class Node:
    id: str
    spec: dict
    img: Image.Image | None = None
    lines: list[Line] = field(default_factory=list)
    bw: int = 0
    bh: int = 0
    w: int = 0
    h: int = 0
    col: int = 0
    row: int = 0
    x: float = 0.0
    y: float = 0.0

    @property
    def body(self) -> tuple[float, float, float, float]:
        bx = self.x + (self.w - self.bw) / 2
        return bx, self.y, bx + self.bw, self.y + self.bh

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return self.x, self.y, self.x + self.w, self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.bh / 2


@dataclass(eq=False)
class Edge:
    a: Node
    b: Node
    spec: dict
    label: list[Line]
    color: tuple
    dashed: bool
    arrow: str
    s: str = ""
    t: str = ""
    pa: tuple = (0.0, 0.0)
    pb: tuple = (0.0, 0.0)
    pts: list = field(default_factory=list)
    cost: float = 0.0
    box: tuple | None = None


@dataclass(eq=False)
class Group:
    label: list[Line]
    nodes: list[Node]
    color: tuple = GROUP_LINE

    def rect(self) -> tuple[float, float, float, float]:
        x0 = min(n.rect[0] for n in self.nodes) - GPAD
        y0 = min(n.rect[1] for n in self.nodes) - GPAD - (measure(self.label)[1] + 8 if self.label else 0)
        x1 = max(n.rect[2] for n in self.nodes) + GPAD
        y1 = max(n.rect[3] for n in self.nodes) + GPAD
        return x0, y0, x1, y1

    def label_rect(self) -> tuple[float, float, float, float]:
        x0, y0, _, _ = self.rect()
        w, h = measure(self.label)
        return x0 + 12, y0 + 6, x0 + 12 + w, y0 + 6 + h


# ------------------------------------------------------------------- images --

def fetch_image(url: str) -> Image.Image:
    folder = manuals.cache_dir() / "web-images"
    path = folder / (hashlib.sha1(url.encode()).hexdigest()[:16] + (Path(urllib.parse.urlparse(url).path).suffix
                                                                    or ".img"))
    if not path.exists():
        manuals.download(url, path, expect_pdf=False)
    with Image.open(path) as im:
        return manuals.flatten(im)


def load_image(src, base: Path, registry: list[dict], used: list[str]) -> Image.Image:
    if isinstance(src, str):
        src = {"file": src}
    if not isinstance(src, dict):
        raise SpecError(f"image must be a file path or a mapping, got {src!r}")
    if "manual" in src:
        if "page" not in src:
            raise SpecError(f"image {src} needs a page")
        entry = manuals.resolve_one(registry, str(src["manual"]))
        used.append(manuals.cite(entry, int(src["page"])).split("](")[0].lstrip("["))
        return manuals.render_page(entry, int(src["page"]), src.get("box"), src.get("dpi"))
    if "url" in src:
        im = fetch_image(str(src["url"]))
    elif "file" in src:
        path = (base / str(src["file"])).resolve()
        if not path.exists():
            raise SpecError(f"image file not found: {path}")
        with Image.open(path) as f:
            im = manuals.flatten(f)
    else:
        raise SpecError(f"image needs `manual` (+ page), `file` or `url`: {src}")
    box = manuals.parse_box(src.get("box"))
    if box:
        w, h = im.size
        im = im.crop((round(box[0] * w), round(box[1] * h), round(box[2] * w), round(box[3] * h)))
    return im


def rotate(im: Image.Image, degrees: float) -> Image.Image:
    turns = {90: Image.Transpose.ROTATE_270, 180: Image.Transpose.ROTATE_180, 270: Image.Transpose.ROTATE_90}
    d = degrees % 360
    if d == 0:
        return im
    if d in turns:
        return im.transpose(turns[d])
    return im.rotate(-d, expand=True, fillcolor=WHITE, resample=Image.Resampling.BICUBIC)


# ------------------------------------------------------------------- build --

def build(spec: dict, base: Path, registry: list[dict], texts: Texts, used: list[str]):
    nodes: list[Node] = []
    for i, ns in enumerate(spec.get("nodes") or []):
        if not isinstance(ns, dict) or not ns.get("id"):
            raise SpecError(f"nodes[{i}] needs an id")
        if any(n.id == str(ns["id"]) for n in nodes):
            raise SpecError(f"duplicate node id {ns['id']!r}")
        n = Node(str(ns["id"]), ns)
        note = texts.lines(ns.get("note"), SIZE["note"], False, MUTED)
        if "image" in ns:
            im = rotate(load_image(ns["image"], base, registry, used), float(ns.get("rotate", 0)))
            if ns.get("width"):
                w = int(ns["width"])
                h = max(1, round(im.height * w / im.width))
            else:
                h = int(ns.get("height", spec.get("image_height", 180)))
                w = max(1, round(im.width * h / im.height))
            n.img = im.resize((w, h), Image.Resampling.LANCZOS)
            n.bw, n.bh = w, h
            n.lines = texts.lines(ns.get("label"), SIZE["label"], True) + note
            cw, ch = measure(n.lines)
            n.w, n.h = max(w, cw), h + (CAPTION_GAP + ch if n.lines else 0)
        else:
            n.lines = texts.lines(ns.get("label", n.id), SIZE["label"], True) + note
            tw, th = measure(n.lines)
            n.bw = max(int(ns.get("width", 0)), tw + 2 * PAD_X, 110)
            n.bh = max(int(ns.get("height", 0)), th + 2 * PAD_Y)
            n.w, n.h = n.bw, n.bh
        nodes.append(n)
    if not nodes:
        raise SpecError("the spec has no nodes")
    by_id = {n.id: n for n in nodes}

    def known(where: str, nid) -> Node:
        if nid not in by_id:
            raise SpecError(f"{where}: unknown node id {nid!r} (known: {', '.join(by_id)})")
        return by_id[nid]

    edges = []
    for i, es in enumerate(spec.get("edges") or []):
        if not isinstance(es, dict):
            raise SpecError(f"edges[{i}] must be a mapping")
        a, b = known(f"edges[{i}].from", es.get("from")), known(f"edges[{i}].to", es.get("to"))
        if a is b:
            raise SpecError(f"edges[{i}] connects {a.id!r} to itself")
        style, arrow = es.get("style", "solid"), es.get("arrow", "end")
        if style not in ("solid", "dashed") or arrow not in ("end", "both", "none"):
            raise SpecError(f"edges[{i}]: style must be solid|dashed and arrow end|both|none")
        for k in ("from_side", "to_side"):
            if es.get(k) and es[k] not in DIRS:
                raise SpecError(f"edges[{i}].{k} must be one of {', '.join(DIRS)}")
        color = color_of(es.get("color"))
        edges.append(Edge(a, b, es, texts.lines(es.get("label"), SIZE["edge"], False, color), color,
                          style == "dashed", arrow))

    groups = []
    for i, gs in enumerate(spec.get("groups") or []):
        members = [known(f"groups[{i}].nodes", m) for m in (gs.get("nodes") or [])]
        if not members:
            raise SpecError(f"groups[{i}] has no nodes")
        groups.append(Group(texts.lines(gs.get("label"), SIZE["group"], True, GROUP_TEXT), members,
                            color_of(gs.get("color"), GROUP_LINE)))
    return nodes, edges, groups


# ------------------------------------------------------------------ layout --

def assign_cells(nodes: list[Node], edges: list[Edge], lr: bool) -> None:
    """Explicit col/row where given; otherwise rank = longest path from a source (LR: column)."""
    rank = {n.id: 0 for n in nodes}
    for _ in range(len(nodes)):
        changed = False
        for e in edges:
            if rank[e.b.id] < rank[e.a.id] + 1 <= len(nodes):
                rank[e.b.id] = rank[e.a.id] + 1
                changed = True
        if not changed:
            break
    taken: dict[tuple[int, int], str] = {}
    fixed = [n for n in nodes if "col" in n.spec and "row" in n.spec]
    for n in fixed:
        n.col, n.row = int(n.spec["col"]), int(n.spec["row"])
    for n in [n for n in nodes if n not in fixed]:
        main = int(n.spec.get("col" if lr else "row", rank[n.id]))
        cross = n.spec.get("row" if lr else "col")
        if cross is None:
            cross = 0
            while ((main, cross) if lr else (cross, main)) in taken or any(
                    (m.col, m.row) == ((main, cross) if lr else (cross, main)) for m in fixed):
                cross += 1
        n.col, n.row = (main, int(cross)) if lr else (int(cross), main)
        taken[(n.col, n.row)] = n.id
    seen: dict[tuple[int, int], str] = {}
    for n in nodes:
        if n.col < 0 or n.row < 0:
            raise SpecError(f"node {n.id!r}: col/row must be >= 0")
        if (n.col, n.row) in seen:
            raise SpecError(f"nodes {seen[(n.col, n.row)]!r} and {n.id!r} are both in col {n.col}, row {n.row}")
        seen[(n.col, n.row)] = n.id


def pick_sides(e: Edge, lr: bool) -> None:
    a, b = e.a, e.b
    if lr:
        if b.col != a.col:
            s, t = ("right", "left") if b.col > a.col else ("left", "right")
        else:
            s, t = ("bottom", "top") if b.row > a.row else ("top", "bottom")
    else:
        if b.row != a.row:
            s, t = ("bottom", "top") if b.row > a.row else ("top", "bottom")
        else:
            s, t = ("right", "left") if b.col > a.col else ("left", "right")
    e.s, e.t = e.spec.get("from_side", s), e.spec.get("to_side", t)


def label_size(lines: list[Line]) -> tuple[int, int]:
    w, h = measure(lines)
    return w + 2 * LABEL_PAD[0], h + 2 * LABEL_PAD[1]


def initial_gaps(spec: dict, edges: list[Edge], groups: list[Group], ncol: int, nrow: int):
    hg = [float(spec.get("hgap", 90))] * max(0, ncol - 1)
    vg = [float(spec.get("vgap", 70))] * max(0, nrow - 1)
    for e in edges:
        if not e.label:
            continue
        w, h = label_size(e.label)
        if e.a.col != e.b.col and e.s in ("left", "right"):
            lo, hi = sorted((e.a.col, e.b.col))
            for g in {lo, hi - 1}:
                hg[g] = max(hg[g], w + 2 * STUB + ARROW + 24)
        if e.a.row != e.b.row and e.s in ("top", "bottom"):
            lo, hi = sorted((e.a.row, e.b.row))
            for g in {lo, hi - 1}:
                vg[g] = max(vg[g], h + 2 * STUB + ARROW + 16)
    for gr in groups:
        rows, cols = [n.row for n in gr.nodes], [n.col for n in gr.nodes]
        label_h = measure(gr.label)[1] + 8 if gr.label else 0
        if min(rows) > 0:
            vg[min(rows) - 1] = max(vg[min(rows) - 1], 2 * GPAD + label_h + 24)
        if max(rows) < nrow - 1:
            vg[max(rows)] = max(vg[max(rows)], 2 * GPAD + 24)
        if min(cols) > 0:
            hg[min(cols) - 1] = max(hg[min(cols) - 1], 2 * GPAD + 40)
        if max(cols) < ncol - 1:
            hg[max(cols)] = max(hg[max(cols)], 2 * GPAD + 40)
    return hg, vg


def place(nodes: list[Node], ncol: int, nrow: int, hg: list[float], vg: list[float]):
    """Columns as wide as their widest node; rows aligned on image/box centres so straight arrows stay
    straight even when captions differ."""
    colw = [max([n.w for n in nodes if n.col == c], default=0) for c in range(ncol)]
    above = [max([n.bh / 2 for n in nodes if n.row == r], default=0) for r in range(nrow)]
    below = [max([n.h - n.bh / 2 for n in nodes if n.row == r], default=0) for r in range(nrow)]
    xs, ys, x, y = [], [], 0.0, 0.0
    for c in range(ncol):
        xs.append(x)
        x += colw[c] + (hg[c] if c < ncol - 1 else 0)
    for r in range(nrow):
        ys.append(y)
        y += above[r] + below[r] + (vg[r] if r < nrow - 1 else 0)
    for n in nodes:
        n.x = xs[n.col] + (colw[n.col] - n.w) / 2
        n.y = ys[n.row] + above[n.row] - n.bh / 2
    gaps_x = [(xs[c] + colw[c], xs[c + 1]) for c in range(ncol - 1)]
    gaps_y = [(ys[r] + above[r] + below[r], ys[r + 1]) for r in range(nrow - 1)]
    return gaps_x, gaps_y, (xs[0], ys[0], x, y)


def lanes(gaps: list[tuple[float, float]], lo: float, hi: float) -> list[float]:
    """Candidate x (or y) positions for vertical (horizontal) runs: gap centres ± a little, plus outside."""
    out = []
    for a, b in gaps:
        mid = (a + b) / 2
        out += [v for v in (mid, mid - 18, mid + 18) if a + 8 < v < b - 8]
    return out + [lo - 30, lo - 48, hi + 30, hi + 48]


# ------------------------------------------------------------------ routing --

def is_h(u, v) -> bool:
    return abs(u[1] - v[1]) < 0.5


def seg_hits_rect(u, v, r) -> bool:
    x0, y0, x1, y1 = r
    if is_h(u, v):
        a, b = sorted((u[0], v[0]))
        return y0 < u[1] < y1 and a < x1 and b > x0
    a, b = sorted((u[1], v[1]))
    return x0 < u[0] < x1 and a < y1 and b > y0


def crosses(s1, s2) -> bool:
    (u, v), (r, s) = s1, s2
    h1, h2 = is_h(u, v), is_h(r, s)
    if h1 == h2:
        return False
    if not h1:
        (u, v), (r, s) = (r, s), (u, v)
    y, x = u[1], r[0]
    return min(u[0], v[0]) + 1 < x < max(u[0], v[0]) - 1 and min(r[1], s[1]) + 1 < y < max(r[1], s[1]) - 1


def overlap(s1, s2, tol: float = 6) -> float:
    (u, v), (r, s) = s1, s2
    if is_h(u, v) and is_h(r, s) and abs(u[1] - r[1]) < tol:
        a, b = max(min(u[0], v[0]), min(r[0], s[0])), min(max(u[0], v[0]), max(r[0], s[0]))
        return max(0.0, b - a)
    if not is_h(u, v) and not is_h(r, s) and abs(u[0] - r[0]) < tol:
        a, b = max(min(u[1], v[1]), min(r[1], s[1])), min(max(u[1], v[1]), max(r[1], s[1]))
        return max(0.0, b - a)
    return 0.0


def simplify(pts: list) -> list | None:
    """Drop duplicate and collinear points; None if the path doubles back on itself."""
    out: list = []
    for p in pts:
        p = (round(p[0], 1), round(p[1], 1))
        if not out or abs(out[-1][0] - p[0]) > 0.5 or abs(out[-1][1] - p[1]) > 0.5:
            out.append(p)
    i = 1
    while i < len(out) - 1:
        a, b, c = out[i - 1], out[i], out[i + 1]
        if (abs(a[0] - b[0]) < 0.5 and abs(b[0] - c[0]) < 0.5) or (abs(a[1] - b[1]) < 0.5 and abs(b[1] - c[1]) < 0.5):
            if (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]) < 0:
                return None
            out.pop(i)
        else:
            i += 1
    return out if all(abs(u[0] - v[0]) < 0.5 or abs(u[1] - v[1]) < 0.5 for u, v in zip(out, out[1:])) else None


def assign_anchors(edges: list[Edge]) -> None:
    """Spread the arrows that share a side of a node, ordered to avoid crossings. Left/right attach to the
    image itself; top/bottom to the whole node (so arrows never cross a caption)."""
    slots: dict[tuple[int, str], list] = defaultdict(list)
    for e in edges:
        slots[(id(e.a), e.s)].append((e, "a"))
        slots[(id(e.b), e.t)].append((e, "b"))
    for (_, side), items in slots.items():
        e0, end0 = items[0]
        node = e0.a if end0 == "a" else e0.b

        def other(item, side=side):
            e, end = item
            o = e.b if end == "a" else e.a
            return o.cy if side in ("left", "right") else o.cx

        items.sort(key=other)
        x0, y0, x1, y1 = node.body
        for i, (e, end) in enumerate(items):
            f = (i + 1) / (len(items) + 1)
            p = {"left": (x0, y0 + f * (y1 - y0)), "right": (x1, y0 + f * (y1 - y0)),
                 "top": (x0 + f * (x1 - x0), node.y), "bottom": (x0 + f * (x1 - x0), node.y + node.h)}[side]
            if end == "a":
                e.pa = p
            else:
                e.pb = p


def stub_end(node: Node, p: tuple, side: str, extra: float) -> tuple:
    dx, dy = DIRS[side]
    clear = 0.0
    if side in ("left", "right"):
        clear = (node.body[0] - node.rect[0]) if side == "left" else (node.rect[2] - node.body[2])
    d = clear + STUB + extra
    return p[0] + dx * d, p[1] + dy * d


def route(e: Edge, nodes: list[Node], xs: list[float], ys: list[float], others: list) -> None:
    p, q = e.pa, e.pb
    p1 = stub_end(e.a, p, e.s, ARROW if e.arrow == "both" else 0)
    q1 = stub_end(e.b, q, e.t, ARROW if e.arrow != "none" else 0)
    cands = [[p1, q1], [p1, (q1[0], p1[1]), q1], [p1, (p1[0], q1[1]), q1]]
    cands += [[p1, (x, p1[1]), (x, q1[1]), q1] for x in xs]
    cands += [[p1, (p1[0], y), (q1[0], y), q1] for y in ys]
    for x in xs:
        for y in ys:
            cands.append([p1, (x, p1[1]), (x, y), (q1[0], y), q1])
            cands.append([p1, (p1[0], y), (x, y), (x, q1[1]), q1])
    best, best_cost = None, math.inf
    for c in cands:
        pts = simplify([p, *c, q])
        if not pts:
            continue
        segs = list(zip(pts, pts[1:]))
        cost = 6.0 * (len(pts) - 2) + 0.02 * sum(abs(u[0] - v[0]) + abs(u[1] - v[1]) for u, v in segs)
        for n in nodes:
            r = (n.rect[0] - 4, n.rect[1] - 4, n.rect[2] + 4, n.rect[3] + 4)
            for i, (u, v) in enumerate(segs):
                if (i == 0 and n is e.a) or (i == len(segs) - 1 and n is e.b):
                    continue
                if seg_hits_rect(u, v, r):
                    cost += 1000
        for s in segs:
            for o in others:
                cost += 40 * crosses(s, o) + 4 * overlap(s, o)
        if cost < best_cost:
            best, best_cost = pts, cost
    e.pts, e.cost = best or [p, q], best_cost


# ------------------------------------------------------------------- labels --

def area(a, b) -> float:
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def place_label(e: Edge, nodes: list[Node], taken: list, others: list) -> bool:
    """Put the label on the edge where it hides nothing; False if every spot collides."""
    w, h = label_size(e.label)
    segs = sorted(zip(e.pts, e.pts[1:]), key=lambda s: -(abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1])))
    spots = []
    for u, v in segs:
        for f in (0.5, 0.35, 0.65, 0.2, 0.8):
            x, y = u[0] + (v[0] - u[0]) * f, u[1] + (v[1] - u[1]) * f
            if is_h(u, v):
                spots.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2))
            else:
                spots += [(x + 8, y - h / 2, x + 8 + w, y + h / 2), (x - 8 - w, y - h / 2, x - 8, y + h / 2)]
    best, best_cost = None, math.inf
    for rank, r in enumerate(spots):
        hit = sum(area(r, (n.rect[0] - 6, n.rect[1] - 6, n.rect[2] + 6, n.rect[3] + 6)) for n in nodes)
        hit += sum(area(r, t) for t in taken)
        cost = 1000 * hit + 300 * sum(seg_hits_rect(u, v, r) for u, v in others) + rank
        if cost < best_cost:
            best, best_cost = r, cost
    e.box = best
    return best_cost < 1000


# ------------------------------------------------------------------- draw --

def dashed_line(d, u, v, color, width: int, dash: float = 11, gap: float = 7) -> None:
    length = math.dist(u, v)
    if length == 0:
        return
    ux, uy = (v[0] - u[0]) / length, (v[1] - u[1]) / length
    t = 0.0
    while t < length:
        e = min(t + dash, length)
        d.line([(u[0] + ux * t, u[1] + uy * t), (u[0] + ux * e, u[1] + uy * e)], fill=color, width=width)
        t = e + gap


def polyline(d, pts, color, width: int, dashed: bool) -> None:
    for u, v in zip(pts, pts[1:]):
        if dashed:
            dashed_line(d, u, v, color, width)
        else:
            d.line([u, v], fill=color, width=width)
    if not dashed:
        r = width / 2 - 0.5
        for x, y in pts[1:-1]:
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)


def arrowhead(d, tip, frm, color) -> None:
    ang = math.atan2(tip[1] - frm[1], tip[0] - frm[0])
    left = (tip[0] - ARROW * math.cos(ang) + 7 * math.sin(ang), tip[1] - ARROW * math.sin(ang) - 7 * math.cos(ang))
    right = (tip[0] - ARROW * math.cos(ang) - 7 * math.sin(ang), tip[1] - ARROW * math.sin(ang) + 7 * math.cos(ang))
    d.polygon([tip, left, right], fill=color)


def trimmed(pts: list, start: bool, end: bool) -> list:
    """Shorten the ends under arrowheads so the line doesn't poke through the tip."""
    pts = [list(p) for p in pts]
    for idx, nxt, on in ((0, 1, start), (-1, -2, end)):
        if on:
            (x, y), (nx, ny) = pts[idx], pts[nxt]
            length = math.dist((x, y), (nx, ny)) or 1
            pts[idx] = [x + (nx - x) / length * (ARROW - 3), y + (ny - y) / length * (ARROW - 3)]
    return [tuple(p) for p in pts]


def dashed_rect(d, r, color, width: int = 2) -> None:
    x0, y0, x1, y1 = r
    for u, v in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        dashed_line(d, u, v, color, width)


def draw_highlights(d, n: Node, texts: Texts) -> None:
    x0, y0, x1, y1 = n.body
    for hl in n.spec.get("highlights") or []:
        b = manuals.parse_box(hl.get("box"))
        color = color_of(hl.get("color"), ACCENT)
        r = [x0 + b[0] * (x1 - x0), y0 + b[1] * (y1 - y0), x0 + b[2] * (x1 - x0), y0 + b[3] * (y1 - y0)]
        if hl.get("shape", "box") == "circle":
            d.ellipse(r, outline=color, width=4)
        else:
            d.rounded_rectangle(r, radius=6, outline=color, width=4)
        lines = texts.lines(hl.get("label"), SIZE["mark"], True, WHITE)
        if lines:
            w, h = measure(lines)
            w, h = w + 12, h + 6
            lx = min(max(r[0], x0), x1 - w) if w < x1 - x0 else r[0]
            ly = r[3] + 6 if r[3] + 6 + h <= y1 else (r[1] - 6 - h if r[1] - 6 - h >= y0 else r[3] - h - 4)
            d.rounded_rectangle([lx, ly, lx + w, ly + h], radius=5, fill=color)
            draw_lines(d, lines, lx + 6, ly + 2, align="left")


def compose(spec: dict, base: Path, registry: list[dict]) -> tuple[Image.Image, list[str]]:
    texts, used, warnings = Texts(), [], []
    if not isinstance(spec, dict):
        raise SpecError("the spec must be a mapping with `nodes` (and usually `edges`)")
    nodes, edges, groups = build(spec, base, registry, texts, used)
    direction = str(spec.get("direction", "LR")).upper()
    if direction not in ("LR", "TB"):
        raise SpecError("direction must be LR or TB")
    lr = direction == "LR"
    assign_cells(nodes, edges, lr)
    for e in edges:
        pick_sides(e, lr)
    ncol, nrow = max(n.col for n in nodes) + 1, max(n.row for n in nodes) + 1
    hg, vg = initial_gaps(spec, edges, groups, ncol, nrow)
    for _ in range(10):
        gaps_x, gaps_y, (gx0, gy0, gx1, gy1) = place(nodes, ncol, nrow, hg, vg)
        xs, ys = lanes(gaps_x, gx0, gx1), lanes(gaps_y, gy0, gy1)
        assign_anchors(edges)
        routed: list = []
        for e in sorted(edges, key=lambda e: abs(e.a.col - e.b.col) + abs(e.a.row - e.b.row)):
            route(e, nodes, xs, ys, routed)
            routed += list(zip(e.pts, e.pts[1:]))
        taken = [g.label_rect() for g in groups if g.label]
        stuck = []
        for e in edges:
            if e.label:
                mine = set(zip(e.pts, e.pts[1:]))
                if not place_label(e, nodes, taken, [s for s in routed if s not in mine]):
                    stuck.append(e)
                taken.append(e.box)
        if not stuck:
            break
        for e in stuck:
            for g in range(*sorted((e.a.col, e.b.col))):
                hg[g] += 40
            for g in range(*sorted((e.a.row, e.b.row))):
                vg[g] += 30
            if e.a.col == e.b.col and e.a.row == e.b.row:
                break
    else:
        warnings += [f"label of {e.a.id} → {e.b.id} overlaps something; try explicit col/row or a shorter label"
                     for e in stuck]
    warnings += [f"arrow {e.a.id} → {e.b.id} passes through a node; try explicit col/row or from_side/to_side"
                 for e in edges if e.cost >= 1000]
    for g in groups:
        inside = [n.id for n in nodes if n not in g.nodes and area(n.rect, g.rect())]
        if inside:
            warnings.append(f"group {''.join(ln.text for ln in g.label)!r} also covers {', '.join(inside)}")

    # canvas: everything drawn, plus margins, title and sources
    boxes = [n.rect for n in nodes] + [g.rect() for g in groups] + [e.box for e in edges if e.box]
    pts = [p for e in edges for p in e.pts]
    minx = min([b[0] for b in boxes] + [p[0] for p in pts]) - 8
    miny = min([b[1] for b in boxes] + [p[1] for p in pts]) - 8
    maxx = max([b[2] for b in boxes] + [p[0] for p in pts]) + 8
    maxy = max([b[3] for b in boxes] + [p[1] for p in pts]) + 8
    title = texts.lines(spec.get("title"), SIZE["title"], True)
    subtitle = texts.lines(spec.get("subtitle"), SIZE["subtitle"], False, MUTED)
    width = max(maxx - minx, measure(title)[0], measure(subtitle)[0]) + 2 * MARGIN
    src = ([f"Drawings: {', '.join(dict.fromkeys(used))} (official manuals; see gear/manuals.yaml)"]
           if used and spec.get("auto_sources", True) else []) + [str(s) for s in spec.get("sources") or []]
    src_rows = [row for s in src for row in wrap(s, SIZE["source"], width - 2 * MARGIN)]
    src_lines = texts.lines("\n".join(src_rows), SIZE["source"], False, MUTED)
    head = measure(title)[1] + measure(subtitle)[1] + (24 if title or subtitle else 0)
    foot = measure(src_lines)[1] + (24 if src_lines else 0)
    height = MARGIN + head + (maxy - miny) + foot + MARGIN
    ox, oy = MARGIN - minx + (width - 2 * MARGIN - (maxx - minx)) / 2, MARGIN + head - miny

    def sh(r):
        return r[0] + ox, r[1] + oy, r[2] + ox, r[3] + oy

    for n in nodes:
        n.x, n.y = n.x + ox, n.y + oy
    for e in edges:
        e.pts = [(x + ox, y + oy) for x, y in e.pts]
        e.box = sh(e.box) if e.box else None

    canvas = Image.new("RGB", (math.ceil(width), math.ceil(height)), WHITE)
    d = ImageDraw.Draw(canvas)
    draw_lines(d, title + subtitle, MARGIN, MARGIN, align="left")
    for g in groups:
        d.rounded_rectangle(g.rect(), radius=14, fill=GROUP_FILL, outline=g.color, width=2)
        lx0, ly0, _, _ = g.label_rect()
        draw_lines(d, g.label, lx0, ly0, align="left")
    for e in edges:
        polyline(d, trimmed(e.pts, e.arrow == "both", e.arrow != "none"), e.color, 3, e.dashed)
    for n in nodes:
        x0, y0, x1, y1 = n.body
        if n.img is not None:
            canvas.paste(n.img, (round(x0), round(y0)))
            d.rectangle([x0 - 1, y0 - 1, x1, y1], outline=IMG_LINE, width=1)
            draw_lines(d, n.lines, n.cx, y1 + CAPTION_GAP)
            draw_highlights(d, n, texts)
        else:
            dashed = n.spec.get("style") == "dashed"
            d.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=BOX_FILL if not dashed else WHITE,
                                outline=None if dashed else color_of(n.spec.get("color")), width=2)
            if dashed:
                dashed_rect(d, (x0, y0, x1, y1), color_of(n.spec.get("color"), MUTED))
            draw_lines(d, n.lines, n.cx, y0 + (y1 - y0 - measure(n.lines)[1]) / 2)
    for e in edges:
        if e.arrow != "none":
            arrowhead(d, e.pts[-1], e.pts[-2], e.color)
        if e.arrow == "both":
            arrowhead(d, e.pts[0], e.pts[1], e.color)
        if e.box:
            d.rounded_rectangle(e.box, radius=6, fill=WHITE, outline=e.color, width=2)
            draw_lines(d, e.label, (e.box[0] + e.box[2]) / 2, e.box[1] + LABEL_PAD[1])
    draw_lines(d, src_lines, MARGIN, height - MARGIN - measure(src_lines)[1], align="left")
    return canvas, warnings + texts.warnings


def load_spec(path: str) -> tuple[dict, Path, str]:
    if path == "-":
        raw, base, stem = sys.stdin.read(), Path.cwd(), "diagram"
    else:
        p = Path(path)
        if not p.exists():
            raise SpecError(f"spec not found: {p}")
        raw, base, stem = p.read_text(encoding="utf-8"), p.resolve().parent, p.stem
    try:
        spec = json.loads(raw) if raw.lstrip().startswith("{") else yaml.safe_load(raw)
    except (ValueError, yaml.YAMLError) as e:
        raise SpecError(f"can't parse the spec: {e}") from None
    return spec, base, stem


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("spec", help="diagram spec (YAML/JSON), or - for stdin")
    p.add_argument("-o", "--output", help="PNG to write (default out/visuals/<spec name>.png)")
    p.add_argument("--registry", help="manuals registry (default gear/manuals.yaml)")
    args = p.parse_args(argv)
    try:
        spec, base, stem = load_spec(args.spec)
        image, warnings = compose(spec, base, manuals.load_registry(args.registry))
    except (SpecError, manuals.RegistryError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except manuals.FetchError as e:
        print(f"BROKEN: {e.reason}: {e.url} (run `manuals.py check`)", file=sys.stderr)
        return 2
    path = Path(args.output) if args.output else manuals.visuals_dir() / f"{stem}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    manuals.announce(path, f"{image.width}x{image.height}px")
    for w in warnings:
        print(f"warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
