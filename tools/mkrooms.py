#!/usr/bin/env python3
"""Extract the room data and tile font from the original, and choose each
room's four colours.

    .venv/bin/python tools/mkrooms.py [--snap shots/zx_start.z80]

Writes, all committed (the build never runs this):
    src/data/roomdata.bin   the original's room data, &AA5C-&DFA1, verbatim
    src/data/tiles.bin      the tile font, codes &20-&5B (8 bytes each)
    src/data/roomoffsets.txt  where each room starts in roomdata.bin
                            (tools/packrooms.py reads it)
    src/data/rooms.6502     the palettes the rooms use (their first band's),
                            each once: 30 for 120 rooms
    src/data/roompal.txt    each room's palette number in rooms.6502
                            (tools/packrooms.py puts it in the room's
                            first byte, beside its paper)
    src/data/bands.6502     the bands below (decision 15), in sideways RAM

The palette (decision 2): MODE 1 shows four colours, so each room gets the
four that cover most of its pixels, with the room's background paper as
logical colour 0, Harry's colour as logical 3, and every Spectrum colour
mapped to one of the four. Harry's colour is yellow (decision 6: he is
yellow on the Spectrum), or white in a room where white shows WHITE_GAIN
more of the room's pixels in their own colour: Spectrum yellow, which he
is drawn in, then maps to white there. The
mapping is chosen by brute force to show the most pixels in their own
colour, under two hard rules: in every cell the room draws, ink and paper
must stay different; and every colour but the background must differ from
the background, so anything drawn later in any colour stays visible. The
bands (decision 15) add a third: no split where an object crossing it would
change colour.
Pixel counts come from the oracle (tools/zxrooms.py, build/rooms).
"""
import argparse
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from zx import Spectrum  # noqa: E402

ROOM_PTRS = 0xA96A
DATA_START, DATA_END = 0xAA5C, 0xDFA2
CHARS = 0x73B8
FIRST_TILE, LAST_TILE = 0x20, 0x5B
NAMES = "black blue red magenta green cyan yellow white".split()
# Spectrum colour order is GRB-ish (0 black, 1 blue, 2 red, 3 magenta, 4 green,
# 5 cyan, 6 yellow, 7 white); the BBC's physical colours are RGB bits
# (0 black, 1 red, 2 green, 3 yellow, 4 blue, 5 magenta, 6 cyan, 7 white).
ZX_TO_BBC = [0, 4, 1, 5, 2, 6, 3, 7]
# Colours the room data doesn't use still get drawn (sprites, items), so
# every colour carries a little weight, to send an unused colour to its
# nearest neighbour rather than to any free slot.
PRIOR = [20] * 8
RGB = [(0, 0, 0), (0, 0, 215), (215, 0, 0), (215, 0, 215),
       (0, 215, 0), (0, 215, 215), (215, 215, 0), (215, 215, 215)]


def dist(a, b):
    """Perceptual-ish distance between two Spectrum colours."""
    (r1, g1, b1), (r2, g2, b2) = RGB[a], RGB[b]
    return ((r1 - r2) * 0.30) ** 2 + ((g1 - g2) * 0.59) ** 2 + ((b1 - b2) * 0.11) ** 2


