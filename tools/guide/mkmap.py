import os
"""Tile the viewer's 120 room screenshots into the factory map."""
import sys
from PIL import Image, ImageDraw, ImageFont
from crop import crop

W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "guide")  # work files and images (not committed)
VIEW = f"{W}/work/view"

rooms = {}
if __name__ != "__main__": raise_import = False
for r in range(1, 121):
    im = crop(f"{VIEW}/room_{r:03d}.png")
    im.save(f"{W}/work/bbc_{r:03d}.png")
    rooms[r] = im.crop((0, 16, 256, 192))      # the playfield, rows 2-23


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def label(draw, x, y, text, f, pad=3):
    l, t, r, b = draw.textbbox((0, 0), text, font=f)
    draw.rectangle((x, y, x + r - l + 2 * pad, y + b - t + 2 * pad), fill=(255, 255, 255))
    draw.text((x + pad - l, y + pad - t), text, font=f, fill=(0, 0, 0))


def make_map(scale, gap, out, fsize):
    cw, ch = int(256 * scale), int(176 * scale)
    img = Image.new("RGB", (10 * cw + 11 * gap, 12 * ch + 13 * gap), (60, 60, 60))
    d = ImageDraw.Draw(img)
    f = font(fsize)
    for r in range(1, 121):
        c, row = (r - 1) % 10, (r - 1) // 10
        x, y = gap + c * (cw + gap), gap + row * (ch + gap)
        tile = rooms[r] if scale == 1 else rooms[r].resize((cw, ch), Image.LANCZOS)
        img.paste(tile, (x, y))
        label(d, x + 2, y + 2, str(r), f)
    # the railway: rooms 71-80, row 8 of the grid, joined end to end
    y = gap + 7 * (ch + gap)
    d.rectangle((gap - 2, y - 2, gap + 10 * (cw + gap) - gap + 1, y + ch + 1), outline=(255, 0, 255), width=2)
    img.save(out, optimize=True)
    return img


if __name__ == "__main__":
    make_map(0.5, 2, f"{W}/work/map_half.png", 11)
    make_map(1, 4, f"{W}/work/map_full.png", 16)
