#!/usr/bin/env python3
"""Compare the BBC's rooms (build/bbcrooms, from tools/roomcheck.mjs) with
the original's (build/rooms, from tools/zxrooms.py).

    python3 tools/roomcmp.py [rooms...]

The three maps must match byte for byte. The screen (rows 2-23; the status
bar isn't drawn yet) must show every Spectrum pixel in the logical colour
the room's palette maps its colour to (src/data/rooms.6502), or the map of
the band the row is in (src/data/bands.6502, decision 15). Text cells
(tile map bit 7) are expected in the MOS font instead (decision 4).
"""
import re
import sys


def palettes():
    src = open("src/data/rooms.6502").read()
    out = {}
    for m in re.finditer(r"EQUB &(..), &(..), &(..), &(..)\s+\\\s+(\d+):", src):
        b = [int(m.group(i), 16) for i in range(1, 5)]
        cmap = [(b[2] >> (2 * i)) & 3 for i in range(4)] + [(b[3] >> (2 * i)) & 3 for i in range(4)]
        out[int(m.group(5))] = cmap
    return out


def bands():
    """{room: [(first row, cmap)]} from src/data/bands.6502 (decision 15)."""
    out = {}
    for m in re.finditer(r"EQUB (\d+), (\d+) \* 8 \+ (\d+), &(..), &(..)", open("src/data/bands.6502").read()):
        lo, hi = int(m.group(4), 16), int(m.group(5), 16)
        cmap = [(lo >> (2 * i)) & 3 for i in range(4)] + [(hi >> (2 * i)) & 3 for i in range(4)]
        out.setdefault(int(m.group(1)), []).append((int(m.group(2)), cmap))
    return out


def bbc_pixel(scr, row, line, x):
    cell = row * 32 + x // 8
    byte = scr[cell * 16 + (8 if x & 4 else 0) + line]
    bit = 3 - (x & 3)
    return ((byte >> (bit + 4)) & 1) << 1 | ((byte >> bit) & 1)


def main():
    pals = palettes()
    room_bands = bands()
    mos = open("build/mosfont.bin", "rb").read()
    rooms = [int(a) for a in sys.argv[1:]] or range(1, 121)
    bad = 0
    for r in rooms:
        zx = open(f"build/rooms/room_{r:03d}.bin", "rb").read()
        bbc = open(f"build/bbcrooms/room_{r:03d}.bin", "rb").read()
        zscr, zmaps = zx[:6144], zx[6912:6912 + 2304]
        bmaps, bscr = bbc[:2304], bbc[2304:]
        problems = []
        for i, name in enumerate(["attr", "tile", "type"]):
            a, b = zmaps[768 * i:768 * (i + 1)], bmaps[768 * i:768 * (i + 1)]
            diffs = [c for c in range(768) if a[c] != b[c]]
            if diffs:
                c = diffs[0]
                problems.append(f"{name} map: {len(diffs)} cells differ, first ({c // 32},{c % 32}) zx {a[c]:02X} bbc {b[c]:02X}")
        pix = 0
        first = None
        for row in range(2, 24):
            cmap = pals[r]
            for start, band_map in room_bands.get(r, []):
                if row >= start:
                    cmap = band_map
            for line in range(8):
                y = row * 8 + line
                zrow = ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2)
                for x in range(256):
                    attr = zmaps[row * 32 + x // 8]
                    tile = zmaps[768 + row * 32 + x // 8]
                    if tile & 0x80:
                        on = mos[((tile & 0x7F) - 32) * 8 + line] & (0x80 >> (x & 7))
                    else:
                        on = zscr[zrow + x // 8] & (0x80 >> (x & 7))
                    want = cmap[attr & 7] if on else cmap[(attr >> 3) & 7]
                    got = bbc_pixel(bscr, row, line, x)
                    if want != got:
                        pix += 1
                        first = first or (x, y, want, got)
        if pix:
            problems.append(f"screen: {pix} pixels differ, first at {first[:2]} want {first[2]} got {first[3]}")
        if problems:
            bad += 1
            print(f"room {r}: " + "; ".join(problems))
    print(f"{len(rooms) - bad} of {len(rooms)} rooms match")
    return 1 if bad else 0


sys.exit(main())
