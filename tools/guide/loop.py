"""The main loop's three frames (src/game.6502's game_loop; the original's &77B9)."""
from PIL import Image, ImageDraw
from util import font, mono, save

DRAW, LOGIC, CONTACT, HARRY = (170, 60, 60), (70, 110, 180), (150, 90, 170), (200, 150, 40)
cols = [
    ("frame 1", [
        ("draw monsters, the thing", "draw_monsters, draw_object", DRAW),
        ("contact, drop, falling", "collide, drop, falling", CONTACT),
        ("keys", "read_keys", LOGIC),
        ("Harry moves", "harry_update", HARRY),
        ("a room change?", "change_room", LOGIC),
        ("the movement tick", "move_sound", LOGIC),
    ]),
    ("frame 2", [
        ("draw Harry", "draw_harry", DRAW),
        ("train or truck", "machines", LOGIC),
        ("the lift", "run_lift", LOGIC),
        ("the next thing", "next_object", LOGIC),
        ("monsters, tick A", "monsters_tick", LOGIC),
    ]),
    ("frame 3", [
        ("draw monsters, the thing", "draw_monsters, draw_object", DRAW),
        ("contact, drop, falling", "collide, drop, falling", CONTACT),
        ("monsters, tick B", "monsters_tick", LOGIC),
        ("the next thing", "next_object", LOGIC),
    ]),
]
f, fh, fm = font(14), font(16), mono(12)
cw, bh, gap, top = 270, 50, 40, 70
W = 3 * cw + 4 * gap
H = top + 6 * (bh + 8) + 90
img = Image.new("RGB", (W, H), (28, 28, 28))
d = ImageDraw.Draw(img)
d.text((gap, 14), "One pass of the main loop: three frames, 1/50 s each (16.7 passes a second)", font=fh,
       fill=(240, 240, 240))
for i, (title, boxes) in enumerate(cols):
    x = gap + i * (cw + gap)
    d.text((x, top - 26), title, font=fh, fill=(240, 240, 240))
    y = top
    for label, code, col in boxes:
        d.rounded_rectangle((x, y, x + cw, y + bh), radius=6, fill=col)
        d.text((x + 10, y + 7), label, font=f, fill=(255, 255, 255))
        d.text((x + 10, y + 28), code, font=fm, fill=(235, 235, 235))
        y += bh + 8
    # the wait for VSync that ends the frame
    vx = x + cw + gap / 2
    d.line((vx, top - 30, vx, top + 6 * (bh + 8)), fill=(255, 255, 255), width=2)
    d.text((vx - 24, top + 6 * (bh + 8) + 6), "VSync", font=fm, fill=(255, 255, 255))
y = H - 50
d.text((gap, y), "Each frame starts with the drawing, just after the vertical sync, where the original's interrupt handler "
       "drew. A pass starts", font=font(12, False), fill=(200, 200, 200))
d.text((gap, y + 18), "at read_keys: the contact test above it in frame 1 is the last part of the pass before.",
       font=font(12, False), fill=(200, 200, 200))
print(save(img, "main-loop.png"))
