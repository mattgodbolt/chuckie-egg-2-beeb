#!/usr/bin/env python3
"""Compare Harry pass by pass: the original (tools/passlog.py) against the
port (tools/passlog.mjs).

    python3 tools/passcmp.py [build/zx_passes.json build/bbc_passes.json] [--all]

Prints the first pass that differs, with a few passes of context, or says
they match. --all lists every differing pass.
"""
import json
import sys

FIELDS = ["room", "cell", "yf", "xf", "state", "face", "cnt", "fall", "rng", "monsters",
          "score", "lives", "carried", "factory", "rr", "sel", "falling", "train"]


def load(path):
    return [json.loads(line) for line in open(path) if line.strip()]


def show(e):
    row, col = divmod(e["cell"], 32)
    mons = " ".join(f"[{c // 32},{c % 32},{yf},{sub},{dx},{dy},t{t},s{sp:02x}]"
                    for c, yf, sub, dx, dy, t, sp in e.get("monsters", []))
    return (f"room {e['room']:3d} row {row:2d} col {col:2d} yf {e['yf']} xf {e['xf']:3d} "
            f"state {e['state']} face {e['face']} cnt {e['cnt']:2d} fall {e['fall']:2d} "
            f"rng {e.get('rng', '')} {mons} score {e.get('score')} lives {e.get('lives')} "
            f"carry {e.get('carried')} fac {e.get('factory')} rr {e.get('rr')} sel {e.get('sel')} "
            f"fall {e.get('falling')} train {e.get('train')}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    zx = load(args[0] if args else "build/zx_passes.json")
    bbc = load(args[1] if len(args) > 1 else "build/bbc_passes.json")
    n = min(len(zx), len(bbc))
    # The original doesn't set the fall counter at the start of a game (it
    # holds 250, left over); Harry starts mid-jump, which zeroes it at once.
    zx[0]["fall"] = bbc[0]["fall"]
    bad = [i for i in range(n) if any(zx[i][f] != bbc[i][f] for f in FIELDS)]
    if not bad:
        print(f"{n} passes match")
        return 0
    first = bad[0]
    print(f"{len(bad)} of {n} passes differ; first at pass {first}:")
    for i in range(max(0, first - 3), min(n, first + 4)):
        mark = "*" if i in bad else " "
        print(f"{mark} {i:4d} zx  {show(zx[i])}")
        print(f"{mark} {i:4d} bbc {show(bbc[i])}")
    if "--all" in sys.argv:
        print("differing passes:", bad)
    return 1


sys.exit(main())
