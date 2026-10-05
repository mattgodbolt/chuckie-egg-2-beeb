#!/usr/bin/env python3
"""The build's memory, module by module, from build/listing.txt and
build/symbols.json. Run from the repository root after `make`."""
import json
import re

sym = json.load(open("build/symbols.json"))["src/main.6502"]
lines = open("build/listing.txt").read().splitlines()


def marks(start_pat, end_pat):
    """(address, name) for each INCLUDE/INCBIN between two listing lines."""
    out, on = [], False
    for ln in lines:
        if re.search(start_pat, ln):
            on = True
        if on:
            m = re.match(r"\s+([0-9A-F]{4})\s.*(INCLUDE|INCBIN) \"([^\"]+)\"", ln)
            if m:
                out.append((int(m.group(1), 16), m.group(3)))
            elif re.match(r"\s+([0-9A-F]{4})\s+\.(\w+)$", ln) and on:
                pass
        if on and re.search(end_pat, ln):
            break
    return out


def table(title, items, end):
    print(f"\n{title}")
    total = 0
    for (a, n), nxt in zip(items, [i[0] for i in items[1:]] + [end]):
        print(f"  &{a:04X} {n:28s} {nxt - a:6d}")
        total += nxt - a
    print(f"  {'total':34s} {total:6d}")


code = marks(r"SECTION Code,", r"ENDSECTION")
code = [c for c in code if c[0] >= 0x0E00]
table("Main RAM code section (&0E00 up)", code, sym["code_end"])
print(f"  free below &5000: {0x5000 - sym['code_end']}")

data = marks(r"SECTION Data,", r"ENDSECTION")
data = [(0x8000, "magic")] + data
table("Sideways bank", data, sym["data_end"])
print(f"  free in bank: {0xC000 - sym['data_end']}")

# The pieces of the code section that are data, not code.
pieces = ["harry_frames", "sprite_frames", "monster_table", "things", "visits",
          "thing_types", "mon_types", "death_notes", "death_notes_end", "band_cmaps",
          "objgfx", "code_end"]
print("\nData inside the code section")
for a, b in zip(pieces, pieces[1:]):
    print(f"  {a:16s} &{sym[a]:04X} {sym[b] - sym[a]:6d}")
print("\nOther")
for s in ["page1", "page1_end", "page2", "page2_end", "loader", "loader_end", "menu",
          "mailbox", "mailbox_end", "packed_rooms", "sprites", "tiles", "data_end"]:
    if s in sym:
        print(f"  {s:16s} &{sym[s]:04X}")
