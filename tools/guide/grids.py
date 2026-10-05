"""Captioned grids of screenshots for the guide."""
from PIL import Image, ImageDraw
from util import W, crop, font, save

SC = f"{W}/work/scenes"
VB = f"{W}/work"


def grid(items, cols, name, scale=2, playfield=False, cap=15):
    """items: (image or path, caption)."""
    ims = []
    for src, text in items:
        im = src if isinstance(src, Image.Image) else crop(src)
        if playfield:
            im = im.crop((0, 16, 256, 192))
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        ims.append((im, text))
    w, h = ims[0][0].size
    gap, ch = 6, cap + 14
    rows = (len(ims) + cols - 1) // cols
    out = Image.new("RGB", (cols * w + (cols + 1) * gap, rows * (h + ch) + (rows + 1) * gap - (gap if rows else 0) + gap),
                    (28, 28, 28))
    d = ImageDraw.Draw(out)
    f = font(cap)
    for i, (im, text) in enumerate(ims):
        x = gap + (i % cols) * (w + gap)
        y = gap + (i // cols) * (h + ch + gap)
        out.paste(im, (x, y))
        d.text((x + 2, y + h + 5), text, font=f, fill=(240, 240, 240))
    return save(out, name)


def sc(n):
    return f"{SC}/{n}.png"


def room(r):
    return Image.open(f"{VB}/bbc_{r:03d}.png").convert("RGB")


if __name__ == "__main__":
    print(grid([(sc("train_a"), "1. a ladder (room 74)"),
                (sc("pipe_a"), "2. walking a slippery pipe (room 27)"),
                (sc("pipe_b"), "3. stand still on it: he drops through"),
                (sc("slope_b"), "4. walking up a slope (room 21)"),
                (sc("lift_a"), "5. landing on a lift (room 34)"),
                (sc("lift_b"), "6. it sinks while he rides it")], 3, "harry-moves.png"))
    print(grid([(sc("truck_b"), "the truck: Harry jumps out (room 1)"),
                (sc("train_b"), "the train, with the power on (room 74)"),
                (sc("bar_a"), "a rising lift bar (room 26)")], 3, "machines.png"))
    print(grid([(sc("dog_run"), "the dog runs (room 2)..."),
                (sc("dog_sat"), "...and sits when it's blocked"),
                (sc("croc"), "crocodile and steam (room 30)"),
                (sc("drips_a"), "drips form and fall (room 94)"),
                (sc("dino"), "the dinosaur on a scooter (room 120)"),
                (sc("spider"), "spiders on their threads (room 4)")], 3, "monsters.png"))
    print(grid([(sc("rm_33"), "33: the milk vat"), (sc("rm_51"), "51: the cocoa vat"), (sc("rm_110"), "110: the sugar vat"),
                (sc("rm_95"), "95: the toy maker"), (sc("rm_115"), "115: the generator"), (sc("rm_48"), "48: the egg maker"),
                (sc("rm_111"), "111: dispatch"), (sc("girder_a"), "96: the girder"),
                (sc("lift_sign"), "105: the LIFT")], 3, "factory-rooms.png", playfield=True))
    print(grid([(sc("girder_a"), "standing on the girder, TAKE..."), (sc("girder_b"), "...swings it into the gap"),
                (sc("lift_sign"), "the LIFT (room 105)..."), (sc("out_of_order"), "...touch it and see")],
               2, "walk-extras.png"))
    print(grid([(sc("milk_a"), "carrying milk over the vat"), (sc("milk_fall"), "dropped: it falls in"),
                (sc("milk_full"), "the eighth: FULL!, +10,000, a life")], 3, "walk-vat.png"))
    print(grid([(sc("lever_off"), "the generator, off"), (sc("lever_jump"), "jump right past the lever"),
                (sc("lever_on"), "power on: the lamp lights")], 3, "walk-power.png"))
    print(grid([(sc("toy_a"), "the eighth part, over the hopper"), (sc("toy_fall"), "dropped: it falls in"),
                (sc("toy_made"), "with power: the toy (+20,000)")], 3, "walk-toy.png"))
    print(grid([(sc("egg_before"), "carrying the toy onto the egg maker"), (sc("egg_made"), "dropped, vats full: the egg"),
                (sc("deliver_a"), "the egg to the truck at dispatch"), (sc("deliver_truck"), "the truck drives off"),
                (sc("deliver_b"), "and the next egg begins")], 3, "walk-egg.png"))
