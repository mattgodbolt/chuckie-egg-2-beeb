"""Crop jsbeeb screenshots (1792x1200, 4 screen pixels per BBC pixel and
line) to the 256x192 picture.  python crop.py in.png out.png [scale]"""
import sys
from PIL import Image

X0, Y0 = 368, 264


def crop(path, scale=1):
    im = Image.open(path).convert("RGB")
    im = im.crop((X0, Y0, X0 + 1024, Y0 + 768))
    # sample the middle of each 4x4 block
    small = Image.new("RGB", (256, 192))
    px = im.load()
    sp = small.load()
    for y in range(192):
        for x in range(256):
            sp[x, y] = px[4 * x + 1, 4 * y + 1]
    if scale != 1:
        small = small.resize((256 * scale, 192 * scale), Image.NEAREST)
    return small


if __name__ == "__main__":
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    crop(sys.argv[1], scale).save(sys.argv[2], optimize=True)
