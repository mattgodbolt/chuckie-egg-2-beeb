#!/usr/bin/env python3
"""Per-room disc records for a streaming edition: what each room would load
on entry, and what that costs on disc and in RAM.

A record: the packed room (decision 21's stream), the room's sprite frames
(decision 26's packing, mirror twins kept together), a pointer list (frame
index + offset, 3 bytes a frame), the room's monster-table entries (index,
row, column, type: 4 bytes each) and its palette and bands (4 + 3 a split).

Run from the repository root: .venv/bin/python <this>.
"""
import math
import re
import sys

sys.path.insert(0, "tools")
here = __file__.rsplit("/", 1)[0]
sys.argv = [sys.argv[0]]
import io, contextlib  # noqa: E401,E402
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(f"{here}/roomsprites.py").read().split("allf = set(range(152))")[0])

src = open("src/data/packed.6502").read()
lens = [int(x) for x in re.findall(r"\d+", src.split(".packed_lengths")[1].split("ROOM_BUFFER_SIZE")[0])]
assert len(lens) == 120 and sum(lens) == 6845, (len(lens), sum(lens))
bands = open("src/data/bands.6502").read()
splits = {}
for line in bands.splitlines():
    m_ = re.match(r"\s*EQUB\s+(\d+),", line)
    if m_:
        r = int(m_.group(1))
        splits[r] = splits.get(r, 0) + 1

recs = {}
for r in range(1, 121):
    s = room_frames(r)
    nmon = sum(1 for e in range(256) if mon[e] & 0x7F == r)
    size = lens[r - 1] + cost(s) + 3 * len(s) + 4 * nmon + 4 + 3 * splits.get(r, 0)
    recs[r] = (size, lens[r - 1], cost(s), len(s), nmon)

sizes = sorted(((v[0], r) for r, v in recs.items()), reverse=True)
print("Biggest records: bytes (room, sprites, frames, monsters)")
for sz, r in sizes[:8]:
    v = recs[r]
    print(f"  room {r:3d}: {sz:5d} = room {v[1]} + sprites {v[2]} ({v[3]} frames) + ...; {v[4]} monster entries")
tot = sum(v[0] for v in recs.values())
secs = sum(math.ceil(v[0] / 256) for v in recs.values())
print(f"total {tot} bytes; {secs} sectors if each record starts a sector ({secs / 10:.0f} tracks)")
dist = {}
for v in recs.values():
    n = math.ceil(v[0] / 256)
    dist[n] = dist.get(n, 0) + 1
print("sectors a record: " + ", ".join(f"{k}: {dist[k]} rooms" for k in sorted(dist)))
print(f"monster entries in rooms: max {max(v[4] for v in recs.values())}")
print(f"split-room counts: {len(splits)} rooms with splits, {sum(splits.values())} splits")

# The rooms' adjacency, for laying records out so that a room change seeks
# little: in room order, rooms r and r+1 are neighbours; r and r+10 are a
# column apart.
order = list(range(1, 121))
pos, s = {}, 0
for r in order:
    pos[r] = s
    s += math.ceil(recs[r][0] / 256)
steps = []
for r in range(1, 121):
    for n in neighbours(r):
        if n > r:
            steps.append(abs(pos[n] // 10 - pos[r] // 10))
print(f"room-order layout: tracks between neighbouring rooms: max {max(steps)}, "
      f"mean {sum(steps) / len(steps):.1f}; same track {steps.count(0)} of {len(steps)}")

# A prototype of the layout: each room's frames packed as a set and checked
# to unpack to the original's frames; records sector-aligned in room order,
# each room's first sector and sector count in records.idx (3 bytes a room)
# for the timing probe (discprobe5.mjs).
from mkgfx import unpack  # noqa: E402
total, index = 0, bytearray()
for r in range(1, 121):
    ptrs = sorted({frames[i] for i in room_frames(r)})
    if ptrs:
        b, where = pack(m, ptrs, plain_ptrs & set(ptrs))
        for p in ptrs:
            assert unpack(b, where[p]) == columns(m, p), (r, hex(p))
    n = math.ceil(recs[r][0] / 256)
    index += bytes([total & 0xFF, total >> 8, n])
    total += n
open(f"{here}/records.idx", "wb").write(index)
print(f"records: {total} sectors; every room's frames, packed as a set, unpack as the original's")
