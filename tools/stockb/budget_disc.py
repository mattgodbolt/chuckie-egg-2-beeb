#!/usr/bin/env python3
"""The stock-B budget, from this build's symbols: what main RAM must hold in
each plan, and what is left. Measured items come from build/symbols.json;
new code is estimated (marked ~).

Run from the repository root after `make`: python3 <this>.
"""
import json

def load_symbols(path="build/symbols.json"):
    """Baron 0.5's --symbols (format 2), flattened to {name: value}."""
    out = {}
    for assembly in json.load(open(path))["assemblies"]:
        for section in assembly["sections"]:
            for kind in section.values():
                if isinstance(kind, dict):
                    out.update((k, v["value"]) for k, v in kind.items()
                               if isinstance(v, dict) and "value" in v and "@" not in k)
    return out


s = load_symbols()
MAIN = 0x5000 - 0x0E00                       # code and data under the screen
used = s["code_end"] - 0x0E00
free = 0x5000 - s["code_end"]
bank = s["data_end"] - 0x8000

tiles = s["data_end"] - s["tiles"]
sprites = s["tiles"] - s["sprites"]
harry = 294                                  # sprites.bin's first 294 bytes (mkgfx: Harry's frames, kept whole)
bands_code = s["room_bands"] - s["setup_bands"]
room_bands = s["band_maps"] - s["room_bands"]
band_maps = s["room_palettes"] - s["band_maps"]
palettes = s["packed_rooms"] - s["room_palettes"]
packed = s["packed_lengths"] - s["packed_rooms"]
lengths = 120
unpack_tables = s["sprites"] - s["tier_width"]
mailbox = s["mailbox_end"] - s["mailbox"]
monster_table = s["things"] - s["monster_table"] - (s["things"] - s["obj_frames"] if "obj_frames" in s else 146)

print(f"main RAM &0E00-&4FFF: {MAIN}; used {used}; free {free}")
print(f"bank: {bank} (tiles {tiles}, sprites {sprites} incl. Harry {harry}, packed rooms {packed}, "
      f"lengths {lengths}, unpack tables {unpack_tables}, palettes {palettes}, bands {room_bands}+{band_maps}, "
      f"bands code {bands_code}, mailbox {mailbox}, magic {s['mailbox'] - 0x8000})")
print(f"shortfall if everything stays resident: {bank - free}")

print("\nPlan: per-room records from disc (OSWORD &7F), MODE 1 screen as now")
add = [
    ("tile font (bank -> main)", tiles),
    ("Harry's frames (bank -> main)", harry),
    ("setup_bands (bank -> main)", bands_code),
    ("band colour maps (bank -> main)", band_maps),
    ("unpacker's tier and vocabulary tables (bank -> main)", unpack_tables),
    ("record buffer (largest record, room 120: 1,017)", 1024),
    ("~ record loader: OSWORD &7F block and call, retry, pointer patching, monster entries", 250),
    ("record start sectors (a byte a room)", 120),
    ("mailbox the game keeps: keys, RNG, flags, the OS bytes a BREAK keeps", 8 + 4 + 4 + 29),
    ("high-score table and filename (or MENU keeps them on disc: 0)", 150 + 20),
    ("WORDV (&020C) left to the MOS: a 2-byte hole in page 2's tables (measured: the rest may hold tables)", 2),
    ("page-1 tables out of the stack's way (the DFS call takes 50 bytes of stack)", 32),
    ("LowState up to &0D1B-&0DB9, over the B's extended vectors (measured: the read still works): 0", 0),
    ("the DFS's bytes in page &10 (&1073, &1080-&108F, &10D6) kept clear of code: ~48", 48),
]
sub = [
    ("monster table (each room's entries go in its record; the dog's swap and the egg's limit become flags)", monster_table - 10),
    ("~ the bank's paging (system.6502)", 15),
]
need = sum(v for _, v in add)
gain = sum(v for _, v in sub)
for k, v in add:
    print(f"  + {v:5d}  {k}")
for k, v in sub:
    print(f"  - {v:5d}  {k}")
print(f"  net {need - gain} against {free} free: {free - need + gain} left")
opt = [("monster types into the records too (a room's 4 at most)", 208 - 20),
       ("high-score table kept on disc by MENU instead", 170),
       ("start sectors as 2 bits a room (sectors per record) instead of a byte", 90)]
print("  options:")
for k, v in opt:
    print(f"    - {v:4d}  {k}")
print(f"  with all of them: {free - need + gain + sum(v for _, v in opt)} left")
