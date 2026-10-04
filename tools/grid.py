#!/usr/bin/env python3
"""Tile screenshots into one image: grid.py out.png cols a.png b.png ..."""
import sys
from PIL import Image
out, cols, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = [Image.open(f) for f in files]
w, h = ims[0].size
w2, h2 = w // 2, h // 2
rows = (len(ims) + cols - 1) // cols
W = Image.new("RGB", (w2 * cols, h2 * rows))
for i, im in enumerate(ims):
    W.paste(im.resize((w2, h2)), ((i % cols) * w2, (i // cols) * h2))
W.save(out)
