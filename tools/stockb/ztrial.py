#!/usr/bin/env python3
"""ZX02 trials on the game's data: how much would each file shrink?
Run from the repository root with .venv/bin/python."""
import sys
sys.path.insert(0, "tools")
import zx02  # noqa: E402
from zx import Spectrum  # noqa: E402

m = Spectrum("build/zx_start.z80").mem
files = {
    "sprites.bin (packed, decision 26)": open("src/data/sprites.bin", "rb").read(),
    "sprites raw (original &DFA2-&FDF7)": bytes(m[0xDFA2:0xFDF8]),
    "objgfx.bin": open("src/data/objgfx.bin", "rb").read(),
    "things.bin": open("src/data/things.bin", "rb").read(),
    "monsters.bin": open("src/data/monsters.bin", "rb").read(),
    "packed.bin (rooms)": open("src/data/packed.bin", "rb").read(),
    "tiles.bin": open("src/data/tiles.bin", "rb").read(),
    "visits.bin": open("src/data/visits.bin", "rb").read(),
    "thingtypes.bin": open("src/data/thingtypes.bin", "rb").read(),
}
for name, data in files.items():
    z = zx02.compress(data)
    assert zx02.decompress(z) == data
    print(f"{name:40s} {len(data):6d} -> {len(z):6d}  ({100*len(z)/len(data):.0f}%)", flush=True)
