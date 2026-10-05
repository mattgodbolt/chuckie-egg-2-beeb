"""Room 51 drawn a record at a time."""
from PIL import Image, ImageDraw
from util import W, render, row_maps, logical, font, mono, save

D = f"{W}/work/b51"
final = open(f"{D}/final.bin", "rb").read()
maps = row_maps(final, f"{D}/final.png")
steps = [open(f"{D}/step_{n:02d}.bin", "rb").read() for n in range(10)]

CAPS = [
    ("18", "the paper: room filled"),
    ("40 21 02 00 20 01", "run: 32 across, row 2"),
    ("40 21 17 00 20 01", "run: 32 across, row 23"),
    ("40 21 03 00 94 01", "run: 20 down, column 0"),
    ("40 21 0C 1F 8B 01", "run: 11 down, column 31"),
    ("40 21 0C 16 09 01", "run: 9 across, row 12"),
    ("0A 1C 55 0B 1F 04", "single: a / slope tile"),
    ("07 1F 0E 08 06 0F", "hopper: 6 rows, 15 wide"),
    ("02 38 10 0D 43 4F 43 4F 41 80", "text: COCOA"),
    ("20 1F 14 0F 84 00 00", "capped run: pipe, 4 down"),
]

S = 2
PW, PH = 256 * S // 2 * 2, 176 * S
pw, ph = 256, 176
cap_h = 40
gap = 8
cols = 5
img = Image.new("RGB", (cols * pw + (cols + 1) * gap, 2 * (ph + cap_h) + 3 * gap), (32, 32, 32))
d = ImageDraw.Draw(img)
fm, fs = mono(12), font(12)
prev = None
for n, scr in enumerate(steps):
    pic = render(scr, maps).crop((0, 16, 256, 192))
    lg = logical(scr)
    x0 = gap + (n % cols) * (pw + gap)
    y0 = gap + (n // cols) * (ph + cap_h + gap)
    img.paste(pic, (x0, y0))
    if prev is not None:
        xs = [x for y in range(16, 192) for x in range(256) if lg[y][x] != prev[y][x]]
        ys = [y for y in range(16, 192) for x in range(256) if lg[y][x] != prev[y][x]]
        if xs:
            bx0, bx1, by0, by1 = min(xs), max(xs), min(ys) - 16, max(ys) - 16
            d.rectangle((x0 + bx0 - 2, y0 + by0 - 2, x0 + bx1 + 2, y0 + by1 + 2), outline=(255, 255, 255), width=1)
            d.rectangle((x0 + bx0 - 3, y0 + by0 - 3, x0 + bx1 + 3, y0 + by1 + 3), outline=(0, 0, 0), width=1)
    prev = lg
    b, t = CAPS[n]
    d.text((x0, y0 + ph + 5), f"{n}. {t}", font=fs, fill=(255, 255, 255))
    d.text((x0, y0 + ph + 22), b, font=fm, fill=(255, 220, 120))
print(save(img, "room51-records.png"))
