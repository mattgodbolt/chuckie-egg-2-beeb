#!/usr/bin/env python3
"""Extract the original's objects ("things") as they are on the tape.

    .venv/bin/python tools/mkobjects.py [--snap build/ce2.z80]

From the snapshot taken as the tape finishes loading (nothing has run on
the tables yet). Writes, committed (the build never runs this):
    src/data/things.bin     the thing table &6600-&69FF: room (bit 7 = not
                            in the world), row, column, type, 256 each
    src/data/thinginit.bin  rooms, rows, columns of things 0-&28 (their
                            start, restored every egg)
    src/data/visits.bin     the room-visit bonus &A380-&A3F8 (room 0-120)
    src/data/objgfx.bin     the object images &6FD0-&74B7, each a column
                            at a time, packed as the monsters' are
                            (tools/mkgfx.py), in the port's order of the
                            graphics (below): the ones a portable thing
                            other than the toy and its parts can show
    src/data/fixgfx.bin     ... and after them, the ones only fixed things
                            show (the streaming edition keeps those in its
                            rooms' records: tools/mkrecords.py)
    src/data/toys.bin       the four toys, a block each (below), one after
                            another, in the order of egg AND 3
    src/data/objects.6502   the graphics' offsets in objgfx (&8A98's
                            pointers but the toys'), their low bytes
                            relocated to `objgfx`, and where its pages
                            start; where each toy's block starts in
                            toys.bin; the types that things have
                            (&6A00-&6AC8, renumbered: below) as three
                            lists, inks, kinds, and the graphics of types
                            9 on; the portable things' types from &24
                            (below)
See docs/research/objects.md.

The graphics: the original's pointers &00-&07 and &0E are the boat's (the
tape's types 0-8 have them), and &37-&3F the boat's again, for &9B08's
base + t, each egg's toy and its parts (types 0-8) taking the nine of
toy ((egg - 1) AND 3) + 1 from &1C + 9 x the toy. The port keeps each
toy's nine apart, in a block of its own (decision 45): the jet's for egg
AND 3 = 0, the motorbike's, the car's, then the boat's. A block is the
nine graphics' offsets from its start, type t's at t, then the graphics,
packed as objgfx's are (a mirror image's twin one of the nine, or kept
whole). Only the loader (objects.6502's toy_load) knows which egg's is
in: the rest reads the toy's graphics from it, so the toy's types have
no graphic numbers. The rest of the graphics are in the original's
order, those a portable thing shows first (so the ones only fixed things
show come last, and the streaming edition can leave them out of main
RAM: decision 42), and the types' graphics renumbered to match, so every
type has the same picture. They are packed in that order, so their
offsets in objgfx go up with their numbers, and thing_load works out a
graphic's high byte from which of objgfx's pages starts at or below it
(OBJ_PAGES), instead of a table.

The types: only the ones some thing has (five never are), in the order
(objects.6502's thing_load relies on it, as its port_types): the toy's
eight parts 0-7 (things 0-7), the toy 8 (&27), the ingredients 9-11
(things 8-&1F, 8 to a type: 8 + thing / 8), the baskets 12 (&20-&23, 8 +
thing / 8 too), the bone, the girder, the ladder and the egg (&24, &25,
&26, &28), then the rest in the original's order. So a portable thing's
type needn't be stored: below &24 it is worked out, and the five from &24
are a table. The portable things' types are the first PORT_TYPES, and the
ones only fixed things have come after them.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from zx import Spectrum  # noqa: E402
from mkgfx import MIRROR, columns, mirrored, trimmed, unpack  # noqa: E402

THINGS, TYPES, TYPES_END = 0x6600, 0x6A00, 0x6AC9
VISITS, VISITS_END = 0xA380, 0xA3F9
OBJGFX, OBJGFX_END = 0x6FD0, 0x74B8
OBJ_POINTERS, OBJ_POINTER_COUNT = 0x8A98, 73
NPORT = 0x29                # things 0-&28 are portable (objects.6502)
TOY_TYPES = 9               # the toy's parts and the toy: types 0-8
PORT_TYPES = 17             # the portable things' types: 0-16 (the docstring)


def pack_in_order(m, ptrs):
    """tools/mkgfx.py's pack, but the frames in the order given (each
    once), not their addresses': the block and their offsets in it."""
    blob, where, kept = bytearray(), {}, {}
    for ptr in dict.fromkeys(ptrs):
        h, w, cols = columns(m, ptr)
        where[ptr] = len(blob)
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


