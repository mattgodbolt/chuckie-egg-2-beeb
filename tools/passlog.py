#!/usr/bin/env python3
"""Play the original pass by pass and log Harry's state each pass.

    .venv/bin/python tools/passlog.py '<inputs>' passes [--out build/zx_passes.json]

The BBC counterpart is tools/passlog.mjs; tools/passcmp.py compares the two.
<inputs> holds keys over ranges of main-loop passes (inclusive), comma
separated: `right:10-40,jump:45,up:50-60`. Names: up down left right jump
take. Pass 0 is the first time the main loop (&77B9) is reached after P
starts a game; keys are set at the top of a pass, before the original reads
them, so both machines see the same keys on the same pass.

Each line of the output: pass, room, cell (row * 32 + col), yf, xf,
state, face, cnt (jump count), fall (fall counter).
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


def harry_state(m, n):
    attr = m[HARRY + 2] | m[HARRY + 3] << 8
    return {
        "pass": n, "room": m[0xA3FE], "cell": attr - 0x5800, "yf": m[HARRY + 5] & 7,
        "xf": m[HARRY + 0x0A], "state": m[0xA487], "face": m[HARRY + 0x0D],
        "cnt": m[0xA485], "fall": m[0xA486],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("passes", type=int)
    ap.add_argument("--snap", default="build/ce2.z80")
    ap.add_argument("--out", default="build/zx_passes.json")
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
    log = []
    for n in range(args.passes):
        if spec.run_tstates(10 * 50 * FRAME, stop=MAIN_LOOP) != MAIN_LOOP:
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
