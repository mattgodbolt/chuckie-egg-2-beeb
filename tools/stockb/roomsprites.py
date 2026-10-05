#!/usr/bin/env python3
"""Per-room sprite sets: which of the 152 sprite frames each room can show,
and what they cost packed as decision 26 packs them (empty lines trimmed,
mirror images as stubs when the twin is in the same set).

Run from the repository root: .venv/bin/python <this>.

Frames a monster can show (monsters.6502's choose_frame, research 4.5-4.7):
- STATIC: base (dx = 0, sub = 0)
- VERT or special (speed bit 7): base + 0..3
- horizontal: right base + 0..3, left base + 4..7 (FAST: + 0,1 and + 2,3);
  a RESPAWN monster never turns, so only its starting direction's.
- room 2's dog sits (&0C); room 120's dinosaur stops at base + 2.
Machines: truck strips &7C-&89 in rooms 1 and 111; train strips &47-&50 in
rooms 71-80; lift bar &96 (rooms 26, 55), platform &97 (34, 104).
"""
import sys
from collections import defaultdict

sys.path.insert(0, "tools")
from mkgfx import pack, columns, SPRITE_FRAMES, HARRY_FRAMES, STRIPS  # noqa: E402
from zx import Spectrum  # noqa: E402

m = Spectrum("build/zx_start.z80").mem
word = lambda a: m[a] | m[a + 1] << 8
harry = [word(HARRY_FRAMES + 2 * i) for i in range(12)]
frames = [word(SPRITE_FRAMES + 2 * i) for i in range(152)]
mon = open("src/data/monsters.bin", "rb").read()
types = open("src/data/montypes.bin", "rb").read()

STATIC, NEG, RESPAWN, FREE, VERT, FAST = 1, 8, 16, 32, 64, 128


def type_frames(t, room):
    ink, base, flags, speed = types[4 * t:4 * t + 4]
    if flags & STATIC:
        out = {base}
    elif flags & VERT or speed & 0x80:
        out = {base + i for i in range(4)}
    else:
        n = 2 if flags & FAST else 4
        dirs = [1 if flags & NEG else 0] if flags & RESPAWN else [0, 1]
        out = {base + d * n + i for d in dirs for i in range(n)}
    if room == 2:
        out |= {0x0C}
    if room == 120:
        out |= {base + 2}
    return out


def room_frames(room, eggs=5):
    k = min(130 + 25 * eggs, 255)
    s = set()
    for e in range(256):
        r = mon[e] & 0x7F
        if r != room:
            continue
        if e > k:
            continue
        s |= type_frames(mon[0x300 + e], room)
    if room in (1, 111):
        s |= set(range(0x7C, 0x8A))
    if 71 <= room <= 80:
        s |= set(range(0x47, 0x51))
    if room in (26, 55):
        s.add(0x96)
    if room in (34, 104):
        s.add(0x97)
    return s


plain_ptrs = {frames[i] for i in STRIPS}


def cost(idx):
    """Packed bytes for this set of frame indices (decision 26's format)."""
    ptrs = {frames[i] for i in idx}
    if not ptrs:
        return 0
    blob, _ = pack(m, sorted(ptrs), plain_ptrs & ptrs)
    return len(blob)


def raw(idx):
    ptrs = {frames[i] for i in idx}
    return sum(2 + 8 * m[p] * m[p + 1] for p in ptrs)


def neighbours(r):
    out = set()
    for d in (1, -1, 10, -10):
        n = r + d
        if r == 80 and d == 1:
            n = 71
        if r == 71 and d == -1:
            n = 80
        if 1 <= n <= 120:
            out.add(n)
    return out


allf = set(range(152))
print(f"all 152 frames packed: {cost(allf)} (raw {raw(allf)}); Harry {len(pack(m, harry, set(harry))[0])}")
rows = []
for r in range(1, 121):
    s = room_frames(r)
    rows.append((cost(s), r, len(s), raw(s), cost(room_frames(r, 1))))
