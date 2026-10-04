#!/usr/bin/env python3
"""Random walks in random rooms, compared pass by pass with the original.

    python3 tools/fuzz.py [count] [--seed N] [--passes 150] [--jobs 3]

Each case puts Harry standing somewhere in a random room (a cell with two
empty cells over a solid floor, from the BBC's own room dumps in
build/bbcrooms, which make rooms writes) and holds random keys for random
spells, then runs tools/passlog.py and tools/passlog.mjs and compares them
with tools/passcmp.py. A case that differs is printed as a line ready for
tests/scenarios.txt. Same seed, same cases.
"""
import argparse
import os
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

KEYS = ["left", "right", "up", "down", "jump", "take"]


def standing_spots(room):
    path = f"build/bbcrooms/room_{room:03d}.bin"
    if not os.path.exists(path):
        return []
    types = open(path, "rb").read()[1536:2304]
    spots = []
    for row in range(2, 21):
        for col in range(0, 31):
            c = row * 32 + col
            if all(types[c + d] == 0 and types[c + 32 + d] == 0 for d in (0, 1)) \
                    and types[c + 64] & 1 and types[c + 65] & 1:
                spots.append((row, col))
    return spots


def make_case(rnd, passes):
    while True:
        room = rnd.randint(1, 120)
        spots = standing_spots(room)
        if spots:
            break
    row, col = rnd.choice(spots)
    spells = []
    p = 5
    while p < passes - 10:
        length = rnd.randint(3, 40)
        key = rnd.choice(KEYS)
        spells.append(f"{key}:{p}-{min(p + length, passes - 1)}")
        if rnd.random() < 0.3:                   # a jump on top now and then
            spells.append(f"jump:{p + rnd.randint(0, length)}")
        p += length + rnd.randint(0, 10)
    return ",".join(spells), f"{room},{row},{col},0,0,1,0"


def run_case(n, inputs, start, passes):
    zx, bbc = f"build/fuzz_zx_{n}.json", f"build/fuzz_bbc_{n}.json"
    for cmd in ([".venv/bin/python", "tools/passlog.py", inputs, str(passes), "--start", start, "--out", zx],
                ["node", "tools/passlog.mjs", inputs, str(passes), "--start", start, "--out", bbc]):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            # The original stuck outside its main loop: Harry put where he
            # dies at once, until the game ends. Nothing to compare.
            if cmd[1] == "tools/passlog.py" and "never reached the main loop" in r.stdout + r.stderr:
                return n, None, "skipped: the original's game ended (a deadly start)"
            return n, False, f"{cmd[1]} failed: {(r.stderr or r.stdout).strip().splitlines()[-1:]}"
    r = subprocess.run(["python3", "tools/passcmp.py", zx, bbc], capture_output=True, text=True)
    return n, r.returncode == 0, r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("count", type=int, nargs="?", default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--passes", type=int, default=150)
    ap.add_argument("--jobs", type=int, default=3)
    args = ap.parse_args()
    rnd = random.Random(args.seed)
    cases = [make_case(rnd, args.passes) for _ in range(args.count)]
    bad = skipped = 0
    with ThreadPoolExecutor(args.jobs) as pool:
        futures = [pool.submit(run_case, n, i, s, args.passes) for n, (i, s) in enumerate(cases)]
        for f in futures:
            n, ok, out = f.result()
            inputs, start = cases[n]
            if ok is None:
                skipped += 1
                print(f"case {n} ({start}): {out}")
            elif ok:
                print(f"case {n} ({start}): {out}")
            else:
                bad += 1
                print(f"case {n} DIFFERS: fuzz-{args.seed}-{n} | {inputs} | {args.passes} | {start}")
                print("   " + "\n   ".join(out.splitlines()[:9]))
            sys.stdout.flush()
    print(f"{args.count - bad - skipped} of {args.count - skipped} cases match ({skipped} skipped)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
