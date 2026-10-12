#!/usr/bin/env python3
"""The original's toy for each egg given, for tools/toycheck.mjs: where the
toy's eight parts (things 0-7), the toy (&27) and the toy maker's lights
(&29-&30) start, and the picture each shows, from the tape's tables.

    .venv/bin/python tools/toylog.py [--snap build/ce2.z80] EGG...

The original's EggInit (&9A80, at &9B08) gives the toy's types (0-8) the
nine graphics of toy ((egg - 1) AND 3) + 1, from &1C + 9 x the toy in the
pointer table (&8A98); a thing of type t shows the graphic its type has.
Prints JSON: for each egg, a list of {thing, room, row, col, rows}, rows
the picture's lines, each a string of 0s and 1s, 8 a byte across, as the
original draws it from its cell's top left.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from zx import Spectrum  # noqa: E402

THINGS, TYPES, OBJ_POINTERS = 0x6600, 0x6A00, 0x8A98
TOY_THINGS = [*range(8), 0x27, *range(0x29, 0x31)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", default="build/ce2.z80")
    ap.add_argument("eggs", nargs="+", type=int)
    args = ap.parse_args()
    m = Spectrum(args.snap).mem
    word = lambda a: m[a] | m[a + 1] << 8
    out = []
    for egg in args.eggs:
        toy = ((egg - 1) & 3) + 1
        things = []
        for x in TOY_THINGS:
            t = m[THINGS + 768 + x]
            assert t < 9, hex(x)
            ptr = word(OBJ_POINTERS + 2 * (0x1C + 9 * toy + t))
            h, w = m[ptr], m[ptr + 1]
            rows = ["".join(f"{m[ptr + 2 + line * w + col]:08b}" for col in range(w)) for line in range(h * 8)]
            things.append({"thing": x, "room": m[THINGS + x] & 0x7F, "row": m[THINGS + 256 + x],
                           "col": m[THINGS + 512 + x], "rows": rows})
        out.append(things)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
