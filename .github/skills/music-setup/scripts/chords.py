#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf>=1.24", "pillow>=10.1", "pyyaml>=6"]
# ///
r"""Chord diagrams (chord boxes) for the stringed instruments, plus plain-text tab to paste into chat.

  uv run .github/skills/music-setup/scripts/chords.py "E7#5=x 7 x 7 9 8" "A7#5=x 0 x 0 2 1" --instrument bass-vi
  uv run .github/skills/music-setup/scripts/chords.py "Am=x02210" "C/G=332010" --title "Open chords"
  uv run .github/skills/music-setup/scripts/chords.py "D=x x 0 2 3 2" --tuning "D A D G B E" -o out/visuals/d.png

Each chord is NAME=FRETS, low string first: x = don't play it, 0 = open, numbers = fret. Separate the
frets with spaces or commas (a run of single digits like x02210 works too). Writes a PNG (default
out/visuals/<title>.png, gitignored) and prints its path, then a plain-text tab block (tab tables
render badly in chat; paste this in a code block instead).

Checks every shape against its name (spellings are general music theory) and prints a warning when
a note isn't in the chord or a chord tone is missing (a missing perfect 5th is fine). Unknown chord
names are drawn without the check. Roots are drawn in orange.

Also warns when two neighbouring notes are closer than a perfect 4th below C3: a rule of thumb
(not from any manual) for voicings that sound muddy. On the Bass VI, playing the same shape 12
frets higher, or leaving out a low string, usually fixes it.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manuals  # noqa: E402  (lives next to this script)

# Open-string pitches, low string first. Sources: gear/bass-vi.md (one octave below guitar).
INSTRUMENTS = {
    "guitar": "E2 A2 D3 G3 B3 E4",   # Jaguar, Telecaster, Ibanez acoustic
    "bass-vi": "E1 A1 D2 G2 B2 E3",
    "bass": "E1 A1 D2 G2",
}
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLATS = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#", "Cb": "B", "Fb": "E", "E#": "F", "B#": "C"}
# Intervals in semitones above the root.
QUALITIES = {
    ("", "maj", "M"): (0, 4, 7),
    ("m", "min", "-"): (0, 3, 7),
    ("5",): (0, 7),
    ("dim", "°", "o"): (0, 3, 6),
    ("aug", "+", "#5"): (0, 4, 8),
    ("sus2",): (0, 2, 7),
    ("sus4", "sus"): (0, 5, 7),
    ("6",): (0, 4, 7, 9),
    ("m6",): (0, 3, 7, 9),
    ("7",): (0, 4, 7, 10),
    ("maj7", "M7", "Δ", "Δ7"): (0, 4, 7, 11),
    ("m7", "min7", "-7"): (0, 3, 7, 10),
    ("mmaj7", "m(maj7)", "mM7"): (0, 3, 7, 11),
    ("m7b5", "ø", "ø7"): (0, 3, 6, 10),
    ("dim7", "°7", "o7"): (0, 3, 6, 9),
    ("7#5", "aug7", "+7", "7+5", "7+", "7aug"): (0, 4, 8, 10),
    ("7b5",): (0, 4, 6, 10),
    ("maj7#5", "+maj7", "augmaj7"): (0, 4, 8, 11),
    ("7sus4", "7sus"): (0, 5, 7, 10),
    ("add9",): (0, 2, 4, 7),
    ("9",): (0, 2, 4, 7, 10),
    ("maj9",): (0, 2, 4, 7, 11),
    ("m9",): (0, 2, 3, 7, 10),
    ("7b9",): (0, 1, 4, 7, 10),
    ("7#9",): (0, 3, 4, 7, 10),
}
SUFFIXES = {s: iv for names, iv in QUALITIES.items() for s in names}
MUDDY_BELOW = 48   # C3 (MIDI note number)
MUDDY_GAP = 5      # semitones: anything closer than a perfect 4th

INK = (40, 40, 40)
MUTED = (120, 120, 120)
DOT = (31, 78, 156)
ROOT = (228, 87, 46)
WARN = (190, 60, 30)
WHITE = (255, 255, 255)


class ChordError(Exception):
    pass


def pitch(name: str) -> tuple[int, int | None]:
    """'G#2' -> (pitch class 8, MIDI 44); 'Bb' -> (10, None)."""
    m = re.fullmatch(r"([A-Ga-g])([#b♯♭]?)(-?\d)?", name.strip())
    if not m:
        raise ChordError(f"not a note name: {name!r}")
    note = m[1].upper() + m[2].replace("♯", "#").replace("♭", "b")
    pc = NAMES.index(FLATS.get(note, note))
    if m[3] is None:
        return pc, None
    octave = int(m[3])
    # Cb4 is B3 and B#3 is C4: they cross into the neighbouring octave
    return pc, 12 * (octave + 1) + pc + (-12 if note == "Cb" else 12 if note == "B#" else 0)


def parse_tuning(text: str) -> list[tuple[int, int | None]]:
    strings = [pitch(n) for n in re.split(r"[\s,]+", text.strip()) if n]
    if not 3 <= len(strings) <= 8:
        raise ChordError(f"tuning needs 3–8 strings, got {len(strings)}: {text!r}")
    return strings


def parse_frets(text: str, strings: int) -> list[int | None]:
    t = text.strip()
    parts = [p for p in re.split(r"[\s,]+", t) if p]
    if len(parts) == 1 and len(t) == strings:
        parts = list(t)
    if len(parts) != strings:
        raise ChordError(f"{text!r}: {len(parts)} frets for {strings} strings (low string first)")
    frets: list[int | None] = []
    for p in parts:
        if p.lower() in ("x", "-"):
            frets.append(None)
        elif p.isdigit() and int(p) <= 24:
            frets.append(int(p))
        else:
            raise ChordError(f"{text!r}: {p!r} isn't a fret (use x, 0 or 1–24)")
    if all(f is None for f in frets):
        raise ChordError(f"{text!r}: every string is muted")
    return frets


def parse_name(name: str) -> tuple[int, tuple[int, ...] | None, int | None]:
    """'E7#5' -> (root pc, intervals or None if unknown, slash-bass pc or None)."""
    n = name.strip().replace("♯", "#").replace("♭", "b")
    m = re.fullmatch(r"([A-G][#b]?)(.*?)(?:/([A-G][#b]?))?", n)
    if not m:
        raise ChordError(f"chord name must start with a note A–G: {name!r}")
    root = pitch(m[1])[0]
    intervals = SUFFIXES.get(m[2]) or SUFFIXES.get(re.sub(r"[()\s]", "", m[2]))
    return root, intervals, (pitch(m[3])[0] if m[3] else None)


def note_name(pc: int) -> str:
    return NAMES[pc % 12]


@dataclass
class Chord:
    name: str
    frets: list[int | None]
    notes: list[str | None]         # per string, None = muted
    root: int | None
    warnings: list[str] = field(default_factory=list)
    muddy: bool = False

    @property
    def tab(self) -> str:
        return " ".join("x" if f is None else str(f) for f in self.frets)


def analyse(name: str, frets: list[int | None], tuning: list[tuple[int, int | None]]) -> Chord:
    pcs = [None if f is None else (tuning[i][0] + f) % 12 for i, f in enumerate(frets)]
    root, intervals, bass = parse_name(name)
    chord = Chord(name, frets, [None if p is None else note_name(p) for p in pcs], root)
    played = {p for p in pcs if p is not None}
    if intervals is None:
        chord.warnings.append(f"{name}: unknown chord type, notes not checked")
    else:
        tones = {(root + i) % 12 for i in intervals}
        extra = played - tones - ({bass} if bass is not None else set())
        if extra:
            chord.warnings.append(f"{name}: {', '.join(note_name(p) for p in sorted(extra))} not in the chord "
                                  f"({' '.join(note_name(root + i) for i in intervals)})")
        missing = [i for i in intervals if (root + i) % 12 not in played and i != 7]
        if missing:
            chord.warnings.append(f"{name}: missing {', '.join(note_name(root + i) for i in missing)}")
        lowest = next(p for p in pcs if p is not None)
        if bass is not None and lowest != bass:
            chord.warnings.append(f"{name}: lowest note is {note_name(lowest)}, not {note_name(bass)}")
    midi = sorted(tuning[i][1] + f for i, f in enumerate(frets) if f is not None and tuning[i][1] is not None)
    for lo, hi in zip(midi, midi[1:]):
        if lo < MUDDY_BELOW and hi - lo < MUDDY_GAP:
            chord.muddy = True
            chord.warnings.append(f"{name}: {midi_name(lo)}–{midi_name(hi)} are close together down low, "
                                  "may sound muddy (rule of thumb)")
            break
    return chord


def midi_name(m: int) -> str:
    return f"{note_name(m)}{m // 12 - 1}"


# ------------------------------------------------------------------ drawing --

def draw_chord(chord: Chord, tuning_names: list[str], scale: float = 1.0) -> Image.Image:
    s = lambda v: round(v * scale)  # noqa: E731
    strings = len(chord.frets)
    gap, fret_h = s(48), s(56)
    fretted = [f for f in chord.frets if f]
    start = 1 if not fretted or max(fretted) <= 5 else min(fretted)
    rows = max(5, (max(fretted) - start + 1) if fretted else 0)
    grid_w = gap * (strings - 1)
    left, top = s(70), s(130)
    w, h = left + grid_w + s(60), top + rows * fret_h + s(90)
    im = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(im)
    cx = lambda i: left + i * gap  # noqa: E731
    title_font, tab_font = manuals.font(s(30), bold=True), manuals.font(s(22))
    d.text((left + grid_w / 2, s(10)), chord.name, font=title_font, fill=INK, anchor="mt")
    d.text((left + grid_w / 2, s(50)), chord.tab, font=tab_font, fill=MUTED, anchor="mt")
    for i in range(strings):
        d.line([(cx(i), top), (cx(i), top + rows * fret_h)], fill=INK, width=max(1, s(2)))
    for r in range(rows + 1):
        y = top + r * fret_h
        d.line([(left, y), (left + grid_w, y)], fill=INK, width=s(7) if r == 0 and start == 1 else max(1, s(2)))
    if start > 1:
        d.text((left - s(16), top + fret_h / 2), f"{start}fr", font=manuals.font(s(20)), fill=INK, anchor="rm")
    note_font, small = manuals.font(s(19), bold=True), manuals.font(s(15))
    rad = s(17)
    for i, f in enumerate(chord.frets):
        x, y_mark = cx(i), top - s(22)
        if f is None:
            d.line([(x - s(9), y_mark - s(9)), (x + s(9), y_mark + s(9))], fill=INK, width=s(3))
            d.line([(x - s(9), y_mark + s(9)), (x + s(9), y_mark - s(9))], fill=INK, width=s(3))
            continue
        is_root = chord.root is not None and chord.notes[i] == note_name(chord.root)
        colour = ROOT if is_root else DOT
        if f == 0:
            d.ellipse([x - s(11), y_mark - s(11), x + s(11), y_mark + s(11)], outline=colour, width=s(3))
        else:
            y = top + (f - start + 0.5) * fret_h
            d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=colour)
        d.text((x, top + rows * fret_h + s(14)), chord.notes[i], font=note_font, fill=colour, anchor="mt")
    for i, name in enumerate(tuning_names):
        d.text((cx(i), top + rows * fret_h + s(42)), name, font=small, fill=MUTED, anchor="mt")
    if chord.muddy:
        d.text((left + grid_w / 2, h - s(8)), "close low notes: may sound muddy", font=small, fill=WARN, anchor="mb")
    return im


def sheet(chords: list[Chord], tuning_names: list[str], title: str, subtitle: str, cols: int = 3) -> Image.Image:
    cells = [draw_chord(c, tuning_names) for c in chords]
    cols = max(1, min(cols, len(cells)))
    cw, ch = max(c.width for c in cells), max(c.height for c in cells)
    rows = -(-len(cells) // cols)
    head = 100
    im = Image.new("RGB", (cols * cw + 40, head + rows * ch + 20), WHITE)
    d = ImageDraw.Draw(im)
    d.text((im.width / 2, 18), title, font=manuals.font(34, bold=True), fill=INK, anchor="mt")
    d.text((im.width / 2, 62), subtitle, font=manuals.font(18), fill=MUTED, anchor="mt")
    for k, cell in enumerate(cells):
        r, c = divmod(k, cols)
        im.paste(cell, (20 + c * cw + (cw - cell.width) // 2, head + r * ch))
    return im


def build(specs: list[str], tuning_text: str) -> tuple[list[Chord], list[str]]:
    tuning = parse_tuning(tuning_text)
    tuning_names = [note_name(pc) for pc, _ in tuning]
    chords = []
    for spec in specs:
        if "=" not in spec:
            raise ChordError(f"{spec!r}: write chords as NAME=FRETS, e.g. \"E7#5=x 7 x 7 9 8\"")
        name, frets = spec.split("=", 1)
        chords.append(analyse(name.strip(), parse_frets(frets, len(tuning)), tuning))
    return chords, tuning_names


def tab_block(chords: list[Chord], tuning_names: list[str]) -> str:
    width = max(len(c.name) for c in chords)
    cells = [["x" if f is None else str(f) for f in c.frets] for c in chords]
    col = max(len(t) for row in cells + [tuning_names] for t in row)
    row = lambda items: " ".join(f"{t:<{col}}" for t in items).rstrip()  # noqa: E731
    lines = [f"{'':{width}}   {row(tuning_names)}   (low string first; x = don't play, 0 = open)"]
    lines += [f"{c.name:{width}}   {row(cells[k])}" for k, c in enumerate(chords)]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("chords", nargs="+", metavar="NAME=FRETS", help='e.g. "E7#5=x 7 x 7 9 8"')
    tune = p.add_mutually_exclusive_group()
    tune.add_argument("--instrument", choices=sorted(INSTRUMENTS), default="guitar",
                      help="sets the tuning (default guitar)")
    tune.add_argument("--tuning", help='open strings, low first, e.g. "D2 A2 D3 G3 B3 E4" (octaves optional)')
    p.add_argument("--title", help="sheet title (default: the chord names)")
    p.add_argument("--cols", type=int, default=3, help="diagrams per row (default 3)")
    p.add_argument("-o", "--output", help="PNG to write (default out/visuals/<title>.png)")
    args = p.parse_args(argv)
    tuning_text = args.tuning or INSTRUMENTS[args.instrument]
    try:
        chords, tuning_names = build(args.chords, tuning_text)
    except ChordError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    title = args.title or ", ".join(c.name for c in chords)
    label = args.tuning and f"tuning {args.tuning}" or args.instrument
    subtitle = f"{label}  ·  low string on the left  ·  roots in orange  ·  note names under the strings"
    image = sheet(chords, tuning_names, title, subtitle, args.cols)
    stem = re.sub(r"[^a-z0-9]+", "-", title.lower().replace("#", "s")).strip("-")[:60] or "chords"
    path = Path(args.output) if args.output else manuals.visuals_dir() / f"{stem}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    manuals.announce(path, f"{image.width}x{image.height}px")
    print()
    print(tab_block(chords, tuning_names))
    for c in chords:
        for w in c.warnings:
            print(f"warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
