#!/usr/bin/env python3
"""Split the rooms and the sprites into records: a body for each room and
the graphics groups the bodies share (docs/streaming.md).

    .venv/bin/python tools/mkrecords.py

Reads what the other generators wrote (src/data/: packed.bin and
packlens.txt from packrooms.py, roombands.txt from mkrooms.py, sprites.bin,
gfx.6502, monsters.bin and montypes.bin from mkgfx.py) and writes,
committed (the build never runs this):
    src/data/records.bin    the bodies, rooms 1-120, then the groups
    src/data/records.6502   what stays in main RAM to find them, and
                            Harry's frame pointers
    src/data/harry.bin      Harry's frames, which every room shows

A room's body:
    +0      offset of its monsters
    +1      offset of its bands
    +2      offset of its packed room
    +3      how many groups, then their numbers
    monsters: how many, then four bytes each, in the order the original
            scans its monster table (entries 1-255, then 0): the entry's
            number, row, column, type. The entry's number decides whether
            it is on (monsters.6502: the egg's limit, the dog's swap).
    bands:  two bytes a split, first row * 8 + logical 2's BBC colour, the
            map's number in band_maps; 0 ends
    packed room: the bit stream (unpack.6502)

A group is the frames of one monster graphic (every frame its types can
show: tools/stockb/roomsprites.py), or the truck's, the train's, a lift's,
or the sitting dog's:
    +0      how many frames
            then three bytes each: the frame's number in sprite_frames, its
            header's offset from the group's start
            then the frames, packed as sprites.bin has them (decision 26),
            a mirror image's stub re-pointed at its twin in the group
Entering a room points sprite_frames at its groups' frames (rooms.6502).
"""
import re
import sys
from collections import defaultdict

DATA = "src/data"
MIRROR = 0x80
STATIC, NEG, RESPAWN, VERT, FAST = 0x01, 0x08, 0x10, 0x40, 0x80
TRUCK = range(0x7C, 0x8A)
TRAIN = range(0x47, 0x51)
LIFTS = {26: 0x96, 55: 0x96, 34: 0x97, 104: 0x97}  # pages.6502's lift_table; frame &95 + type
DOG_SITS, DINOSAUR_STOPS = 0x0C, 0x37 + 2           # monsters.6502's respawn


def read(name):
    return open(f"{DATA}/{name}", "rb").read()


def frame_size(blob, o):
    """The bytes of the frame whose header is at o (mkgfx.py's format)."""
    if blob[o + 1] & MIRROR:
        return 4
    h, w = blob[o] & 7, blob[o + 1] & 15
    top, bottom = blob[o] >> 3, blob[o + 1] >> 4 & 7
    return 2 + (h * 8 - top - bottom) * w


def twin_of(blob, o):
    """A mirror image's twin: the header whose pixels its stub points at."""
    return ((o + (blob[o + 2] | blob[o + 3] << 8)) & 0xFFFF) - 2


def type_frames(types, t):
    """Every frame monster type t can show (monsters.6502's choose_frame):
    one if static; base + 0-3 if it moves vertically or is special; else
    right base + 0-3 and left + 4-7 (fast: + 0-1 and + 2-3), and only its
    starting direction's if it respawns rather than turning."""
    ink, base, flags, speed = types[4 * t:4 * t + 4]
    if flags & STATIC:
        return {base}
    if flags & VERT or speed & 0x80:
        return {base + i for i in range(4)}
    n = 2 if flags & FAST else 4
    dirs = [1 if flags & NEG else 0] if flags & RESPAWN else [0, 1]
    return {base + d * n + i for d in dirs for i in range(n)}


