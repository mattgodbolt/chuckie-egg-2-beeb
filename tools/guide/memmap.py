"""The BBC's memory as the game uses it (docs/memory-map.md, build/listing.txt)."""
import json
import math
import os
from PIL import Image, ImageDraw
from util import REPO, font, mono, save

# The boundaries from the sideways RAM edition's build (make first), so the
# picture is redrawn true by running this again.
SYMS = {}
for asm in json.load(open(os.path.join(REPO, "build", "ce2.r.json")))["assemblies"]:
    for sec in asm["sections"]:
        for k, v in sec.get("labels", {}).items():
            if "@" not in k and "." not in k:
                SYMS[k] = v["value"]
        for k, v in sec.get("assignments", {}).items():
            if "@" not in k and "." not in k and isinstance(v.get("value"), (int, float)):
                SYMS[k] = int(v["value"])
S = SYMS.__getitem__


def free(n):
    return f"{n:,} bytes"


MAIN = [  # (start, end exclusive, label, detail, colour)
    (0x0000, 0x0100, "zero page", "the game's state and scratch", (90, 120, 200)),
    (0x0100, 0x0200, "page 1", "tables, then the stack", (110, 110, 160)),
    (0x0200, 0x0400, "pages 2-3", "the interrupt vector; the rest the OS's", (120, 120, 120)),
    (0x0400, 0x0D00, "the three maps", "attribute &0400, tile &0700, cell type &0A00", (60, 150, 90)),
    (0x0D00, 0x0E00, "LowState", "checkpoint, monsters, score, lives; the room's groups", (90, 120, 200)),
    (S("code_start"), S("music"), "code and tables", "Harry, monsters, objects, machines, drawing...", (200, 120, 60)),
    (S("music"), S("code_end"), "the music", "the Sugar Plum Fairy's events and pitches", (170, 90, 150)),
    (S("code_end"), S("screen"), "free", free(S("screen") - S("code_end")), (50, 50, 50)),
    (S("screen"), 0x8000, "screen", "256 x 192, MODE 1 pixels", (170, 60, 60)),
]
BANK = [
    (0x8000, S("mailbox"), "mark", "how the front end knows the bank", (120, 120, 120)),
    (S("mailbox"), S("mailbox_end"), "mailbox", "keys, scores, high scores: kept over a reset", (150, 90, 170)),
    (S("records"), S("data_end"), "the rooms' records", "each room, its colours and monsters, and sprites", (60, 150, 90)),
    (S("data_end"), 0xC000, "free", free(0xC000 - S("data_end")), (50, 50, 50)),
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
d.text((x_main, H - 34), "Heights are not to scale. The sideways RAM edition, from the build "
       "(tools/guide/memmap.py redraws it).", font=fs, fill=(170, 170, 170))


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
