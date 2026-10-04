#!/usr/bin/env python3
"""Sweep BAND_ADJ (decision 15) and check room 48's splits land in the blank.

    python3 tools/bandsweep.py FROM TO STEP

Builds the viewer with -D BAND_SWEEP=n, shows room 48, and counts pixels of
the new colour on the line before each split (early) and of the old one on
the line after (late), from the screenshot (4 x 4 per BBC pixel).
"""
import subprocess, sys
from PIL import Image
from collections import Counter
x0, y0 = 368, 264
def colours(img, row, l):
    px = img.load(); y = y0 + row * 32 + l * 4 + 1
    return Counter(px[x0 + x * 4 + 1, y] for x in range(256))
BLUE, RED, CYAN = (0, 0, 255), (255, 0, 0), (0, 255, 255)
for n in range(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])):
    subprocess.run(["../baron/build/src/baron", "-D", "VIEWER=1", "-D", f"BAND_SWEEP={n}", "-D", 'BUILD="sweep"',
                    "-o", "build/sweep.ssd", "--opt", "3", "--symbols", "build/sweep.json", "src/main.6502"],
                   check=True, capture_output=True)
    subprocess.run(["node", "tools/play.mjs", "0.5,=room:48,2,!sweep", "build/shots/", "--disc", "build/sweep.ssd",
                    "--until", "viewer"], check=True, capture_output=True)
    img = Image.open("build/shots/sweep.png").convert("RGB")
    a, b = colours(img, 22, 7), colours(img, 23, 0)
    c, d = colours(img, 15, 7), colours(img, 16, 0)
    early = a[RED] + c[BLUE]          # new colour on the line before
    late = b[BLUE] + d[CYAN]          # old colour on the line after
    print(f"BAND_ADJ {n:4d}: early {early:3d} late {late:3d}", "OK" if not early and not late else "")
    sys.stdout.flush()
