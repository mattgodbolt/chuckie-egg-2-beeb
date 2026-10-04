#!/usr/bin/env python3
"""Play the original pass by pass and log Harry's state each pass.

    .venv/bin/python tools/passlog.py '<inputs>' passes [--out build/zx_passes.json]

The BBC counterpart is tools/passlog.mjs; tools/passcmp.py compares the two.
<inputs> holds keys over ranges of main-loop passes (inclusive), comma
separated: `right:10-40,jump:45,up:50-60`. Names: up down left right jump
take. Pass 0 is the first time the main loop (&77B9) is reached after P
starts a game; keys are set at the top of a pass, before the original reads
them, so both machines see the same keys on the same pass.

--start room,row,col,yf,xf,state,face puts Harry there before pass 0:
after one pass in room 1, the original's room set-up (&7913) is called
with him placed, and his checkpoint taken (the port does the same through
dbg_room).

Each line of the output: pass, room, cell (row * 32 + col), yf, xf,
state, face, cnt (jump count), fall (fall counter), the RNG's state, and
each monster as [cell, yf, sub, dx, dy, tick, speed].
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from zx import FRAME, Spectrum  # noqa: E402

MAIN_LOOP = 0x77B9
KEYS = {"up": "Q", "down": "A", "left": "O", "right": "P", "jump": "SYM", "take": "1"}
HARRY = 0xA451


def parse_inputs(spec):
    out = []
    for part in filter(None, spec.split(",")):
        name, _, rng = part.partition(":")
        a, _, b = rng.partition("-")
        out.append((KEYS[name], int(a), int(b or a)))
    return out


MONSTERS = 0xA490           # 26-byte records; the count is at &A48F
RNG = 0x91B1               # big-endian, 4 bytes


def harry_state(m, n):
    attr = m[HARRY + 2] | m[HARRY + 3] << 8
    monsters = []
    for i in range(m[0xA48F]):
        r = MONSTERS + 26 * i
        a = m[r + 2] | m[r + 3] << 8
        monsters.append([a - 0x5800, m[r + 5] & 7, m[r + 0x0A], m[r + 0x0B], m[r + 0x0C],
                         m[r + 8], m[r + 0x13]])
    return {
        "pass": n, "room": m[0xA3FE], "cell": attr - 0x5800, "yf": m[HARRY + 5] & 7,
        "xf": m[HARRY + 0x0A], "state": m[0xA487], "face": m[HARRY + 0x0D],
        "cnt": m[0xA485], "fall": m[0xA486],
        "rng": "".join(f"{m[RNG + i]:02x}" for i in range(4)), "monsters": monsters,
        "score": "".join(str(m[0xA445 + i]) for i in range(10)), "lives": m[0xA3FA],
        "carried": m[0xA560], "factory": m[0xA48C], "rr": m[0xA400],
        "sel": 1 if m[0xA405] else 0, "falling": m[0xA54E],
        "train": [m[0xA48D], m[0xA48E]],
        "things": "".join(f"{m[0x6600 + i]:02x}" for i in range(0x29)),
    }


def teleport(spec, start, power=False, factory=None, carry=None):
    """After one pass in room 1, put Harry in room, row, col, yf, xf with
    state and facing, call the room set-up (&7913) and take the checkpoint.
    With power, the lever's power is on first (&A48C bit 0)."""
    from skoolkit.simutils import PC, SP
    room, row, col, yf, xf, state, face = start
    m = spec.mem
    regs = spec.sim.registers
    for first in (True, False):     # to the top of the second pass
        if spec.run_tstates(10 * 50 * FRAME, stop=MAIN_LOOP) != MAIN_LOOP:
            raise SystemExit("never reached the main loop")
        if first:
            spec.run_tstates(200)       # off the breakpoint
    m[0xA3FE] = room
    attr = 0x5800 + row * 32 + col
    m[HARRY + 2], m[HARRY + 3] = attr & 0xFF, attr >> 8
    m[HARRY + 4], m[HARRY + 5] = attr & 0xFF, 0x40 | (row & 0x18) | yf
    m[HARRY + 0x0A], m[HARRY + 0x0D] = xf, face
    m[HARRY + 0x0B] = m[HARRY + 0x0C] = 0
    header = m[0x89FF + 2 * (face + xf)] | m[0x8A00 + 2 * (face + xf)] << 8
    p = header + 2
    m[HARRY + 0], m[HARRY + 1] = p & 0xFF, p >> 8
    m[HARRY + 6], m[HARRY + 7] = m[header], m[header + 1]
    m[0xA487], m[0xA485], m[0xA486] = state, 0, 0
    if power:
        m[0xA48C] |= 1
    if factory is not None:
        m[0xA48C] = factory
    if carry is not None:
        # Carried, as the take leaves it (&956B): out of the world, its
        # height (from its type's frame, &6A00 and &8A98) for the drop.
        m[0xA560] = carry
        m[0x6600 + carry] |= 0x80
        gfx = m[0x6A00 + 3 * m[0x6900 + carry] + 1]
        frame = m[0x8A98 + 2 * gfx] | m[0x8A99 + 2 * gfx] << 8
        m[0xA561] = m[frame]
    # Call the room set-up, returning to the main loop's top.
    sp = regs[SP] - 2
    m[sp], m[sp + 1] = MAIN_LOOP & 0xFF, MAIN_LOOP >> 8
    regs[SP] = sp
    regs[PC] = 0x7913
    if spec.run_tstates(10 * 50 * FRAME, stop=MAIN_LOOP) != MAIN_LOOP:
        raise SystemExit("room set-up didn't return")
    m[HARRY + 0x12], m[HARRY + 0x13] = room, state
    for i in range(26):
        m[0xA46B + i] = m[HARRY + i]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("passes", type=int)
    ap.add_argument("--snap", default="build/ce2.z80")
    ap.add_argument("--out", default="build/zx_passes.json")
    ap.add_argument("--start", help="room,row,col,yf,xf,state,face")
    ap.add_argument("--power", action="store_true", help="with --start: the power on")
    ap.add_argument("--factory", type=lambda v: int(v, 0), help="with --start: the factory flags (&A48C)")
    ap.add_argument("--carry", type=lambda v: int(v, 0), help="with --start: Harry carrying this thing")
    args = ap.parse_args()
    inputs = parse_inputs(args.inputs)
    spec = Spectrum(args.snap)
    # Through the instructions to the menu, then P.
    for _ in range(3):
        spec.frames(150)
        spec.key("SPACE", True)
        spec.frames(5)
        spec.key("SPACE", False)
    spec.frames(50)
    spec.key("P", True)
    spec.frames(5)
    spec.key("P", False)
    if args.start:
        teleport(spec, [int(v) for v in args.start.split(",")], args.power, args.factory, args.carry)
    log = []
    for n in range(args.passes):
        # (After a teleport the set-up has just returned to the loop's top.)
        if not (n == 0 and args.start) and \
                spec.run_tstates(10 * 50 * FRAME, stop=MAIN_LOOP) != MAIN_LOOP:
            raise SystemExit(f"pass {n}: never reached the main loop")
        for key, a, b in inputs:
            spec.key(key, a <= n <= b)
        log.append(harry_state(spec.mem, n))
        # Step off the breakpoint so the next run finds the next pass.
        spec.run_tstates(200)
    with open(args.out, "w") as f:
        for entry in log:
            f.write(json.dumps(entry) + "\n")
    print(f"{len(log)} passes logged to {args.out}")


if __name__ == "__main__":
    main()
