"""The BBC screen as the port uses it: a diagram on a real screenshot."""
from PIL import Image, ImageDraw
from util import W, crop, font, mono, save

S = 2
pic = crop(f"{W}/work/scenes/truck_b.png")
big = pic.resize((256 * S, 192 * S), Image.NEAREST)
ml, mt = 30, 50
out = Image.new("RGB", (ml + big.width + 470, mt + 500), (28, 28, 28))
d = ImageDraw.Draw(out)
f, fs, fm = font(15), font(13, False), mono(13)
WH, GR, YE = (240, 240, 240), (170, 170, 170), (255, 220, 120)
out.paste(big, (ml, mt))
x1 = ml + big.width
# width
d.line((ml, mt - 14, x1 - 1, mt - 14), fill=GR, width=1)
for x in (ml, x1 - 1):
    d.line((x, mt - 19, x, mt - 9), fill=GR)
t = "256 pixels: 32 cells, 64 bytes (MODE 1's pixels, the CRTC narrowed: R1 = 64)"
d.text((ml + (big.width - d.textlength(t, font=fs)) / 2, mt - 36), t, font=fs, fill=WH)
# brackets on the right
bx = x1 + 12


def bracket(y0, y1, lines, top=None):
    d.line((bx, y0 + 1, bx + 8, y0 + 1), fill=GR)
    d.line((bx + 8, y0 + 1, bx + 8, y1 - 1), fill=GR)
    d.line((bx, y1 - 1, bx + 8, y1 - 1), fill=GR)
    y = top if top is not None else (y0 + y1) / 2 - 10 * len(lines)
    for i, (txt, fnt, col) in enumerate(lines):
        d.text((bx + 18, y + 20 * i), txt, font=fnt, fill=col)


bracket(mt, mt + 16 * S, [("rows 0-1: the status bar, black and white", fs, WH)])
bracket(mt + 16 * S + 2, mt + big.height, [
    ("rows 2-23: the room, 32 x 22 cells", f, WH),
    ("four colours of its own; a timer interrupt", fs, GR),
    ("changes the palette just before row 2,", fs, GR),
    ("and again at up to two more splits", fs, GR),
    ("192 lines in all (R6 = 24 rows of 8)", fs, GR),
], top=mt + 16 * S + 10)
# memory layout under the picture
y = mt + 500 - 30
d.text((ml, y), "Screen memory &5000-&7FFF (12K):  row r starts at &5000 + r x &200;  cell n (= 32r + c) at &5000 + 16n",
       font=fm, fill=YE)
# one cell, enlarged: the B of BEWARE
cx, cy = 17, 13
cell = pic.crop((cx * 8, cy * 8, cx * 8 + 8, cy * 8 + 8))
Z = 22
gx, gy = bx + 20, mt + 200
d.text((gx, gy - 40), f"One cell (row {cy}, column {cx}) is 16 bytes:", font=f, fill=WH)
d.text((gx, gy - 20), "two columns of four pixels, eight lines each", font=fs, fill=GR)
cz = cell.resize((8 * Z, 8 * Z), Image.NEAREST)
out.paste(cz, (gx + 40, gy))
for i in range(9):
    d.line((gx + 40 + i * Z, gy, gx + 40 + i * Z, gy + 8 * Z), fill=(60, 60, 60))
    d.line((gx + 40, gy + i * Z, gx + 40 + 8 * Z, gy + i * Z), fill=(60, 60, 60))
d.line((gx + 40 + 4 * Z, gy - 4, gx + 40 + 4 * Z, gy + 8 * Z + 4), fill=WH, width=2)
for line in range(8):
    d.text((gx, gy + line * Z + 4), f"+{line}", font=fm, fill=GR)
    d.text((gx + 40 + 8 * Z + 8, gy + line * Z + 4), f"+{line + 8}", font=fm, fill=GR)
ty = gy + 8 * Z + 14
d.text((gx, ty), "A byte holds four pixels, two bits each:", font=fs, fill=WH)
d.text((gx, ty + 20), "bits 7 6 5 4 = the high bits of pixels 0 1 2 3", font=fm, fill=GR)
d.text((gx, ty + 38), "bits 3 2 1 0 = the low bits of pixels 0 1 2 3", font=fm, fill=GR)
d.text((gx, ty + 56), "so colour 1 is &0F, 2 is &F0, 3 is &FF", font=fm, fill=GR)
print(save(out, "screen-layout.png"))
