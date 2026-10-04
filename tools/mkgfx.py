#!/usr/bin/env python3
"""Extract the original's sprites and their pointer tables.

    .venv/bin/python tools/mkgfx.py [--snap build/zx_start.z80]

Writes, committed (the build never runs this):
    src/data/sprites.bin    the sprite block &DFA2-&FDF7: Harry, the
                            monsters, truck, train and lifts
                            (docs/research/monsters.md, section 8), each
                            frame a column at a time, packed (below)
    src/data/gfx.6502       pointer tables into it, relocated to `sprites`
    src/data/monsters.bin   the monster table (&6B00, four 256-byte columns:
                            room, row, column, type)
    src/data/montypes.bin   the 52 monster types (&6F00, 4 bytes: ink, base
                            frame, flags, speed): docs/research/monsters.md,
                            section 3. (Apart, because it lives in page 3.)

A sprite frame is the original's: height in character rows, width in
bytes, then its pixels, 1 bit a pixel; but the pixels are stored a column
at a time (height*8 bytes for each byte across) where the original has a
row at a time (decision 20): the BBC draws a column at a time, and steps
down a column with an index alone (sprite.6502).

And a monster's or a lift's frame (and an object's: tools/mkobjects.py)
leaves out what drawing it doesn't need (decision 26):
- Its empty lines at the top and bottom (every column's): how many in the
  height byte's bits 3-7 (top) and the width byte's bits 4-6 (bottom).
  Drawing or erasing an empty line changes nothing.
- A frame that is another's mirror image (the left-facing frames of a few
  monsters are the right-facing ones turned over) keeps only its header,
  with bit 7 of the width byte set, and then where its twin's pixels are,
  relative to the header. sprite.6502 walks the twin's columns the other
  way and turns each byte over.
Harry's frames (collide.6502 reads his pixels) and the truck's and train's
strips (machines.6502 paints their empty lines in the paper) keep every
line and their own pixels, so their header bytes are the original's. The
16 bytes no pointer reaches (&EA8E) are left out.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from zx import Spectrum  # noqa: E402

SPRITES, SPRITES_END = 0xDFA2, 0xFDF8
HARRY_FRAMES = 0x89FF       # 12 pointers to frame headers
SPRITE_FRAMES = 0x91B7      # 152 pointers: monsters, truck, train, lifts
MONSTERS, MONTYPES, MONTYPES_END = 0x6B00, 0x6F00, 0x6FD0
# The sprite frames machines.6502 paints as strips: the train (&47-&50) and
# the truck (&7C-&89).
STRIPS = set(range(0x47, 0x51)) | set(range(0x7C, 0x8A))
MIRROR = 0x80               # the width byte's bit 7: a mirror image's stub
REV = [int(f"{b:08b}"[::-1], 2) for b in range(256)]


def columns(m, ptr):
    """The frame at ptr in the original's memory: h, w and its columns (its
    rows made columns: one byte wide, the same either way)."""
    h, w = m[ptr], m[ptr + 1]
    return h, w, [bytes(m[ptr + 2 + line * w + col] for line in range(h * 8)) for col in range(w)]


def trimmed(cols):
    """The empty lines at the top and bottom of these columns, and the
    columns without them."""
    lines = len(cols[0])
    top = 0
    while top < lines and not any(c[top] for c in cols):
        top += 1
    bottom = 0
    while bottom < lines - top and not any(c[lines - 1 - bottom] for c in cols):
        bottom += 1
    return top, bottom, [c[top:lines - bottom] for c in cols]


def mirrored(cols):
    """The columns of a frame turned over left to right."""
    return [bytes(REV[b] for b in c) for c in reversed(cols)]


def pack(m, frames, plain=()):
    """The frames (pointers into m) packed, in the order they are in m, all
    but the plain ones trimmed or turned into mirror images' stubs: the
    block and their offsets in it. (tools/mkobjects.py packs the objects'
    the same way.)"""
    blob, where, kept = bytearray(), {}, {}
    for ptr in sorted(set(frames)):
        h, w, cols = columns(m, ptr)
        where[ptr] = len(blob)
        if ptr in plain:
            blob += bytes([h, w]) + b"".join(cols)
            continue
        top, bottom, held = trimmed(cols)
        assert h < 8 and w < 16 and top < 32 and bottom < 8 and held[0], hex(ptr)
        header = bytes([h | top << 3, w | bottom << 4])
        twin = kept.get((header, tuple(mirrored(held))))
        if twin is not None:
            # A mirror image: its header, flagged, then where its twin's
            # pixels are, relative to the header.
            blob += bytes([header[0], header[1] | MIRROR]) + ((twin - where[ptr]) & 0xFFFF).to_bytes(2, "little")
            continue
        kept[header, tuple(held)] = len(blob) + 2
        blob += header + b"".join(held)
    return bytes(blob), where


def unpack(blob, o):
    """The frame at o in a packed block with every line, its own pixels and
    its header bytes plain: as columns(m, ptr) has it."""
    h, w = blob[o] & 7, blob[o + 1] & 15
    top, bottom = blob[o] >> 3, blob[o + 1] >> 4 & 7
    lines = h * 8 - top - bottom
    p = o + 2
    if blob[o + 1] & MIRROR:
        p = (o + (blob[o + 2] | blob[o + 3] << 8)) & 0xFFFF
    held = [blob[p + c * lines:p + (c + 1) * lines] for c in range(w)]
    if blob[o + 1] & MIRROR:
        held = mirrored(held)
    return h, w, [bytes(top) + c + bytes(bottom) for c in held]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", default="build/zx_start.z80")
    ap.add_argument("--out", default="src/data")
    args = ap.parse_args()
    m = Spectrum(args.snap).mem
    word = lambda a: m[a] | m[a + 1] << 8
    harry = [word(HARRY_FRAMES + 2 * i) for i in range(12)]
    others = [word(SPRITE_FRAMES + 2 * i) for i in range(152)]
    assert all(SPRITES <= p < SPRITES_END for p in harry + others)
    plain = set(harry) | {others[i] for i in STRIPS}
    assert not plain & {p for i, p in enumerate(others) if i not in STRIPS}
    # In the original's order, so Harry's frame 0 stays at `sprites`, which
    # objects.6502's restart record names.
    blob, where = pack(m, harry + others, plain)
    assert where[harry[0]] == 0
    for ptr in set(harry + others):
        assert unpack(blob, where[ptr]) == columns(m, ptr), hex(ptr)
    with open(f"{args.out}/sprites.bin", "wb") as f:
        f.write(blob)

    def rel(ptr):
        return f"sprites + &{where[ptr]:04X}"

    lines = [
        "\\ Generated by tools/mkgfx.py from the original: do not edit.",
        "",
        "\\ Harry's frames (&89FF), by facing + xf: 0-3 right, 4-7 left (shifted",
        "\\ 0/2/4/6 pixels, also the walk cycle), 8-11 climbing. Each points at",
        "\\ the frame's header (height in cells, width in bytes).",
        ".harry_frames",
    ]
    for i in range(12):
        lines.append(f"    EQUW {rel(word(HARRY_FRAMES + 2 * i))}")
    lines += [
        "",
        "\\ The other sprites' frames (&91B7): monsters, truck, train, lifts. A",
        "\\ monster type's base frame indexes this table.",
        ".sprite_frames",
    ]
    for i in range(152):
        lines.append(f"    EQUW {rel(word(SPRITE_FRAMES + 2 * i))}")
    with open(f"{args.out}/monsters.bin", "wb") as f:
        f.write(bytes(m[MONSTERS:MONTYPES]))
    with open(f"{args.out}/montypes.bin", "wb") as f:
        f.write(bytes(m[MONTYPES:MONTYPES_END]))
    with open(f"{args.out}/gfx.6502", "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"sprites.bin: {len(blob)} bytes (the original's {SPRITES_END - SPRITES})")


if __name__ == "__main__":
    main()