def type_numbers(t_type):
    """The port's number for each original type a thing has (the
    docstring); t_type is the thing table's types (things.bin's last 256
    bytes). tools/mkrecords.py numbers the fixed things' types with it."""
    first = [*range(8), 0x27, 0x08, 0x10, 0x18, 0x20, 0x24, 0x25, 0x26, 0x28]
    order = [t_type[x] for x in first]
    assert order[:TOY_TYPES] == list(range(TOY_TYPES))
    order += [t for t in sorted(set(t_type)) if t not in order]
    assert len(set(order)) == len(order)
    number = {t: i for i, t in enumerate(order)}
    # A portable thing's type, as thing_load works it out.
    for x in range(0x24):
        assert number[t_type[x]] == (x if x < 8 else 8 + (x >> 3)), hex(x)
    return number


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", default="build/ce2.z80")
    ap.add_argument("--out", default="src/data")
    args = ap.parse_args()
    m = Spectrum(args.snap).mem
    word = lambda a: m[a] | m[a + 1] << 8
    out = lambda name, a, b: open(f"{args.out}/{name}", "wb").write(bytes(m[a:b]))
    out("things.bin", THINGS, THINGS + 1024)
    # Where the 41 portable things start each egg (the original copies these
    # to &5B00 at start-up and back at every egg): rooms, rows, columns.
    open(f"{args.out}/thinginit.bin", "wb").write(
        bytes(m[THINGS:THINGS + 41] + m[THINGS + 256:THINGS + 256 + 41] + m[THINGS + 512:THINGS + 512 + 41]))
    out("visits.bin", VISITS, VISITS_END)
    # The images packed as the monsters' are (tools/mkgfx.py): a column at
    # a time, without their empty top and bottom lines, a mirror image as
    # a stub.
    pointers = [word(OBJ_POINTERS + 2 * i) for i in range(OBJ_POINTER_COUNT)]
    assert all(OBJGFX <= p < OBJGFX_END for p in pointers)
    # The port's order of the original's graphics (the docstring), and
    # each one's new number: the toys' interleaved, by egg AND 3 (&9B08's
    # base: &1C + 9 x the egg's toy, 1-4, the jet's 4 for eggs 4, 8 ...),
    # the boat's second copy for the first.
    boat = list(range(0x37, 0x40))
    tape_boat = [*range(8), 0x0E]
    assert [pointers[g] for g in boat] == [pointers[g] for g in tape_boat]
    toy = lambda e, t: 0x1C + 9 * (((e - 1) & 3) + 1) + t
    toys = [[tape_boat[t] if toy(e, t) in boat else toy(e, t) for t in range(TOY_TYPES)] for e in range(4)]
    toy_ptrs = {pointers[g] for gs in toys for g in gs}
    # The rest: first the graphics of the portable things' other types
    # (the thing table's first NPORT things'), then the ones only fixed
    # things show.
    things = bytes(m[THINGS:THINGS + 1024])
    t_type = things[768:]
    types = bytes(m[TYPES:TYPES_END])
    shown = {types[3 * t_type[x] + 1] for x in range(NPORT)}
    rest = [g for g in range(OBJ_POINTER_COUNT) if all(g not in gs for gs in toys) and g not in boat]
    # (No other graphic is a toy's.)
    assert not {pointers[g] for g in rest} & toy_ptrs
    order = [g for g in rest if g in shown]
    port_gfx = len(order)
    order += [g for g in rest if g not in shown]
    assert len(order) + len(toy_ptrs) == len(set(pointers))
    renumber = {g: i for i, g in enumerate(order)}
    # Packed in that order: the offsets go up with the numbers.
    blob, where = pack_in_order(m, [pointers[g] for g in order])
    for p in {pointers[g] for g in order}:
        assert unpack(blob, where[p]) == columns(m, p), hex(p)
    offs = [where[pointers[g]] for g in order]
    assert offs == sorted(offs) and len(set(offs)) == len(offs)
    # thing_load's five tests reach five page boundaries past objgfx's
    # start, wherever objgfx is.
    assert (255 + offs[-1]) // 256 <= 5
    open(f"{args.out}/objgfx.bin", "wb").write(blob[:offs[port_gfx]])
    open(f"{args.out}/fixgfx.bin", "wb").write(blob[offs[port_gfx]:])
    # The toys' blocks (the docstring), each from a multiple of 4 bytes
    # (the streaming edition's records' unit: tools/mkrecords.py).
    toy_blob, toy_at = b"", []
    for e, gs in enumerate(toys):
        packed, at = pack_in_order(m, [pointers[g] for g in gs])
        block = bytes(TOY_TYPES + at[pointers[g]] for g in gs) + packed
        assert TOY_TYPES + max(at.values()) < 256
        for t, g in enumerate(gs):
            assert unpack(block, block[t]) == columns(m, pointers[g]), (e, t)
        toy_at.append(len(toy_blob))
        toy_blob += block + bytes(-len(block) % 4)
    open(f"{args.out}/toys.bin", "wb").write(toy_blob)
    # The types some thing has, renumbered (the docstring), as three lists
    # (ink, kind, graphic): a type indexes each, the graphics' only from
    # type 9 (the toy's are its block's).
    number = type_numbers(t_type)
    old = sorted(number, key=number.get)
    assert sorted({number[t_type[x]] for x in range(NPORT)}) == list(range(PORT_TYPES))
    ink, kind = (bytes(types[3 * t + k] for t in old) for k in (0, 2))
    # The tape's toy (the boat) is egg 3's, which every egg's replaces.
    assert [types[3 * t + 1] for t in old[:TOY_TYPES]] == tape_boat
    gfx = [None] * TOY_TYPES + [renumber[types[3 * t + 1]] for t in old[TOY_TYPES:]]
    assert all(g < port_gfx for g in gfx[TOY_TYPES:PORT_TYPES])
    hexes = lambda b: ", ".join(f"&{x:02X}" for x in b)
    lines = [
        "\\ Generated by tools/mkobjects.py from the original: do not edit.",
        "",
        "\\ The object graphics (&8A98, renumbered: tools/mkobjects.py): a type's",
        "\\ graphic indexes these. Each one's header's offset in objgfx, which go",
        "\\ up with the graphics' numbers (fixgfx's, from PORT_GFX, follow",
        "\\ objgfx's: the ones only fixed things show, which the streaming",
        "\\ edition keeps in its rooms' records instead); their low bytes; and",
        "\\ how many start below each of the next five pages (objects.6502's",
        "\\ thing_load counts the ones at or below a graphic for its high byte).",
        f"PORT_GFX = {port_gfx}",
        "OBJ_OFFS = {",
    ]
    for k in range(0, len(offs), 8):
        lines.append("    " + ", ".join(f"&{o:04X}" for o in offs[k:k + 8]) + ("," if k + 8 < len(offs) else ""))
    lines += [
        "}",
        "IF DEFINED(STREAM)",
        "    OBJ_KEPT = OBJ_OFFS[0..PORT_GFX - 1]",
        "ELSE",
        "    OBJ_KEPT = OBJ_OFFS",
        "ENDIF",
        ".object_lo",
        "    EQUB LO(objgfx + OBJ_KEPT)",
        "OBJ_PAGES = {" + ", ".join(f"SUM(objgfx + OBJ_KEPT < (HI(objgfx) + {i}) * 256)" for i in range(1, 6)) + "}",
        "    ASSERT HI(objgfx + OBJ_KEPT[LEN(OBJ_KEPT) - 1]) <= HI(objgfx) + 5",
        "",
        "\\ Where each toy's block starts in toys.bin (tools/mkobjects.py), by egg",
        "\\ AND 3, and where the last ends (objects.6502's toy_load).",
        "TOY_AT = {" + ", ".join(str(a) for a in toy_at + [len(toy_blob)]) + "}",
    ]
    lines += [
        "",
        "\\ The types (renumbered: tools/mkobjects.py): how many, the portable",
        "\\ things' first (PORT_TYPES of them); their inks, kinds, and graphics",
        "\\ from type TOY_TYPES (the toy's are its block's); and the portable",
        "\\ things' from &24, the bone, the girder, the ladder, the toy and the",
        "\\ egg (thing_load works out the others').",
        f"NTYPES = {len(old)}",
        f"PORT_TYPES = {PORT_TYPES}",
        f"TOY_TYPES = {TOY_TYPES}",
        "TY_INK = {" + hexes(ink) + "}",
        "TY_KIND = {" + hexes(kind) + "}",
        "TY_GFX = {" + ", ".join(str(g) for g in gfx[TOY_TYPES:]) + "}",
        ".port_types",
        "    EQUB " + ", ".join(str(number[t_type[x]]) for x in range(0x24, NPORT)),
    ]
    open(f"{args.out}/objects.6502", "w").write("\n".join(lines) + "\n")
    print("things: 1024, types:", 3 * len(old) - TOY_TYPES, "visits:", VISITS_END - VISITS,
          "graphics:", len(blob), f"(the original's {OBJGFX_END - OBJGFX}; only fixed things', {len(blob) - offs[port_gfx]});",
          "toys:", len(toy_blob), [b - a for a, b in zip(toy_at, toy_at[1:] + [len(toy_blob)])])


if __name__ == "__main__":
    main()
