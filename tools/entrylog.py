#!/usr/bin/env python3
"""Where the original first draws Harry on entering a room: the Spectrum
half of tools/entrycheck.mjs, which runs the same cases on the port.

    .venv/bin/python tools/entrylog.py room,row,col,face,key,x0,x1,stop ...

Each case puts Harry in the room (tools/passlog.py's teleport), standing
at row, col with that facing, holds the key (left or right) and, after
the room changes, records the lit x extent of the screen's lines 166-178
between x0 and x1 at each wait for a frame (the main loop's three HALTs,
where the interrupt draws). With stop 1 the key is let go as the room
changes. Prints one JSON list per case: the extents seen, in order, a
repeat of the one before left out, null where nothing was lit.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from passlog import KEYS, teleport  # noqa: E402
from zx import FRAME, Spectrum  # noqa: E402

HALTS = (0x786F, 0x789A, 0x78B3)    # the main loop's waits, in order
LINES = range(166, 179)
WAITS = 300                         # enough to cross the room's edge


def extent(m, x0, x1):
    xs = []
    for y in LINES:
        row = 0x4000 + ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2)
        xs += [x for x in range(x0, x1 + 1) if m[row + (x >> 3)] & (0x80 >> (x & 7))]
    return [min(xs), max(xs)] if xs else None


def run_case(spec, case):
    room, row, col, face, key, x0, x1, stop = case.split(",")
    teleport(spec, [int(room), int(row), int(col), 0, 0, 1, int(face)])
    k = KEYS[key]
    spec.key(k, True)
    first, seen = int(room), []
    for n in range(WAITS):
        halt = HALTS[n % 3]     # (each a different address: no step off)
        if spec.run_tstates(10 * 50 * FRAME, stop=halt) != halt:
            raise SystemExit(f"{case}: never reached the wait at &{halt:04X}")
        if spec.mem[0xA3FE] != first:
            if stop == "1":
                spec.key(k, False)
            e = extent(spec.mem, int(x0), int(x1))
            if not seen or seen[-1] != e:
                seen.append(e)
            if len(seen) == 4:
                break
    spec.key(k, False)
    return seen


def main():
    out = []
    for case in sys.argv[1:]:
        spec = Spectrum("build/ce2.z80")
        # Through the instructions to the menu, then P (as passlog.py).
        for _ in range(3):
            spec.frames(150)
            spec.key("SPACE", True)
            spec.frames(5)
            spec.key("SPACE", False)
        spec.frames(50)
        spec.key("P", True)
        spec.frames(5)
        spec.key("P", False)
        out.append(run_case(spec, case))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
