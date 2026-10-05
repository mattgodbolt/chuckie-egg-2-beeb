"""Harry's jump on flat ground, from the original's arc table (&89CF)."""
from PIL import Image, ImageDraw
from util import font, save

ARC = [4, 4, 3, 2, 1, 1, 1, 0, 0, 0, 0, -1, -1, -1, -2, -3, -4, -4, -4, -4, -4]
pts = [(0, 0)]
h = 0
for n, dy in enumerate(ARC, 1):
    h += dy
    pts.append((2 * n, h))
    if h <= 0:
        break               # lands: pass 18 on flat ground
assert pts[-1] == (36, 0) and len(pts) == 19

S = 2                       # supersample
K = 16                      # screen pixels per game pixel
SURF, GRID, AXIS = (252, 252, 251), (226, 225, 220), (140, 139, 134)
INK, INK2, SERIES = (11, 11, 11), (82, 81, 78), (42, 120, 214)
ml, mr, mt, mb = 70, 30, 60, 60
W, H = ml + 40 * K + mr, mt + 20 * K + mb
img = Image.new("RGB", (W * S, H * S), SURF)
d = ImageDraw.Draw(img)


def P(x, y):
    return ((ml + x * K) * S, (mt + (20 - y) * K) * S)


f, fb, fs = font(13 * S, bold=False), font(14 * S), font(12 * S, bold=False)
# cell grid: 8-pixel character cells
for x in range(0, 41, 8):
    d.line([P(x, 0), P(x, 20)], fill=GRID, width=S)
for y in range(0, 21, 8):
    d.line([P(0, y), P(40, y)], fill=GRID, width=S)
d.line([P(0, 0), P(40, 0)], fill=AXIS, width=S)
for x in range(0, 41, 8):
    t = str(x)
    d.text((P(x, 0)[0] - d.textlength(t, font=fs) / 2, P(x, 0)[1] + 6 * S), t, font=fs, fill=INK2)
d.text((8 * S, P(0, 20)[1] - 2 * S), "px up", font=fs, fill=INK2)
for y in (0, 8, 16):
    t = str(y)
    d.text((P(0, y)[0] - d.textlength(t, font=fs) - 8 * S, P(0, y)[1] - 8 * S), t, font=fs, fill=INK2)
d.text((P(20, 0)[0] - 120 * S, P(0, 0)[1] + 28 * S), "pixels along (2 a pass, fixed at take-off)", font=f, fill=INK2)
d.text((10 * S, 14 * S), "Harry's jump: height after each main-loop pass", font=fb, fill=INK)
d.text((10 * S, 34 * S), "from the original's arc table; one pass is three frames", font=fs, fill=INK2)
# the arc
d.line([P(x, y) for x, y in pts], fill=SERIES, width=2 * S, joint="curve")
for x, y in pts:
    cx, cy = P(x, y)
    r = 5 * S
    d.ellipse((cx - r - 2 * S, cy - r - 2 * S, cx + r + 2 * S, cy + r + 2 * S), fill=SURF)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=SERIES)
# annotations
cx, cy = P(18, 16)
d.text((cx - 30 * S, cy - 26 * S), "peak 16 px: exactly two cells", font=fs, fill=INK)
cx, cy = P(36, 0)
d.text((cx - 150 * S, cy - 24 * S), "lands on pass 18, 36 px along", font=fs, fill=INK)
img = img.resize((W, H), Image.LANCZOS)
print(save(img, "jump-arc.png"))
