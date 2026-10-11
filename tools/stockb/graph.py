#!/usr/bin/env python3
"""The room graph from the original's type maps (build/rooms, the oracle).
An exit is possible when Harry could cross that edge (harry.6502 edges):
left/right: two rows at column 0/31 with no solid (&21) cell;
up: a column whose row-2 cell lets a head through (&2D clear) or is ladder/rope (&12);
down: a column whose row-23 cell has no floor (&21 clear) or is ladder/rope.
Destination: room +-1, +-10; 80 right -> 71, 71 left -> 80 (change_room)."""
import json, sys

def tmap(r):
    d = open(f"build/rooms/room_{r:03d}.bin", "rb").read()
    return d[6912 + 1536:6912 + 2304]

def T(t, row, col): return t[row * 32 + col]

def exits(r):
    t = tmap(r)
    out = {}
    def side(col):
        return any(T(t, y, col) & 0x21 == 0 and T(t, y + 1, col) & 0x21 == 0 for y in range(2, 23))
    if side(0): out["L"] = 80 if r == 71 else r - 1
    if side(31): out["R"] = 71 if r == 80 else r + 1
    if any(T(t, 2, c) & 0x2D == 0 or T(t, 2, c) & 0x12 for c in range(32)): out["U"] = r - 10
    if any(T(t, 23, c) & 0x21 == 0 or T(t, 23, c) & 0x12 for c in range(32)): out["D"] = r + 10
    return {k: v for k, v in out.items() if 1 <= v <= 120}

G = {r: exits(r) for r in range(1, 121)}
if __name__ == "__main__":
    out = {r: G[r] for r in G}
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "/dev/stdout", "w"), indent=0)
