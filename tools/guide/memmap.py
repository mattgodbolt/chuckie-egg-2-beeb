"""The BBC's memory as the game uses it (docs/memory-map.md, build/listing.txt)."""
import math
from PIL import Image, ImageDraw
from util import font, mono, save

MAIN = [  # (start, end exclusive, label, detail, colour)
    (0x0000, 0x0100, "zero page", "the game's state and scratch", (90, 120, 200)),
    (0x0100, 0x0200, "page 1", "tables, and the stack in its top 64 bytes", (110, 110, 160)),
    (0x0200, 0x0400, "pages 2-3", "the interrupt vector, tables; the rest the OS's", (120, 120, 120)),
    (0x0400, 0x0D00, "the three maps", "attribute &0400, tile &0700, cell type &0A00", (60, 150, 90)),
    (0x0D00, 0x0E00, "LowState", "monsters, checkpoint, score, lives", (90, 120, 200)),
    (0x0E00, 0x44F5, "code and tables", "Harry, monsters, objects, machines, drawing...", (200, 120, 60)),
    (0x44F5, 0x5000, "free", "about 2.8K", (50, 50, 50)),
    (0x5000, 0x8000, "screen", "256 x 192, MODE 1 pixels", (170, 60, 60)),
]
BANK = [
    (0x8000, 0x8105, "mailbox", "keys, scores, the RNG: survives the reset", (150, 90, 170)),
    (0x8105, 0x82FF, "palettes, bands", "their code, 49 splits, 30 palettes", (60, 150, 150)),
    (0x82FF, 0x9F1D, "packed rooms", "6,845 bytes and their code tables", (60, 150, 90)),
    (0x9F1D, 0xB7E0, "sprites", "Harry, monsters, truck, train, lifts", (200, 160, 50)),
    (0xB7E0, 0xB9C0, "tile font", "60 tiles x 8 bytes", (200, 120, 60)),
    (0xB9C0, 0xC000, "free", "about 1.6K", (50, 50, 50)),
]


def h(size):
    return max(26, int(9 * math.sqrt(size / 16)))


f, fs, fm = font(14), font(12, False), mono(12)
colw, gap = 210, 390
x_main, x_bank = 70, 70 + colw + gap
total_main = sum(h(e - s) for s, e, *_ in MAIN)
total_bank = sum(h(e - s) for s, e, *_ in BANK)
H = max(total_main, total_bank) + 110
img = Image.new("RGB", (x_bank + colw + 330, H), (28, 28, 28))
d = ImageDraw.Draw(img)
d.text((x_main, 12), "Main RAM (32K)", font=font(16), fill=(240, 240, 240))
d.text((x_bank, 12), "Sideways RAM bank, paged in at &8000 (16K)", font=font(16), fill=(240, 240, 240))
d.text((x_main, H - 34), "Heights are not to scale. Figures from the build at the time of writing; "
       "the build prints the current ones.", font=fs, fill=(170, 170, 170))


def column(x, blocks):
    y = 44
    for s, e, label, detail, col in blocks:
        hh = h(e - s)
        d.rectangle((x, y, x + colw, y + hh - 2), fill=col)
        d.text((x + 8, y + hh / 2 - 9), label, font=f, fill=(255, 255, 255))
        d.text((x - 62, y - 2), f"&{s:04X}", font=fm, fill=(200, 200, 200))
        d.text((x + colw + 10, y + hh / 2 - 8), detail, font=fs, fill=(220, 220, 220))
        y += hh
    d.text((x - 62, y - 8), f"&{blocks[-1][1]:04X}", font=fm, fill=(200, 200, 200))


column(x_main, MAIN)
column(x_bank, BANK)
y = 44 + total_bank + 20
d.text((x_bank, y), "&C000: the OS ROM's font, read in place for text", font=fs, fill=(220, 220, 220))
d.text((x_bank, y + 18), "(on a Master, a copy in HAZEL at the same address)", font=fs, fill=(170, 170, 170))
print(save(img, "memory-map.png"))
