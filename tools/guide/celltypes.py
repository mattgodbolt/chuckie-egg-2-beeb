"""Cell types (the original's type map, from the oracle) over the BBC's
pictures of rooms 91, 27 and 8, with a key."""
from PIL import Image, ImageDraw
from util import W, REPO, font, save

KINDS = [
    (0x80, "deadly", "&80", (255, 40, 40)),
    (0x02, "ladder", "&02", (40, 220, 40)),
    (0x10, "rope: slide down only", "&10", (255, 150, 0)),
    (0x04, "slope /", "&04", (0, 220, 255)),
    (0x08, "slope \\", "&08", (60, 120, 255)),
    (0x20, "slippery pipe", "&20", (255, 255, 0)),
    (0x01, "solid: floor, wall, ceiling", "&01", (230, 230, 230)),
]
S = 2


def overlay(room):
    types = open(f"{REPO}/build/rooms/room_{room:03d}.bin", "rb").read()[6912 + 1536:6912 + 2304]
    base = Image.open(f"{W}/work/bbc_{room:03d}.png").convert("RGB").crop((0, 16, 256, 192))
    base = base.resize((256 * S, 176 * S), Image.NEAREST)
    dim = Image.blend(base, Image.new("RGB", base.size, (0, 0, 0)), 0.55)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    s = 8 * S
    for row in range(2, 24):
        for col in range(32):
            t = types[row * 32 + col]
            for mask, _, _, rgb in KINDS:
                if t & mask:
                    x, y = col * s, (row - 2) * s
                    dr.rectangle((x + 1, y + 1, x + s - 2, y + s - 2), fill=rgb + (110,), outline=rgb + (255,), width=2)
                    break
    return Image.alpha_composite(dim.convert("RGBA"), layer).convert("RGB")


rooms = [(91, "room 91"), (27, "room 27"), (8, "room 8")]
ims = [overlay(r) for r, _ in rooms]
w, h = ims[0].size
gap, ch = 8, 26
out = Image.new("RGB", (2 * w + 3 * gap, 2 * (h + ch) + 3 * gap), (28, 28, 28))
d = ImageDraw.Draw(out)
f, fk = font(16), font(17)
for i, (im, (_, cap)) in enumerate(zip(ims, rooms)):
    x, y = gap + (i % 2) * (w + gap), gap + (i // 2) * (h + ch + gap)
    d.text((x, y), cap, font=f, fill=(240, 240, 240))
    out.paste(im, (x, y + ch))
# the key in the fourth slot
x, y = gap + w + gap + 20, gap + h + ch + gap + ch + 10
d.text((x, y), "Cell types (each cell's byte in the type map)", font=fk, fill=(255, 255, 255))
y += 40
for _, name, val, rgb in KINDS:
    d.rectangle((x, y, x + 22, y + 22), fill=tuple(c // 2 for c in rgb), outline=rgb, width=2)
    d.text((x + 34, y + 1), f"{val}  {name}", font=fk, fill=(240, 240, 240))
    y += 36
d.text((x, y + 6), "A cell can hold more than one bit:", font=font(14, False), fill=(200, 200, 200))
d.text((x, y + 26), "&03 is a ladder that is also a floor.", font=font(14, False), fill=(200, 200, 200))
print(save(out, "cell-types.png"))
