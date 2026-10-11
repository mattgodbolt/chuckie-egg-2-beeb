#!/usr/bin/env python3
"""Pad baron's SSD to 40 tracks, every sector from track 1 on filled with
(track, sector) pairs, and the catalogue told the disc has 400 sectors."""
import sys
src, out = sys.argv[1], sys.argv[2]
img = bytearray(open(src, 'rb').read())
img += bytes(400 * 256 - len(img))
for s in range(10, 400):
    t, sec = divmod(s, 10)
    img[s * 256:(s + 1) * 256] = bytes([t, sec]) * 128
img[256 + 6] = (img[256 + 6] & ~3) | (400 >> 8)
img[256 + 7] = 400 & 0xff
open(out, 'wb').write(img)
