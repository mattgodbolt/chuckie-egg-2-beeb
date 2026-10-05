"""The whole factory: the BBC room viewer's 120 rooms in their 10 x 12 grid."""
from PIL import Image, ImageDraw
from util import W, font, label, save

rooms = {r: Image.open(f"{W}/work/bbc_{r:03d}.png").convert("RGB").crop((0, 16, 256, 192)) for r in range(1, 121)}
cw, ch, gap, side, top = 256, 176, 4, 84, 40
img = Image.new("RGB", (2 * side + 10 * cw + 9 * gap, top + 12 * ch + 11 * gap + 40), (40, 40, 40))
d = ImageDraw.Draw(img)
f, fb = font(16), font(22)
for r in range(1, 121):
    c, row = (r - 1) % 10, (r - 1) // 10
    x, y = side + c * (cw + gap), top + row * (ch + gap)
    img.paste(rooms[r], (x, y))
    label(d, x + 2, y + 2, str(r), f)
d.text((side, 8), "Rooms 1-120: right is +1, left -1, down +10, up -10", font=fb, fill=(240, 240, 240))
# the railway: rooms 71-80 (grid row 8) joined end to end
MAG = (255, 80, 255)
y0 = top + 7 * (ch + gap)
x0, x1 = side, side + 10 * cw + 9 * gap
d.rectangle((x0 - 3, y0 - 3, x1 + 2, y0 + ch + 2), outline=MAG, width=4)
ym = y0 + ch // 2
d.line((x1 + 4, ym, x1 + side - 10, ym), fill=MAG, width=4)
d.polygon([(x1 + side - 6, ym), (x1 + side - 20, ym - 9), (x1 + side - 20, ym + 9)], fill=MAG)
d.text((x1 + 10, ym + 12), "to 71", font=f, fill=MAG)
d.line((10, ym, x0 - 8, ym), fill=MAG, width=4)
d.polygon([(x0 - 6, ym), (x0 - 20, ym - 9), (x0 - 20, ym + 9)], fill=MAG)
d.text((10, ym + 12), "from 80", font=f, fill=MAG)
d.text((side, img.height - 32), "The railway, rooms 71-80, loops: walking right out of 80 comes into 71, and left out of "
       "71 into 80.", font=f, fill=MAG)
print(save(img, "factory-map.png"))
