#!/usr/bin/env python3
"""Draw every room with the original's own code, and keep what it drew.

    .venv/bin/python tools/zxrooms.py [--snap shots/zx_start.z80] [--out build/rooms]

For each room 1-120: restore the snapshot (a game just started), set the
room number, call the room drawer at &7920 and stop when it returns. Writes
<out>/room_NNN.bin (the 6912-byte screen, then the three 768-byte maps the
drawer fills: &5D00 attributes, &6000 tiles, &6300 cell types) and
<out>/room_NNN.png. This is the oracle any re-implementation of the room
format is checked against, byte for byte.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from skoolkit.simutils import PC, SP  # noqa: E402

from zx import FRAME, Spectrum, screen_image  # noqa: E402

ROOM = 0xA3FE
DRAW_ROOM = 0x7920
SENTINEL = 0x5B00   # a return address nothing else will reach


def draw_room(snap, room, exec_map=None):
    spec = Spectrum(snap, exec_map)
    m = spec.mem
    regs = spec.sim.registers
    m[ROOM] = room
    sp = 0xFFF0 - 2
    m[sp] = SENTINEL & 0xFF
    m[sp + 1] = SENTINEL >> 8
    regs[SP] = sp
    regs[PC] = DRAW_ROOM
    # Interrupts off: the drawer runs with them disabled in the game too.
    spec.sim.trace(DRAW_ROOM, SENTINEL, 0, regs[25] + 200 * FRAME, 0, None, exec_map, None, None, None)
    if regs[PC] != SENTINEL:
        raise RuntimeError(f"room {room}: drawer did not return (PC={regs[PC]:04X})")
    return spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", default="build/zx_start.z80")
    ap.add_argument("--out", default="build/rooms")
    ap.add_argument("--map", help="add the addresses executed to FILE (trace.py's format)")
    ap.add_argument("rooms", nargs="*", type=int)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    exec_map = set() if args.map else None
    for room in args.rooms or range(1, 121):
        spec = draw_room(args.snap, room, exec_map)
        m = spec.mem
        data = bytes(m[0x4000:0x5B00]) + bytes(m[0x5D00:0x6600])
        with open(f"{args.out}/room_{room:03d}.bin", "wb") as f:
            f.write(data)
        screen_image(m, 1).save(f"{args.out}/room_{room:03d}.png")
    print("rooms written to", args.out)
    if args.map:
        merge_map(args.map, exec_map)


def merge_map(path, addrs):
    """Union addrs into the execution map at path."""
    if os.path.exists(path):
        with open(path) as f:
            addrs |= {int(line.strip().lstrip("$"), 16) for line in f if line.strip()}
    with open(path, "w") as f:
        for a in sorted(addrs):
            f.write(f"${a:04X}\n")


if __name__ == "__main__":
    main()
