"""Spectrum against BBC: the palette bands (room 48) and the colour check."""
import re
from PIL import Image, ImageDraw
from util import W, REPO, font, save

S = 2


def zx(r):
    return Image.open(f"{REPO}/build/rooms/room_{r:03d}.png").convert("RGB").crop((0, 16, 256, 192))


def bbc(r):
    return Image.open(f"{W}/work/bbc_{r:03d}.png").convert("RGB").crop((0, 16, 256, 192))


def bits(p):
    return tuple(c > 100 for c in p)


def splits(r):
    src = open(f"{REPO}/src/data/bands.6502").read()
    names = "black red green yellow blue magenta cyan white".split()
    return [(int(m.group(2)), names[int(m.group(3))])
            for m in re.finditer(r"EQUB (\d+), (\d+) \* 8 \+ (\d+), \d+", src) if int(m.group(1)) == r]


def panel(im):
    return im.resize((256 * S, 176 * S), Image.NEAREST)


def bands_figure(r=48):
    a, b = panel(zx(r)), panel(bbc(r))
    gap, top = 10, 30
    out = Image.new("RGB", (2 * a.width + 3 * gap, a.height + top + 40), (28, 28, 28))
    d = ImageDraw.Draw(out)
    f, fs = font(16), font(13)
    out.paste(a, (gap, top))
    out.paste(b, (2 * gap + a.width, top))
    d.text((gap, 7), f"Spectrum: room {r} as the original draws it", font=f, fill=(240, 240, 240))
    d.text((2 * gap + a.width, 7), "BBC: four colours, logical 2 changed at each split", font=f, fill=(240, 240, 240))
    x0 = 2 * gap + a.width
    for row, colour in splits(r):
        y = top + (row - 2) * 8 * S
        for x in range(x0, x0 + a.width, 12):
            d.line((x, y, x + 6, y), fill=(255, 255, 255), width=2)
        t = f"split before row {row}: logical 2 becomes {colour}"
        d.text((x0 + a.width - d.textlength(t, font=fs) - 6, y - 18), t, font=fs, fill=(255, 255, 255),
               stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((gap, top + a.height + 10),
           "The splits fall between character rows; the room's other three colours stay the same all the way down.",
           font=fs, fill=(200, 200, 200))
    return save(out, "palette-bands.png")


def check_figure(r):
    a, b = zx(r), bbc(r)
    tiles = open(f"{REPO}/build/rooms/room_{r:03d}.bin", "rb").read()[6912 + 768:6912 + 1536]
    diff = Image.new("RGB", (256, 176))
    pa, pb, pd = a.load(), b.load(), diff.load()
    same = total = 0
    for y in range(176):
        for x in range(256):
            if tiles[(y // 8 + 2) * 32 + x // 8] & 0x80:      # text: the BBC's own font (decision 4)
                pd[x, y] = (70, 70, 70)
                continue
            total += 1
            if bits(pa[x, y]) == bits(pb[x, y]):
                same += 1
                g = 40 if pa[x, y] == (0, 0, 0) else 110
                pd[x, y] = (g, g, g)
            else:
                pd[x, y] = (255, 0, 255)
    gap, top = 10, 30
    ims = [panel(a), panel(b), panel(diff)]
    out = Image.new("RGB", (3 * ims[0].width + 4 * gap, ims[0].height + top + 40), (28, 28, 28))
    d = ImageDraw.Draw(out)
    f, fs = font(16), font(13)
    caps = [f"Spectrum (the oracle): room {r}", "BBC (the room viewer)",
            f"magenta: not the Spectrum's colour ({100 * (total - same) / total:.1f}%)"]
    for i, (im, c) in enumerate(zip(ims, caps)):
        x = gap + i * (im.width + gap)
        out.paste(im, (x, top))
        d.text((x, 7), c, font=f, fill=(240, 240, 240))
    d.text((gap, top + ims[0].height + 10),
           "Every pixel is in the logical colour the room's palette gives its Spectrum colour; "
           "the magenta ones are where four colours can't show eight. Grey: the rest; dark grey: text, in the BBC's font.",
           font=fs, fill=(200, 200, 200))
    print(r, same, total, 100 * same / total)
    return save(out, "oracle-check.png")


if __name__ == "__main__":
    print(bands_figure(48))
    print(check_figure(106))