def main():
    packed = read("packed.bin")
    lens = [int(x) for x in open(f"{DATA}/packlens.txt").read().split()]
    assert len(lens) == 120 and sum(lens) == len(packed)
    bands = defaultdict(list)
    for line in open(f"{DATA}/roombands.txt").read().split("\n"):
        if line:
            r, row, colour, cmap = map(int, line.split())
            bands[r].append((row * 8 + colour, cmap))
    mon, types, sprites = read("monsters.bin"), read("montypes.bin"), read("sprites.bin")
    gfx = open(f"{DATA}/gfx.6502").read()
    harry_offs = [int(x, 16) for x in re.findall(r"EQUW sprites \+ &([0-9A-F]+)", gfx.split(".sprite_frames")[0])]
    frame_offs = [int(x, 16) for x in re.findall(r"EQUW sprites \+ &([0-9A-F]+)", gfx.split(".sprite_frames")[1])]
    assert len(harry_offs) == 12 and len(frame_offs) == 152
    # Harry's frames come first in sprites.bin, before every other frame.
    harry_end = max(o + frame_size(sprites, o) for o in harry_offs)
    assert harry_end <= min(frame_offs)

    # The groups, by graphic.
    groups = defaultdict(set)
    for t in range(len(types) // 4):
        groups[types[4 * t + 1]] |= type_frames(types, t)
    groups[DOG_SITS] |= {DOG_SITS}
    groups[0x37] |= {DINOSAUR_STOPS}
    groups["truck"] = set(TRUCK)
    groups["train"] = set(TRAIN)
    groups["bar"] = {0x96}
    groups["platform"] = {0x97}
    names = sorted(groups, key=lambda g: (isinstance(g, str), str(g) if isinstance(g, str) else g))
    number = {g: i for i, g in enumerate(names)}

    # The bodies: entries in the original's scan order, 1-255 then 0.
    entries = defaultdict(list)
    for e in list(range(1, 256)) + [0]:
        r = mon[e] & 0x7F
        if 1 <= r <= 120:
            entries[r].append(e)
    bodies, room_groups = [], {}
    start = 0
    for r in range(1, 121):
        gs = {types[4 * mon[0x300 + e] + 1] for e in entries[r]}
        if r == 2:
            gs.add(DOG_SITS)
        if r in (1, 111):
            gs.add("truck")
        if 71 <= r <= 80:
            gs.add("train")
        if r in LIFTS:
            gs.add("bar" if LIFTS[r] == 0x96 else "platform")
        room_groups[r] = sorted(number[g] for g in gs)
        assert len(entries[r]) <= 4
        head = bytes([len(room_groups[r])] + room_groups[r])
        mons = bytes([len(entries[r])] + [b for e in entries[r] for b in (e, mon[0x100 + e], mon[0x200 + e], mon[0x300 + e])])
        bnds = bytes([b for pair in bands[r] for b in pair] + [0])
        stream = packed[start:start + lens[r - 1]]
        start += lens[r - 1]
        off_mon = 3 + len(head)
        off_bands = off_mon + len(mons)
        off_stream = off_bands + len(bnds)
        body = bytes([off_mon, off_bands, off_stream]) + head + mons + bnds + stream
        assert len(body) < 256
        bodies.append(body)

    # The groups' frames, each frame once (some are pointed at twice), in
    # sprites.bin's order, a mirror's twin brought along if the group lacks
    # it.
    group_blobs = []
    for g in names:
        idx = sorted(groups[g])
        offs = sorted({frame_offs[i] for i in idx})
        for o in list(offs):
            if sprites[o + 1] & MIRROR and twin_of(sprites, o) not in offs:
                offs.append(twin_of(sprites, o))
        offs.sort()
        table = 1 + 3 * len(idx)
        where, pixels = {}, bytearray()
        for o in offs:
            where[o] = table + len(pixels)
            pixels += sprites[o:o + frame_size(sprites, o)]
        for o in offs:
            if sprites[o + 1] & MIRROR:
                p = where[o] - table
                rel = (where[twin_of(sprites, o)] + 2 - where[o]) & 0xFFFF
                pixels[p + 2:p + 4] = rel.to_bytes(2, "little")
        blob = bytes([len(idx)]) + b"".join(bytes([i, where[frame_offs[i]] & 0xFF, where[frame_offs[i]] >> 8]) for i in idx) + pixels
        group_blobs.append(blob)

    records = b"".join(bodies)
    group_at = []
    for blob in group_blobs:
        group_at.append(len(records))
        records += blob

    # Check: every room's frames, installed from its groups, are the frames
    # sprites.bin has at the original's pointers.
    sys.path.insert(0, "tools")
    from mkgfx import unpack  # noqa: E402
    for r in range(1, 121):
        ptr = {}
        for g in room_groups[r]:
            base = group_at[g]
            for k in range(records[base]):
                i, lo, hi = records[base + 1 + 3 * k:base + 4 + 3 * k]
                ptr[i] = base + (lo | hi << 8)
        need = set().union(*(groups[names[g]] for g in room_groups[r])) if room_groups[r] else set()
        assert set(ptr) == need, r
        for i, p in ptr.items():
            assert unpack(records, p) == unpack(sprites, frame_offs[i]), (r, i)

    with open(f"{DATA}/records.bin", "wb") as f:
        f.write(records)
    with open(f"{DATA}/harry.bin", "wb") as f:
        f.write(sprites[:harry_end])
    label = lambda g: f"&{g:02X}" if isinstance(g, int) else g
    lines = [
        "\\ Generated by tools/mkrecords.py: do not edit.",
        "",
        "\\ Harry's frames (&89FF), by facing + xf: 0-3 right, 4-7 left (shifted",
        "\\ 0/2/4/6 pixels, also the walk cycle), 8-11 climbing. Each points at",
        "\\ the frame's header (height in cells, width in bytes).",
        ".harry_frames",
    ] + [f"    EQUW harry_gfx + &{o:04X}" for o in harry_offs] + [
        "",
        "\\ Each room's body's length: room r's follows rooms 1 to r - 1's from",
        "\\ records (rooms.6502 adds them up).",
        ".body_len",
    ] + ["    EQUB " + ", ".join(f"{len(b):3d}" for b in bodies[i:i + 12]) for i in range(0, 120, 12)] + [
        "",
        f"GROUPS = {len(names)}",
        "\\ Each graphics group's offset from records (its monster graphic's",
        "\\ base frame, or the machine).",
        ".group_lo",
    ] + [f"    EQUB LO(&{a:04X})   \\ {i:2d}: {label(g)}" for i, (g, a) in enumerate(zip(names, group_at))] + [
        ".group_hi",
    ] + [f"    EQUB HI(&{a:04X})" for a in group_at] + [
        f"RECORDS_LEN = {len(records)}",
    ]
    with open(f"{DATA}/records.6502", "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"records.bin: {len(records)} bytes: bodies {sum(map(len, bodies))} (largest {max(map(len, bodies))}), "
          f"{len(names)} groups {len(records) - sum(map(len, bodies))} (largest {max(map(len, group_blobs))}); "
          f"harry.bin {harry_end}")


if __name__ == "__main__":
    main()
