#!/usr/bin/env python3
"""How well would each colour scheme reproduce the rooms? Scored on the
oracle's output (build/rooms): for every playfield cell, the paper colour is
weighted by its unset pixels and the ink by its set ones, BRIGHT ignored
(the BBC's eight colours are the Spectrum's eight). A scheme scores the
fraction of pixels it can show in their own colour.

    python3 tools/colourstats.py
"""
from collections import Counter

NAMES = "black blue red magenta green cyan yellow white".split()


def room_cells(r):
    d = open(f"build/rooms/room_{r:03d}.bin", "rb").read()
    scr, attrs = d[:6144], d[6144:6912]
    cells = []
    for row in range(2, 24):
        for col in range(32):
            a = attrs[row * 32 + col]
            ink, paper = a & 7, (a >> 3) & 7
            on = 0
            for line in range(8):
                y = row * 8 + line
                addr = ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + col
                on += bin(scr[addr]).count("1")
            cells.append((row, paper, ink, 64 - on, on))
    return cells


def weights(cells):
    w = Counter()
    for row, paper, ink, off, on in cells:
        w[paper] += off
        w[ink] += on
    return w


def score_room_palette(cells, fixed=()):
    """Best 4 colours for the room (some fixed), by pixels shown exactly."""
    w = weights(cells)
    pal = list(fixed)
    for c, _ in w.most_common():
        if len(pal) == 4:
            break
        if c not in pal:
            pal.append(c)
    total = sum(w.values())
    good = sum(v for c, v in w.items() if c in pal)
    return good / total, pal


def score_row_palette(cells, fixed):
    """Fixed colours plus the best 4-len(fixed) per character row."""
    rows = {}
    for cell in cells:
        rows.setdefault(cell[0], []).append(cell)
    good = total = 0
    for row, cs in rows.items():
        w = weights(cs)
        pal = list(fixed)
        for c, _ in w.most_common():
            if len(pal) == 4:
                break
            if c not in pal:
                pal.append(c)
        total += sum(w.values())
        good += sum(v for c, v in w.items() if c in pal)
    return good / total


def main():
    tot = Counter()
    worst = []
    for r in range(1, 121):
        cells = room_cells(r)
        s1, pal = score_room_palette(cells)
        s2, _ = score_room_palette(cells, fixed=(6,))
        paper = weights([c for c in cells]).most_common(1)[0][0]
        s3 = score_row_palette(cells, fixed=(paper, 6))
        s4 = score_row_palette(cells, fixed=(paper,))
        tot.update({"room": s1, "room+yellow": s2, "row(paper,yellow)": s3, "row(paper)": s4})
        worst.append((s1, r, [NAMES[c] for c in pal]))
    for k, v in tot.items():
        print(f"{k:20s} {100 * v / 120:6.2f}% of pixels in their own colour (mean over rooms)")
    worst.sort()
    print("worst rooms for a per-room palette:")
    for s, r, pal in worst[:12]:
        print(f"  room {r:3d}: {100 * s:5.1f}%  {pal}")


main()
