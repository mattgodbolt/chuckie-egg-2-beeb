import os
"""Cell types (the original's type map, from the oracle) over the BBC's
picture of a room.  python overlay.py room out.png"""
import sys
from PIL import Image, ImageDraw, ImageFont
from mkmap import font

ROOMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "rooms")
W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "guide")  # work files and images (not committed)

# (bit mask, name, colour), first match wins
KINDS = [
    (0x80, "deadly (&80)", (255, 40, 40)),
    (0x02, "ladder (&02)", (40, 220, 40)),
    (0x10, "rope (&10)", (255, 150, 0)),
    (0x04, "slope / (&04)", (0, 220, 255)),
    (0x08, "slope \\ (&08)", (60, 120, 255)),
    (0x20, "slippery pipe (&20)", (255, 255, 0)),
    (0x01, "solid (&01)", (230, 230, 230)),
]


def overlay(room, scale=3):
    d = open(f"{ROOMS}/room_{room:03d}.bin", "rb").read()
    types = d[6912 + 1536:6912 + 2304]
    base = Image.open(f"{W}/work/bbc_{room:03d}.png").convert("RGB").crop((0, 16, 256, 192))
    base = base.resize((256 * scale, 176 * scale), Image.NEAREST)
    dim = Image.blend(base, Image.new("RGB", base.size, (0, 0, 0)), 0.55)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    used = set()
    s = 8 * scale
    for row in range(2, 24):
        for col in range(32):
            t = types[row * 32 + col]
            for mask, name, rgb in KINDS:
                if t & mask:
                    x, y = col * s, (row - 2) * s
                    dr.rectangle((x + 1, y + 1, x + s - 2, y + s - 2), fill=rgb + (120,), outline=rgb + (255,), width=2)
                    used.add(name)
                    break
    out = Image.alpha_composite(dim.convert("RGBA"), layer).convert("RGB")
    # key underneath
    f = font(15)
    keys = [k for k in KINDS if k[1] in used]
    kh = 30
    img = Image.new("RGB", (out.width, out.height + kh), (24, 24, 24))
    img.paste(out, (0, 0))
    dr = ImageDraw.Draw(img)
    x = 8
    for _, name, rgb in keys:
        dr.rectangle((x, out.height + 8, x + 14, out.height + 22), fill=rgb)
        dr.text((x + 20, out.height + 7), name, font=f, fill=(255, 255, 255))
        x += 26 + dr.textlength(name, font=f)
    return img


if __name__ == "__main__":
    overlay(int(sys.argv[1]), int(sys.argv[3]) if len(sys.argv) > 3 else 3).save(sys.argv[2], optimize=True)
