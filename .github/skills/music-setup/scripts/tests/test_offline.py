# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest>=8", "pymupdf>=1.24", "pillow>=10.1", "pyyaml>=6"]
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


def test_short_terms_match_whole_words_only():
    pages = ["insert the cable into the inlet; the instrument input", "plug it in: line in"]
    assert [h["page"] for h in manuals.search_pages(pages, "in")] == [2]
    assert [h["page"] for h in manuals.search_pages(pages, "line in")] == [2]
    assert [h["page"] for h in manuals.search_pages(pages, "instr")] == [1]
    assert "**in**sert" not in manuals.search_pages(pages, "in")[0]["snippet"]


def test_changed_pdf_suggests_version_from_new_title():
    e = entry(version="firmware 1.7.0 (REV 10)", verified={"date": "2026-10-10", "sha256": "a" * 64, "pages": 78})
    meta = {"sha256": "b" * 64, "bytes": 1, "pages": 79, "doc_title": "OP-1 field user guide firmware 1.6.0 (REV 9)"}
    (finding,) = manuals.compare(e, manuals.Cached(e, Path("x.pdf"), meta, "downloaded"))
    assert finding.status == "CHANGED" and finding.updates["version"] == meta["doc_title"]
    same = dict(meta, doc_title="OP-1 field user guide firmware 1.7.0 (REV 10)")
    (finding,) = manuals.compare(e, manuals.Cached(e, Path("x.pdf"), same, "downloaded"))
    assert "version" not in finding.updates


# ------------------------------------------------------------------ visuals --

import diagram  # noqa: E402
from PIL import Image  # noqa: E402

DIAGRAMS = manuals.REPO_ROOT / "setup" / "diagrams"


def test_parse_box_and_relative_box():
    assert manuals.parse_box("0.1,0.2,0.3,0.4") == (0.1, 0.2, 0.3, 0.4)
    for bad in ("0.5,0.2,0.3,0.4", "0,0,1", "a,b,c,d", [0, 0, 1.5, 1]):
        with pytest.raises(manuals.RegistryError):
            manuals.parse_box(bad)
    assert manuals.relative_box((0.5, 0.5, 0.6, 0.6), (0.5, 0.5, 1, 1)) == pytest.approx((0, 0, 0.2, 0.2))
    assert manuals.relative_box((0.1, 0.1, 0.2, 0.2), (0.5, 0.5, 1, 1)) is None


def test_grid_overlay_adds_labelled_margins():
    im = Image.new("RGB", (400, 300), "white")
    out = manuals.grid_overlay(im, (0.5, 0.25, 1.0, 0.75))
    assert out.width > 400 and out.height > 300


def test_font_has_the_arrows_and_dashes():
    assert manuals.missing_glyphs("main out → line in — 3.5 mm · ↔ µ Ω") == set()
    assert manuals.missing_glyphs("ok ✓") == {"✓"}


def test_compose_text_only_diagram():
    spec = {"title": "t — x", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B", "note": "n"},
                                        {"id": "c", "label": "C"}],
            "edges": [{"from": "a", "to": "b", "label": "a → b"}, {"from": "b", "to": "c", "style": "dashed"}],
            "groups": [{"label": "G", "nodes": ["b", "c"]}], "sources": ["somewhere"]}
    image, warnings = diagram.compose(spec, Path("."), [])
    assert image.width > 300 and image.height > 100 and warnings == []


def test_compose_reports_unknown_ids_and_bad_values():
    with pytest.raises(diagram.SpecError, match="unknown node id 'nope'.*known: a"):
        diagram.compose({"nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "nope"}]}, Path("."), [])
    with pytest.raises(diagram.SpecError, match="both in col 0, row 0"):
        diagram.compose({"nodes": [{"id": "a", "col": 0, "row": 0}, {"id": "b", "col": 0, "row": 0}]},
                        Path("."), [])
    with pytest.raises(diagram.SpecError, match="unknown color"):
        diagram.compose({"nodes": [{"id": "a"}, {"id": "b"}],
                         "edges": [{"from": "a", "to": "b", "color": "nocolor"}]}, Path("."), [])


def test_compose_local_image_flattens_rotates_and_highlights(tmp_path):
    Image.new("RGBA", (200, 100), (0, 0, 0, 0)).save(tmp_path / "clear.png")
    spec = {"nodes": [{"id": "img", "label": "drawing", "image": {"file": "clear.png", "box": [0, 0, 0.5, 1]},
                       "rotate": 90, "height": 80, "highlights": [{"box": [0.1, 0.1, 0.5, 0.5], "label": "here"}]},
                      {"id": "t", "label": "box ✓"}],
            "edges": [{"from": "img", "to": "t", "label": "→", "arrow": "both"}]}
    image, warnings = diagram.compose(spec, tmp_path, [])
    assert any("✓" in w for w in warnings) and image.width > 100
    assert manuals.flatten(Image.new("RGBA", (2, 2), (0, 0, 0, 0))).getpixel((0, 0)) == (255, 255, 255)


def test_labels_stay_off_nodes():
    spec = {"nodes": [{"id": "a", "label": "Amp", "col": 0, "row": 0}, {"id": "tx", "label": "TX-6", "col": 1, "row": 1},
                      {"id": "o", "label": "OP-XY", "col": 0, "row": 1}, {"id": "b", "label": "OB-4", "col": 2, "row": 1}],
            "edges": [{"from": "a", "to": "tx", "label": "line / DI out, 1/4in → 3.5 mm\nnever the speaker out"},
                      {"from": "o", "to": "tx", "label": "3.5 mm stereo"},
                      {"from": "tx", "to": "b", "label": "main out → line in"}]}
    _, warnings = diagram.compose(spec, Path("."), [])
    assert warnings == []


@pytest.mark.parametrize("path", sorted(DIAGRAMS.glob("*.yaml")), ids=lambda p: p.name)
def test_recipes_reference_registered_manual_pages(path):
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    registry = {e["id"]: e for e in manuals.load_registry()}
    ids = {n["id"] for n in spec["nodes"]}
    for e in spec.get("edges", []):
        assert e["from"] in ids and e["to"] in ids
    for n in spec["nodes"]:
        img = n.get("image")
        if isinstance(img, dict) and "manual" in img:
            assert img["manual"] in registry, img
            assert 1 <= img["page"] <= registry[img["manual"]]["verified"]["pages"]
            manuals.parse_box(img.get("box"))
        for hl in n.get("highlights", []):
            manuals.parse_box(hl["box"])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
