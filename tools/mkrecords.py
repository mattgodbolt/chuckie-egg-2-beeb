#!/usr/bin/env python3
"""Split the rooms and the sprites into records: a body for each room and
the graphics groups the bodies share (docs/streaming.md), and for the
streaming edition each room's record, its body and its groups together.

    .venv/bin/python tools/mkrecords.py

Reads the original's rooms as its own code draws them (build/rooms, from
tools/zxrooms.py: make rooms) and what the other generators wrote
(src/data/: packed.bin and
packlens.txt from packrooms.py, roombands.txt from mkrooms.py, sprites.bin,
gfx.6502, monsters.bin and montypes.bin from mkgfx.py) and writes,
committed (the build never runs this):
    src/data/records.bin    the bodies, rooms 1-120, then the groups (the
                            sideways edition's bank)
    src/data/roomrecs.bin   the streaming edition's: for each room its
                            body, then its groups, each from a multiple
                            of 4 bytes, the room's record from a sector
                            (256 bytes), so a room is one run of sectors
                            read straight into place (disc.6502). No
                            record crosses a track (ten sectors, the file
                            starting one: tools/ssdmerge.py): one that
                            wouldn't fit starts the next
    src/data/records.6502   what stays in main RAM to find them, and
                            Harry's frame pointers
    src/data/harry.bin      Harry's frames, which every room shows
    src/data/thingsres.bin  the things' rooms (256), then the portable
                            things' rows, columns and types (41 each)

A room's body, its parts one after another (rooms.6502's room_load finds
where each starts):
    exits and visit bonus: bits 0-3 which edges Harry can cross, left,
            right, up, down (from the original's cell types, build/rooms:
            below), for the streaming edition's reading ahead (disc.6502);
            bits 4-7 the room's first-visit bonus (visits.bin, status.6502)
    groups: how many, then for each its number (records.bin), or where
            it starts in the room's record, in fours (roomrecs.bin)
    monsters: how many, then four bytes each, in the order the original
            scans its monster table (entries 1-255, then 0): the entry's
            number, row, column, type. The entry's number decides whether
            it is on (monsters.6502: the egg's limit, the dog's swap).
    bands:  two bytes a split, first row * 8 + logical 2's BBC colour, the
            map's number in band_maps; 0 ends
    fixed things: three bytes for each thing from &29 (the machine parts
            and bonus items, which never move) whose room this is, in order:
            row, column, type. objects.6502's thing_load finds a thing's
            by its place among them; things.bin's other rows, columns and
            types (the portable things', 0-&28) stay in main RAM.
    packed room: the bit stream (unpack.6502)

A group is the frames of one monster graphic (every frame its types can
show: tools/stockb/roomsprites.py), or the truck's, the train's, a lift's,
or the sitting dog's:
    +0      how many frames
            the first frame's number (the original's &91B7 table's
            index: a group's frames are numbered consecutively)
            then two bytes each: the frame's header's offset from the
            group's start
            then the frames, packed as sprites.bin has them (decision 26),
            a mirror image's stub re-pointed at its twin in the group
Entering a room notes its groups' frames, at most FRAMES_MAX of them
from at most GROUPS_MAX groups, for sprite_frame (rooms.6502, sprite.6502).
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
NPORT = 0x29                # things 0-&28 are portable (objects.6502)
FIXED_MAX = 9               # the most fixed things in a room (rooms.6502's room_fixed)
LEN4_BIAS = 3               # room_len4 is a record's length in fours, less this
GROUPS_MAX, FRAMES_MAX = 4, 24  # the most groups, and frames, a room has (main.6502)


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


def exits(r):
    """Which edges of room r Harry could cross, from its cell types (a
    superset is safe: it only steers the reading ahead). Left or right: two
    cells free of solid (&21), one above the other, at the edge; up: a cell
    in row 2 free of &2D, or a ladder or rope (&12); down: one in row 23 with
    no floor (&21), or a ladder or rope."""
    t = open(f"build/rooms/room_{r:03d}.bin", "rb").read()[6912 + 1536:6912 + 2304]
    cell = lambda row, col: t[row * 32 + col]
    side = lambda col: any(cell(y, col) & 0x21 == 0 and cell(y + 1, col) & 0x21 == 0 for y in range(2, 23))
    up = any(cell(2, c) & 0x2D == 0 or cell(2, c) & 0x12 for c in range(32))
    down = any(cell(23, c) & 0x21 == 0 or cell(23, c) & 0x12 for c in range(32))
    return side(0) | side(31) << 1 | up << 2 | down << 3


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
    # The streaming edition's bodies have their palette and bands' colour
    # maps in place of their numbers (main RAM keeps neither table).
    hexes = lambda name, label: [int(x, 16) for x in re.findall(r"&([0-9A-F]{2})", open(f"{DATA}/{name}").read().split(label)[1])]
    palettes, band_maps = hexes("rooms.6502", ".room_palettes"), hexes("bands.6502", ".band_maps")
    things = read("things.bin")
    visits = read("visits.bin")
    assert all(v < 16 for v in visits)
    t_room, t_row, t_col, t_type = (things[k * 256:(k + 1) * 256] for k in range(4))
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
        assert len(gs) <= GROUPS_MAX
        assert sum(len(groups[g]) for g in gs) <= FRAMES_MAX
        assert len(entries[r]) <= 4
        mons = bytes([len(entries[r])] + [b for e in entries[r] for b in (e, mon[0x100 + e], mon[0x200 + e], mon[0x300 + e])])
        # The streaming edition's: the type's four bytes in place of its
        # number, so main RAM needn't keep mon_types (monsters.6502).
        mons_s = bytes([len(entries[r])] + [b for e in entries[r] for b in (e, mon[0x100 + e], mon[0x200 + e])
                                            + tuple(types[4 * mon[0x300 + e]:4 * mon[0x300 + e] + 4])])
        bnds = bytes([b for pair in bands[r] for b in pair] + [0])
        bnds_s = bytes([b for first, m in bands[r] for b in (first, *band_maps[2 * m:2 * m + 2])] + [0])
        fixed = [x for x in range(NPORT, 256) if t_room[x] & 0x7F == r]
        assert len(fixed) <= FIXED_MAX
        fixd = bytes([b for x in fixed for b in (t_row[x], t_col[x], t_type[x])])
        stream = packed[start:start + lens[r - 1]]
        palette = bytes(palettes[4 * (stream[0] >> 3):4 * (stream[0] >> 3) + 4])
        start += lens[r - 1]
        bodies.append((bytes([exits(r) | visits[r] << 4]), mons + bnds + fixd + stream, mons_s + bnds_s + fixd + palette + stream))

    # The groups' frames, each frame once (some are pointed at twice), in
    # sprites.bin's order, a mirror's twin brought along if the group lacks
    # it.
    group_blobs = []
    for g in names:
        idx = sorted(groups[g])
        # sprite_frame finds a frame by its group's first and how many.
        assert idx == list(range(idx[0], idx[0] + len(idx))), g
        offs = sorted({frame_offs[i] for i in idx})
        for o in list(offs):
            if sprites[o + 1] & MIRROR and twin_of(sprites, o) not in offs:
                offs.append(twin_of(sprites, o))
        offs.sort()
        table = 2 + 2 * len(idx)
        where, pixels = {}, bytearray()
        for o in offs:
            where[o] = table + len(pixels)
            pixels += sprites[o:o + frame_size(sprites, o)]
        for o in offs:
            if sprites[o + 1] & MIRROR:
                p = where[o] - table
                rel = (where[twin_of(sprites, o)] + 2 - where[o]) & 0xFFFF
                pixels[p + 2:p + 4] = rel.to_bytes(2, "little")
        blob = bytes([len(idx), idx[0]]) + b"".join(where[frame_offs[i]].to_bytes(2, "little") for i in idx) + pixels
        group_blobs.append(blob)

    def body(r, refs, streaming=False):
        first, rest, rest_s = bodies[r - 1]
        b = first + bytes([len(refs)] + refs) + (rest_s if streaming else rest)
        assert len(b) < 256
        return b
    body_len = [len(body(r, room_groups[r])) for r in range(1, 121)]
    records = b"".join(body(r, room_groups[r]) for r in range(1, 121))
    group_at = []
    for blob in group_blobs:
        group_at.append(len(records))
        records += blob
    pad4 = lambda b: b + bytes(-len(b) % 4)
    roomrecs, room_at, room_len = b"", [], []
    for r in range(1, 121):
        fours, at = [], (len(body(r, room_groups[r], True)) + 3) // 4
        for g in room_groups[r]:
            fours.append(at)
            at += (len(group_blobs[g]) + 3) // 4
        assert LEN4_BIAS <= at <= 255 + LEN4_BIAS   # (room_len4, below)
        rec = pad4(body(r, fours, True)) + b"".join(pad4(group_blobs[g]) for g in room_groups[r])
        sectors = (len(rec) + 255) // 256
        if len(roomrecs) // 256 % 10 + sectors > 10:
            roomrecs += bytes(-len(roomrecs) % 2560)
        room_at.append(len(roomrecs))
        room_len.append(len(rec))
        roomrecs += rec + bytes(-len(rec) % 256)

    # Check: every room's frames, installed from its groups, are the frames
    # sprites.bin has at the original's pointers.
    sys.path.insert(0, "tools")
    from mkgfx import unpack  # noqa: E402
    # (Both files, each room's group list read as room_load reads it.)
    body_at = [sum(body_len[:r - 1]) for r in range(1, 122)]
    for blob, start in ((records, body_at), (roomrecs, room_at + [len(roomrecs)])):
        for r in range(1, 121):
            b = start[r - 1]
            assert blob[b + 1] == len(room_groups[r])
            ptr = {}
            for k in range(blob[b + 1]):
                ref = blob[b + 2 + k]
                base = group_at[ref] if blob is records else b + 4 * ref
                for f in range(blob[base]):
                    lo, hi = blob[base + 2 + 2 * f:base + 4 + 2 * f]
                    ptr[blob[base + 1] + f] = base + (lo | hi << 8)
            need = set().union(*(groups[names[g]] for g in room_groups[r])) if room_groups[r] else set()
            assert set(ptr) == need, r
            for i, p in ptr.items():
                assert unpack(blob, p) == unpack(sprites, frame_offs[i]), (r, i)

    room_max = max(room_len)
    with open(f"{DATA}/records.bin", "wb") as f:
        f.write(records)
    with open(f"{DATA}/roomrecs.bin", "wb") as f:
        f.write(roomrecs)
    with open(f"{DATA}/harry.bin", "wb") as f:
        f.write(sprites[:harry_end])
    assert all(1 <= t_room[x] & 0x7F <= 120 for x in range(NPORT, 256))
    with open(f"{DATA}/thingsres.bin", "wb") as f:
        f.write(t_room + t_row[:NPORT] + t_col[:NPORT] + t_type[:NPORT])
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
        "IF NOT(DEFINED(STREAM))",
        "\\ Each room's body's length: room r's follows rooms 1 to r - 1's from",
        "\\ records (rooms.6502 adds them up).",
        ".body_len",
    ] + ["    EQUB " + ", ".join(f"{n:3d}" for n in body_len[i:i + 12]) for i in range(0, 120, 12)] + [
        "ELSE",
        "\\ Each room's record's length in roomrecs.bin, in fours, less LEN4_BIAS: room",
        "\\ r's starts at the sector after rooms 1 to r - 1's, or the next track's",
        "\\ first if it wouldn't fit in what's left of this one (disc.6502).",
        ".room_len4",
    ] + ["    EQUB " + ", ".join(f"{n // 4 - LEN4_BIAS:3d}" for n in room_len[i:i + 12]) for i in range(0, 120, 12)] + [
        "ENDIF",
        "",
        "IF NOT(DEFINED(STREAM))",
        "\\ Each graphics group's offset from records (its monster graphic's",
        "\\ base frame, or the machine).",
        ".group_lo",
    ] + [f"    EQUB LO(&{a:04X})   \\ {i:2d}: {label(g)}" for i, (g, a) in enumerate(zip(names, group_at))] + [
        ".group_hi",
    ] + [f"    EQUB HI(&{a:04X})" for a in group_at] + [
        "ENDIF",
        "\\ The most a room needs, its record (the streaming edition's cache).",
        f"ROOM_MAX = {room_max}",
        f"NPORT = &{NPORT:02X}       \\ things 0 to NPORT - 1 are portable",
        f"FIXED_MAX = {FIXED_MAX}",
        f"GROUPS_MAX = {GROUPS_MAX}",
        f"LEN4_BIAS = {LEN4_BIAS}",
        f"FRAMES_MAX = {FRAMES_MAX}",
    ]
    with open(f"{DATA}/records.6502", "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"records.bin: {len(records)} bytes: bodies {sum(body_len)} (largest {max(body_len)}), "
          f"{len(names)} groups {len(records) - sum(body_len)} (largest {max(map(len, group_blobs))}); "
          f"roomrecs.bin {len(roomrecs)} (largest {room_max}); harry.bin {harry_end}")


if __name__ == "__main__":
    main()
