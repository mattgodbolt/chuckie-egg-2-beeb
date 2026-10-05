#!/usr/bin/env python3
"""What a 1-bit screen (MODE 4's pixels at 256 x 192, 6K) would cost in
colour, scored like tools/colourstats.py on the oracle's rooms: the share
of playfield pixels shown in their own colour (paper pixels weighted by the
cell's unset pixels, ink by its set ones, BRIGHT ignored).

A 1-bit cell shows its unset pixels in logical 0 and set ones in logical 1;
the drawer may also draw a cell inverted (paper as 1, ink as 0), so each
cell takes the better of the two. Schemes:
  mono       black and white everywhere
  room       the best two colours for the room
  row1       logical 0 fixed for the room, logical 1 per character row
             (8 ULA writes in each row's blank: 22 interrupts a frame)
  row2       both per character row (16 writes a row: too many for one blank)
  bands3     the best two colours in each of at most 3 bands (2 splits, as
             now), rows chosen by brute force
The 4-colour scheme the port uses scores 99.48% (decision 24).

Run from the repository root: python3 <this>.
"""
import sys
from itertools import combinations

sys.path.insert(0, "tools")
from colourstats import room_cells  # noqa: E402


def cell_score(cell, c0, c1):
    row, paper, ink, off, on = cell
    a = off * (paper == c0) + on * (ink == c1)
    b = off * (paper == c1) + on * (ink == c0)
    return max(a, b)


def best_pair(cells, fixed0=None):
    best = (-1, None)
    for c0 in range(8) if fixed0 is None else [fixed0]:
        for c1 in range(8):
            if c1 == c0:
                continue
            s = sum(cell_score(c, c0, c1) for c in cells)
            if s > best[0]:
                best = (s, (c0, c1))
    return best


def by_row(cells):
    rows = {}
    for c in cells:
        rows.setdefault(c[0], []).append(c)
    return rows


def ink_score(cells, c0, c1):
    """Set (ink) pixels shown in their own colour, cells drawn the better way."""
    good = 0
    for row, paper, ink, off, on in cells:
        a = off * (paper == c0) + on * (ink == c1)
        b = off * (paper == c1) + on * (ink == c0)
        good += on * (ink == c1) if a >= b else on * (ink == c0)
    return good


ink_tot = dict(room=0, row1=0)
ink_pix = 0
totals = dict(mono=0, room=0, row1=0, row2=0, bands3=0)
pix = 0
worst = dict((k, (1, 0)) for k in totals)
for r in range(1, 121):
    cells = room_cells(r)
    n = len(cells) * 64
    pix += n
    rows = by_row(cells)
    s = {}
    s["mono"] = sum(cell_score(c, 0, 7) for c in cells)
    s["room"], pair = best_pair(cells)
    ink_pix += sum(c[4] for c in cells)
    ink_tot["room"] += ink_score(cells, *pair)
    best0 = max(range(8), key=lambda c0: sum(best_pair(rc, c0)[0] for rc in rows.values()))
    ink_tot["row1"] += sum(ink_score(rc, *best_pair(rc, best0)[1]) for rc in rows.values())
    # row1: logical 0 fixed for the room, logical 1 free per row
    s["row1"] = max(sum(best_pair(rc, c0)[0] for rc in rows.values()) for c0 in range(8))
    s["row2"] = sum(best_pair(rc)[0] for rc in rows.values())
    # bands3: up to 3 bands of consecutive rows (rows 2-23), best pair in each
    keys = sorted(rows)
    pre = {}

    def band(a, b):
        if (a, b) not in pre:
            pre[a, b] = best_pair([c for k in keys[a:b] for c in rows[k]])[0]
        return pre[a, b]

    nk = len(keys)
    best = band(0, nk)
    for i in range(1, nk):
        best = max(best, band(0, i) + band(i, nk))
        for j in range(i + 1, nk):
            best = max(best, band(0, i) + band(i, j) + band(j, nk))
    s["bands3"] = best
    for k, v in s.items():
        totals[k] += v
        if v / n < worst[k][0]:
            worst[k] = (v / n, r)
    print(f"room {r:3d}: " + "  ".join(f"{k} {100*v/n:5.1f}" for k, v in s.items()), flush=True)

print(f"\nInk (set) pixels in their own colour: room {100*ink_tot['room']/ink_pix:.1f}%, row1 {100*ink_tot['row1']/ink_pix:.1f}%")
print("\nAll 120 rooms, playfield pixels in their own colour:")
for k, v in totals.items():
    print(f"  {k:7s} {100*v/pix:5.2f}%   worst room {worst[k][1]} at {100*worst[k][0]:.1f}%")