rows.sort(reverse=True)
print("\nBiggest per-room sets (all eggs): packed, room, frames, raw, egg-1 packed")
for c, r, n, rw, c1 in rows[:15]:
    print(f"  room {r:3d}: {c:5d} bytes packed, {n:2d} frames, raw {rw:5d}; egg 1: {c1}")
costs = [c for c, *_ in rows]
print(f"\nmean {sum(costs)/120:.0f}, median {sorted(costs)[60]}, rooms with none {costs.count(0)}")

# Without the machines (if the strips stay resident: truck 580, train 260).
mach = set(range(0x7C, 0x8A)) | set(range(0x47, 0x51))
mc = sorted(((cost(room_frames(r) - mach), r) for r in range(1, 121)), reverse=True)
print(f"monsters and lifts only: biggest {mc[:6]}; strips packed {cost(mach)}")

# Per type group: what a cache keyed by monster graphic would hold.
groups = defaultdict(set)
for t in range(52):
    groups[types[4 * t + 1]] |= type_frames(t, 0)

# A room plus its neighbours (for prefetching, or a cache of the last few).
nb = sorted(((cost(set().union(*(room_frames(x) for x in neighbours(r) | {r}))), r)
             for r in range(1, 121)), reverse=True)
print(f"room + neighbours: biggest {nb[:6]}")

# Which rooms' sets are biggest, with the dinosaur: what if room 120 is special?
print("\nFrames by size (packed alone), biggest 12:")
sizes = sorted(((cost({i}), i) for i in range(152)), reverse=True)
print("  " + ", ".join(f"&{i:02X}:{c}" for c, i in sizes[:12]))

# Shift redundancy: is a frame a pure 2/4/6-pixel shift of another (1bpp)?
def rows_of(p):
    h, w = m[p], m[p + 1]
    return h, w, [int.from_bytes(bytes(m[p + 2 + y * w: p + 2 + y * w + w]), "big") for y in range(8 * h)]


uniq = sorted(set(frames))
shifted = []
for p in uniq:
    h, w, rp = rows_of(p)
    if not any(rp):
        continue
    found = None
    for q in uniq:
        if q == p or found:
            continue
        h2, w2, rq = rows_of(q)
        if h2 != h or w2 > w:
            continue
        for s in (2, 4, 6):
            al = [b << (8 * (w - w2)) for b in rq]
            if all((b >> s) << s == b and (b >> s) == a for a, b in zip(rp, al)):
                found = (p, q, s)
                break
    if found:
        shifted.append(found)
print(f"\nframes that are a pure 2/4/6-pixel shift of another: {len(shifted)} of {len(uniq)}")
sv = sum(2 + 8 * m[p] * m[p + 1] for p, q, s in shifted)
print(f"  their raw bytes: {sv}")
idx = {p: [i for i, f in enumerate(frames) if f == p] for p in uniq}
print("  " + ", ".join(f"&{idx[p][0]:02X}<-&{idx[q][0]:02X}>>{s}" for p, q, s in shifted))

# Per monster-graphic group, compressed apart (what a per-room unpacker would
# need: random access by group).
import zx02
blob_all = 0
zsum = 0
gl = []
for base, idxs in sorted(groups.items()):
    ptrs = sorted({frames[i] for i in idxs})
    b, _ = pack(m, ptrs, plain_ptrs & set(ptrs))
    z = zx02.compress(b)
    blob_all += len(b)
    zsum += len(z)
    gl.append((base, len(b), len(z)))
mb = sorted({frames[i] for i in mach})
b, _ = pack(m, mb, plain_ptrs & set(mb))
z = zx02.compress(b)
print(f"\nmonster groups packed {blob_all}, zx02 apart {zsum}; strips {len(b)} -> {len(z)}")
print("  " + ", ".join(f"&{a:02X}:{x}->{y}" for a, x, y in gl))