def room_usage(r, rooms_dir):
    """Pixel weight per colour, and the (paper, ink) pairs that need telling
    apart, from the oracle's picture of room r (rows 2-23)."""
    d = open(f"{rooms_dir}/room_{r:03d}.bin", "rb").read()
    scr, attrs = d[:6144], d[6144:6912]
    weight = list(PRIOR)
    pairs = set()
    for row in range(2, 24):
        for col in range(32):
            a = attrs[row * 32 + col]
            ink, paper = a & 7, (a >> 3) & 7
            on = 0
            for line in range(8):
                y = row * 8 + line
                on += bin(scr[((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + col]).count("1")
            weight[paper] += 64 - on
            weight[ink] += on
            if on and on < 64 and ink != paper:
                pairs.add((paper, ink))
    return weight, pairs


YELLOW = 6
WHITE = 7
# Harry is white in a room only if that shows this much more of its pixels
# in their own colour than yellow does.
WHITE_GAIN = 0.02


def choose_palette(bg, weight, pairs):
    """Returns (colours: four Spectrum colours, logical 0 first; cmap: the
    logical colour for each Spectrum colour 0-7). Yellow is always one of
    the four (decision 6): Harry is yellow."""
    best = None
    others = [c for c in range(8) if c not in (bg, YELLOW)]
    for pair in itertools.combinations(others, 2):
        colours = [bg, *pair, YELLOW] if bg != YELLOW else [bg, *pair, 7]
        rest = [c for c in range(8) if c not in colours]
        for choice in itertools.product(range(4), repeat=len(rest)):
            cmap = [0] * 8
            for i, c in enumerate(colours):
                cmap[c] = i
            for c, l in zip(rest, choice):
                cmap[c] = l
            if any(cmap[c] == 0 for c in range(8) if c != bg):
                continue
            if any(cmap[p] == cmap[i] for p, i in pairs):
                continue
            cost = sum(weight[c] * dist(c, colours[cmap[c]]) for c in range(8))
            if best is None or cost < best[0]:
                best = (cost, colours, cmap)
    if best is None:
        raise RuntimeError("no palette satisfies the rules")
    return best[1], best[2]


def row_usage(r, rooms_dir):
    """room_usage, a playfield row at a time (rows 2-23): [(weight, pairs)]."""
    d = open(f"{rooms_dir}/room_{r:03d}.bin", "rb").read()
    scr, attrs = d[:6144], d[6144:6912]
    rows = []
    for row in range(2, 24):
        weight = [0] * 8
        pairs = set()
        for col in range(32):
            a = attrs[row * 32 + col]
            ink, paper = a & 7, (a >> 3) & 7
            on = 0
            for line in range(8):
                y = row * 8 + line
                on += bin(scr[((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + col]).count("1")
            weight[paper] += 64 - on
            weight[ink] += on
            if on and on < 64 and ink != paper:
                pairs.add((paper, ink))
        rows.append((weight, pairs))
    return rows


def seam_usage(r, rooms_dir):
    """For each boundary between playfield rows (row 2 + i - 1 above, row
    2 + i below, i = 1..21), {colour: pixels}: the pixels of a colour, not
    the background, with the same colour just across the boundary: an
    object a split there would cut."""
    d = open(f"{rooms_dir}/room_{r:03d}.bin", "rb").read()
    scr, attrs = d[:6144], d[6144:6912]

    def colour(x, y):
        a = attrs[(y // 8) * 32 + x // 8]
        b = scr[((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + x // 8]
        return a & 7 if b & (0x80 >> (x & 7)) else (a >> 3) & 7
    seams = [{}]
    for i in range(1, 22):
        y = (i + 2) * 8
        counts = {}
        for x in range(256):
            c = colour(x, y)
            if c == colour(x, y - 1):
                counts[c] = counts.get(c, 0) + 1
        seams.append(counts)
    return seams


def cuts(counts, bg, pa, pb):
    """The pixels just across a split that change colour, from physical
    colours pa above to pb below (the background never does)."""
    return sum(n for c, n in counts.items() if c != bg and pa[c] != pb[c])


def band_map(colours, weight, pairs, force={}):
    """The cheapest map onto four colours (bg first) under choose_palette's
    rules, or None: each other colour to its nearest slot, then a search
    only if that splits a pair badly. `force` pins colours to a logical
    colour (yellow to Harry's, when he isn't yellow)."""
    rest = [c for c in range(8) if c not in colours and c not in force]

    def cost_of(cmap):
        return sum(weight[c] * dist(c, colours[cmap[c]]) for c in range(8))

    def ok(cmap):
        return all(cmap[p] != cmap[i] for p, i in pairs)

    cmap = [0] * 8
    for i, c in enumerate(colours):
        cmap[c] = i
    for c, l in force.items():
        cmap[c] = l
    for c in rest:
        cmap[c] = min(range(1, 4), key=lambda l: dist(c, colours[l]))
    if ok(cmap):
        return cost_of(cmap), cmap
    best = None
    for choice in itertools.product(range(1, 4), repeat=len(rest)):
        for c, l in zip(rest, choice):
            cmap[c] = l
        if ok(cmap):
            cost = cost_of(cmap)
            if best is None or cost < best[0]:
                best = (cost, list(cmap))
    return best


def exact(colours, weight):
    return sum(weight[c] for c in set(colours))


def choose_bands(bg, rows, seams, harry=YELLOW, max_splits=2, gain=0.002):
    """Decision 15: up to two splits between playfield rows, below which
    logical colour 2 (and the map) change; logical 0 (the paper), 1 and 3
    (Harry's colour, `harry`) stay. Returns (colour 1, colour 3, [(first
    row, colour 2, cmap)], exact), the first band starting at row 2; a
    split is kept only if it shows `gain` more of the room's pixels in
    their own colour, and never where an object crossing it would change
    colour (seams, from seam_usage)."""
    yellow = harry if bg != harry else 7
    # Harry is drawn in Spectrum yellow: when logical 3 isn't yellow, yellow
    # maps to it in every band, and can't be logical 1 or 2 as well (he'd
    # take that colour, and change colour at a split).
    force = {YELLOW: 3} if yellow != YELLOW and bg != YELLOW else {}
    others = [c for c in range(8) if c not in (bg, yellow, *force)]
    n = len(rows)
    total = sum(sum(w) for w, _ in rows)

    # A split may not cut an object in two colours (Matt: room 1's ladder,
    # red above a split and blue below, looked like a mistake).
    def seam(i, pa, pb):
        return float("inf") if seams[i] and cuts(seams[i], bg, pa, pb) else 0
    best = None
    for a in others:
        # A band over rows i..j-1, for each colour 2 that maps: [(cost,
        # exact, b, cmap, physical colour of each Spectrum colour)].
        seg = {}
        for i in range(n):
            w = [0] * 8
            pairs = set()
            for j in range(i + 1, n + 1):
                rw, rp = rows[j - 1]
                w = [x + y for x, y in zip(w, rw)]
                pairs |= rp
                weighted = [x + p * (j - i) // n + 1 for x, p in zip(w, PRIOR)]
                cands = []
                for b in others:
                    if b == a:
                        continue
                    colours = [bg, a, b, yellow]
                    m = band_map(colours, weighted, pairs, force)
                    if m:
                        cands.append((m[0], exact(colours, w), b, m[1],
                                      tuple(colours[m[1][c]] for c in range(8))))
                seg[i, j] = cands
        if any(not v for v in seg.values()):
            continue

        def above(i, B):
            # The cheapest band over rows 0..i-1 above band B, with the seam.
            return min(((A[0] + seam(i, A[4], B[4]), A) for A in seg[0, i]), key=lambda t: t[0])

        def below(j, B):
            return min(((C[0] + seam(j, B[4], C[4]), C) for C in seg[j, n]), key=lambda t: t[0])
        # Best for k splits: (cost, exact, [bands]).
        A = min(seg[0, n], key=lambda t: t[0])
        plans = [(A[0], A[1], [(0, A)])]
        one = None
        for i in range(1, n):
            for B in seg[i, n]:
                c, A = above(i, B)
                if one is None or c + B[0] < one[0]:
                    one = (c + B[0], A[1] + B[1], [(0, A), (i, B)])
        plans.append(one)
        two = None
        for i in range(1, n):
            for j in range(i + 1, n):
                for B in seg[i, j]:
                    ca, A = above(i, B)
                    cc, C = below(j, B)
                    if two is None or ca + B[0] + cc < two[0]:
                        two = (ca + B[0] + cc, A[1] + B[1] + C[1], [(0, A), (i, B), (j, C)])
        plans.append(two)
        k = 0
        for kk in range(1, max_splits + 1):
            if (plans[kk][1] - plans[k][1]) / total >= gain and plans[kk][0] < float("inf"):
                k = kk
        plan = plans[k]
        if best is None or plan[0] < best[0][0]:
            best = (plan, a)
    plan, a = best
    return a, yellow, [(start + 2, B[2], B[3]) for start, B in plan[2]], plan[1] / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", default="build/zx_start.z80")
    ap.add_argument("--rooms", default="build/rooms")
    ap.add_argument("--out", default="src/data")
    args = ap.parse_args()
    m = Spectrum(args.snap).mem
    os.makedirs(args.out, exist_ok=True)

    with open(f"{args.out}/roomdata.bin", "wb") as f:
        f.write(bytes(m[DATA_START:DATA_END]))
    with open(f"{args.out}/tiles.bin", "wb") as f:
        f.write(bytes(m[CHARS + 8 * FIRST_TILE:CHARS + 8 * (LAST_TILE + 1)]))

    lines = [
        "\\ Generated by tools/mkrooms.py from the original: do not edit.",
        "",
    ]
    offsets = []
    for r in range(121):
        if r == 0:
            offsets.append(0)
            continue
        p = m[ROOM_PTRS + 2 * r] | m[ROOM_PTRS + 2 * r + 1] << 8
        offsets.append(p - DATA_START)
    with open(f"{args.out}/roomoffsets.txt", "w") as f:
        f.write("\n".join(str(o) for o in offsets[1:]) + "\n")
    lines += [
        "\\ The rooms' palettes (decision 2), each once, four bytes: the BBC",
        "\\ physical colours of logical 0-3 a nibble each (low nibble first), then",
        "\\ the logical colour of each Spectrum colour 0-7, two bits each (colour 0",
        "\\ lowest). A room's number for its palette is in its packed first byte",
        "\\ (tools/packrooms.py, from roompal.txt).",
        ".room_palettes",
    ]
    report = []
    band_lines = [
        "\\ Generated by tools/mkrooms.py from the original: do not edit.",
        "",
        "\\ Bands (decision 15): below a split between playfield rows, logical",
        "\\ colour 2 and the colour map change. Three bytes each: room, first row",
        "\\ * 8 + the BBC physical colour of logical 2, the map's number in",
        "\\ band_maps; 0 ends.",
        ".room_bands",
    ]
    palettes, room_pal, maps = [], [], []
    before = 0
    gains = []
    for r in range(1, 121):
        bg = (m[DATA_START + offsets[r]] >> 3) & 7
        weight, pairs = room_usage(r, args.rooms)
        before += exact(choose_palette(bg, weight, pairs)[0], weight) / sum(weight)
        rows = row_usage(r, args.rooms)
        seams = seam_usage(r, args.rooms)
        a, yellow, bands, ex = choose_bands(bg, rows, seams)
        if bg != YELLOW:
            alt = choose_bands(bg, rows, seams, harry=WHITE)
            if alt[3] - ex >= WHITE_GAIN:
                gains.append((alt[3] - ex, r))
                a, yellow, bands, ex = alt
        _, b, cmap = bands[0]
        colours = [bg, a, b, yellow]
        phys = [ZX_TO_BBC[c] for c in colours]
        packed = [phys[0] | phys[1] << 4, phys[2] | phys[3] << 4,
                  cmap[0] | cmap[1] << 2 | cmap[2] << 4 | cmap[3] << 6,
                  cmap[4] | cmap[5] << 2 | cmap[6] << 4 | cmap[7] << 6]
        if packed not in palettes:
            palettes.append(packed)
            lines.append(f"    EQUB {', '.join(f'&{b:02X}' for b in packed)}"
                         f"   \\ {len(palettes) - 1:2d}: {' '.join(NAMES[c] for c in colours)}; "
                         f"map {''.join(map(str, cmap))}")
        room_pal.append(palettes.index(packed))
        for row, b, cmap in bands[1:]:
            bmap = (cmap[0] | cmap[1] << 2 | cmap[2] << 4 | cmap[3] << 6,
                    cmap[4] | cmap[5] << 2 | cmap[6] << 4 | cmap[7] << 6)
            if bmap not in maps:
                maps.append(bmap)
            band_lines.append(f"    EQUB {r}, {row} * 8 + {ZX_TO_BBC[b]}, {maps.index(bmap)}"
                              f"   \\ {r:3d} from row {row}: {NAMES[b]}; map {''.join(map(str, cmap))}")
        report.append((ex, r, colours, cmap))
    # The packed first byte has five bits for it (tools/packrooms.py).
    assert len(palettes) <= 32
    band_lines += ["    EQUB 0", "",
                   "\\ The bands' colour maps, as the palettes' (rooms.6502).",
                   ".band_maps"]
    for i, (lo, hi) in enumerate(maps):
        band_lines.append(f"    EQUB &{lo:02X}, &{hi:02X}   \\ {i:2d}")
    with open(f"{args.out}/bands.6502", "w") as f:
        f.write("\n".join(band_lines) + "\n")
    with open(f"{args.out}/rooms.6502", "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(f"{args.out}/roompal.txt", "w") as f:
        f.write("\n".join(str(p) for p in room_pal) + "\n")
    report.sort()
    mean = sum(e for e, *_ in report) / len(report)
    print(f"palettes: {100 * mean:.2f}% of pixels in their own colour on average "
          f"({100 * before / 120:.2f}% without bands), {sum(1 for l in band_lines if "from row" in l)} splits; worst bands 0:")
    for e, r, colours, cmap in report[:5]:
        subs = ", ".join(f"{NAMES[c]}->{NAMES[colours[cmap[c]]]}" for c in range(8) if c not in colours)
        print(f"  room {r:3d} {100 * e:5.1f}%  [{' '.join(NAMES[c] for c in colours)}]  {subs}")
    gains.sort(reverse=True)
    print(f"Harry white in {len(gains)} rooms: "
          + ", ".join(f"{r} (+{100 * g:.1f})" for g, r in gains))


if __name__ == "__main__":
    main()
