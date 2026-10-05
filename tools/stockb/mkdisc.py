#!/usr/bin/env python3
"""A 40-track DFS disc for the disc-streaming measurements: one file, BIG,
from sector 2 to the end, each sector filled with (track, sector) so a
read can be checked; and a small file, SMALL (one sector at track 20),
for OSFILE loads. Written to disc.ssd beside this script."""
import os

TRACKS, SPT = 40, 10
total = TRACKS * SPT
img = bytearray(total * 256)
for s in range(total):
    t, sec = divmod(s, SPT)
    img[s * 256:(s + 1) * 256] = bytes([t, sec]) * 128

# Files, in descending start-sector order in the catalogue.
files = [("SMALL", 200, 256, 0x4000), ("BIG", 2, (total - 2) * 256, 0x4000)]
files.sort(key=lambda f: -f[1])
cat0 = bytearray(256)
cat1 = bytearray(256)
cat0[0:8] = b"STREAM  "
cat1[0:4] = b"    "
cat1[4] = 0
cat1[5] = len(files) * 8
cat1[6] = (total >> 8) & 3
cat1[7] = total & 0xFF
for i, (name, start, length, load) in enumerate(files):
    e = 8 + 8 * i
    cat0[e:e + 7] = name.ljust(7).encode()
    cat0[e + 7] = ord("$")
    cat1[e:e + 2] = (load & 0xFFFF).to_bytes(2, "little")
    cat1[e + 2:e + 4] = (load & 0xFFFF).to_bytes(2, "little")
    cat1[e + 4:e + 6] = (length & 0xFFFF).to_bytes(2, "little")
    cat1[e + 6] = ((start >> 8) & 3) | (3 << 2) | (((length >> 16) & 3) << 4) | (3 << 6)
    cat1[e + 7] = start & 0xFF
img[0:256] = cat0
img[256:512] = cat1
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disc.ssd")
open(out, "wb").write(img)
print(out, len(img))
