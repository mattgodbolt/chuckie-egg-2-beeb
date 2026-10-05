import os
"""Shared helpers for the guide's images."""
from PIL import Image, ImageDraw, ImageFont

W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "guide")  # work files and images (not committed)
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
X0, Y0 = 368, 264


def font(size, bold=True):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/TTF/"):
        try:
            return ImageFont.truetype(d + name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def mono(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/TTF/DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def crop(path, scale=1):
    """A jsbeeb screenshot (1792x1200, 4 screen pixels a BBC pixel and line)
    cut down to the 256x192 picture."""
    im = Image.open(path).convert("RGB").crop((X0, Y0, X0 + 1024, Y0 + 768))
    px, out = im.load(), Image.new("RGB", (256, 192))
    op = out.load()
    for y in range(192):
        for x in range(256):
            op[x, y] = px[4 * x + 1, 4 * y + 1]
    if scale != 1:
        out = out.resize((256 * scale, 192 * scale), Image.NEAREST)
    return out


def logical(scr):
    """The 256x192 logical colours (0-3) of a 12K screen dump."""
    out = [[0] * 256 for _ in range(192)]
    for y in range(192):
        r, line = divmod(y, 8)
        for c in range(64):
            b = scr[r * 512 + c * 8 + line]
            for i in range(4):
                out[y][c * 4 + i] = ((b >> (7 - i)) & 1) << 1 | ((b >> (3 - i)) & 1)
    return out


def row_maps(final_scr, final_png):
    """Per pixel row, logical colour -> RGB, read off the finished screen."""
    lg = logical(final_scr)
    pic = crop(final_png).load()
    maps = []
    for y in range(192):
        m = {}
        for x in range(256):
            m.setdefault(lg[y][x], pic[x, y])
        maps.append(m)
    # fill gaps from the nearest row in the same band (rows above, then below)
    for y in range(192):
        for v in range(4):
            if v not in maps[y]:
                lo, hi = (0, 16) if y < 16 else (16, 192)
                for dy in range(1, 192):
                    for yy in (y + dy, y - dy):
                        if lo <= yy < hi and v in maps[yy]:
                            maps[y][v] = maps[yy][v]
                            break
                    if v in maps[y]:
                        break
    return maps


def render(scr, maps):
    lg = logical(scr)
    im = Image.new("RGB", (256, 192))
    px = im.load()
    for y in range(192):
        for x in range(256):
            px[x, y] = maps[y].get(lg[y][x], (255, 0, 255))
    return im


def label(draw, x, y, text, f, pad=3, fg=(0, 0, 0), bg=(255, 255, 255)):
    l, t, r, b = draw.textbbox((0, 0), text, font=f)
    draw.rectangle((x, y, x + r - l + 2 * pad, y + b - t + 2 * pad), fill=bg)
    draw.text((x + pad - l, y + pad - t), text, font=f, fill=fg)


def save(im, name):
    path = f"{W}/images/{name}"
    im.save(path, optimize=True)
    return path
