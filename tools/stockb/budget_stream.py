#!/usr/bin/env python3
"""The streaming stock-B budget with our own NMI disc driver and a cache,
from this build's symbols. Estimates marked ~. Run from the repo root."""
import json
def load_symbols(path="build/symbols.json"):
    out = {}
    for a in json.load(open(path))["assemblies"]:
        for s in a["sections"]:
            for kind in s.values():
                if isinstance(kind, dict):
                    out.update((k, v["value"]) for k, v in kind.items()
                               if isinstance(v, dict) and "value" in v and "@" not in k)
    return out
s = load_symbols()
free = 0x5000 - s["code_end"]
tiles = s["data_end"] - s["tiles"]; harry = 294
bands_code = s["room_bands"] - s["setup_bands"]; band_maps = s["room_palettes"] - s["band_maps"]
unpack_tables = s["sprites"] - s["tier_width"]
mt = s["things"] - s["monster_table"] - 146
P = print
P(f"main RAM free now: {free} (code_end &{s['code_end']:04X})")
add = [
    ("tile font, from the bank", tiles),
    ("Harry's frames, from the bank", harry),
    ("setup_bands, from the bank", bands_code),
    ("band colour maps, from the bank", band_maps),
    ("unpacker's tier/vocabulary tables, from the bank", unpack_tables),
    ("mailbox the game keeps (keys 8, RNG 4, flags 4, OS bytes for BREAK 29) + record file's start 2", 47),
    ("high-score table and filename (0 if MENU keeps them in a file)", 170),
    ("record index: first sector of each record, a byte a room (228 < 256 sectors)", 121),
    ("~ LowState displaced from &0D00-&0D13 by the NMI stub (20 bytes), into main RAM", 20),
    ("~ disc driver (8271 on a B / 1770 on a Master, same slot): command, seek+read, result, retry, motor keep-alive", 250),
    ("~ cache: slot table, lookup, LRU, install (frame pointers, monster entries, palette/bands), prefetch policy", 300),
    ("exits table: 4 bits a room (L R U D), destinations computed as change_room does", 60),
]
sub = [
    ("monster table: entries go in the records (dog-sat flag + the egg's limit kept)", mt - 10),
    ("~ the bank's paging (system.6502)", 15),
]
need = sum(v for _, v in add); gain = sum(v for _, v in sub)
for k, v in add: P(f"  + {v:5d}  {k}")
for k, v in sub: P(f"  - {v:5d}  {k}")
left = free - need + gain
P(f"  net {need-gain}: {left} left in main RAM for cache buffers (both machines)")
opt = [("monster types into the records (4 bytes an entry beside the entry)", 208 - 20),
       ("high scores + filename kept by MENU in a file", 170)]
for k, v in opt: P(f"  option - {v:4d}  {k}")
o = left + sum(v for _, v in opt)
P(f"  with the options: {o}")
P(f"  B-only regions (measured safe for BREAK on OS 1.20, decision 22 forbids them on a Master): page 3 256, &0D9F-&0DEF 81 -> {o + 337}")
