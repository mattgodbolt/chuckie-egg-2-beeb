import os
"""Print a room's cell-type map as characters (oracle)."""
import sys
ROOMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "rooms")
for r in map(int, sys.argv[1:]):
    d = open(f"{ROOMS}/room_{r:03d}.bin", "rb").read()
    t = d[6912 + 1536:6912 + 2304]
    print(f"room {r}")
    print("    " + "".join(str(c % 10) for c in range(32)))
    for row in range(2, 24):
        s = ""
        for col in range(32):
            v = t[row * 32 + col]
            s += ("#" if v == 1 else "H" if v & 2 and v & 1 else "|" if v & 2 else "!" if v & 0x80 else
                  "/" if v & 4 else "\\" if v & 8 else "r" if v & 16 else "=" if v & 0x20 else
                  "." if v == 0 else "?")
        print(f"{row:2d}  {s}")
