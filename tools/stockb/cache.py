#!/usr/bin/env python3
"""Cache sizing for a streaming stock-B edition. Run from the repo root:
.venv/bin/python <this>. Uses roomsprites.py (beside it) and graph.py."""
import io, contextlib, math, re, sys
from collections import defaultdict, Counter
here = __file__.rsplit("/", 1)[0]
sys.path.insert(0, "tools"); sys.path.insert(0, here)
sys.argv = [sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(f"{here}/roomsprites.py").read().split("allf = set(range(152))")[0])
from graph import G

src = open("src/data/packed.6502").read()
lens = [int(x) for x in re.findall(r"\d+", src.split(".packed_lengths")[1].split("ROOM_BUFFER_SIZE")[0])]
splits = Counter()
for line in open("src/data/bands.6502").read().splitlines():
    m_ = re.match(r"\s*EQUB\s+(\d+),", line)
    if m_: splits[int(m_.group(1))] += 1

def entries(r): return [e for e in range(256) if mon[e] & 0x7F == r]

# Graphic groups: a monster graphic (all frames of every type with that base),
# the dog's sitting frame, and the machines.
gframes = defaultdict(set)
for t in range(52):
    gframes[types[4 * t + 1]] |= type_frames(t, 0)
gframes[0x0C] |= {0x0C}
gframes[0x37] |= {0x37 + 2}
gframes["truck"] = set(range(0x7C, 0x8A)); gframes["train"] = set(range(0x47, 0x51))
gframes["bar"] = {0x96}; gframes["plat"] = {0x97}
gcost = {g: cost(f) + 1 + 3 * len(f) for g, f in gframes.items()}   # pixels + count + (index, offset) a frame

def groups(r):
    s = {types[4 * mon[0x300 + e] + 1] for e in entries(r)}
    if r == 2: s.add(0x0C)
    if r in (1, 111): s.add("truck")
    if 71 <= r <= 80: s.add("train")
    if r in (26, 55): s.add("bar")
    if r in (34, 104): s.add("plat")
    return s

# body: packed room, monster entries (4), palette 4 + 3 a split, a group list (1 a group)
body = {r: lens[r - 1] + 4 * len(entries(r)) + 4 + 3 * splits[r] for r in range(1, 121)}
rec = {r: body[r] + cost(room_frames(r)) + 3 * len(room_frames(r)) for r in range(1, 121)}
sec = lambda b: math.ceil(b / 256)
N = {r: set(G[r].values()) for r in G}
P = print

P("== records (monolithic, as records.py) ==")
P(f"total {sum(rec.values())}, max {max(rec.values())} (room {max(rec, key=rec.get)}), mean {sum(rec.values())/120:.0f}")
d = Counter(sec(v) for v in rec.values()); P("sectors a record:", dict(sorted(d.items())), "total", sum(sec(v) for v in rec.values()))
P("bodies only (room + entries + palette/bands + group refs):")
bb = {r: body[r] + len(groups(r)) for r in body}
P(f"  total {sum(bb.values())}, max {max(bb.values())} (room {max(bb, key=bb.get)}), mean {sum(bb.values())/120:.0f}")
P("groups:", len(gcost), "total", sum(gcost.values()), "max", max(gcost.values()))
use = Counter(g for r in range(1, 121) for g in groups(r))
P("group (bytes, rooms using):", ", ".join(f"{g if isinstance(g,str) else '&%02X'%g}:{gcost[g]}/{use[g]}" for g in sorted(gcost, key=lambda g: -gcost[g])))

P("\n== graph ==")
deg = [len(N[r]) for r in N]
P(f"max degree {max(deg)}, mean {sum(deg)/120:.2f}, hist {dict(sorted(Counter(deg).items()))}")

def worst(f, label):
    vals = {r: f(r) for r in range(1, 121)}
    r = max(vals, key=vals.get)
    top = sorted(vals.items(), key=lambda kv: -kv[1])[:5]
    P(f"{label}: max {vals[r]} (room {r}); mean {sum(vals.values())/120:.0f}; top {top}")
    return vals[r]

P("\n== (a) current + all neighbours ==")
worst(lambda r: rec[r] + sum(rec[n] for n in N[r]), "monolithic bytes")
worst(lambda r: sec(rec[r]) + sum(sec(rec[n]) for n in N[r]), "monolithic sectors (256-byte slots)")
worst(lambda r: sum(math.ceil(rec[x] / 128) for x in N[r] | {r}) * 128, "128-byte granules, bytes")
worst(lambda r: 1024 * (1 + len(N[r])), "1K slots, bytes")
P("== (b) current + previous ==")
pairs = [(rec[r] + rec[n], r, n) for r in N for n in N[r]]
P("max pair bytes", max(pairs)[:3], "sectors", max(sec(rec[r]) + sec(rec[n]) for r in N for n in N[r]))
P("== current + neighbours + checkpoint pinned (worst case: any other room) ==")
worst(lambda r: rec[r] + sum(rec[n] for n in N[r]) + max(rec[x] for x in range(1, 121) if x not in N[r] | {r}), "bytes")

P("\n== (d) bodies and graphic groups cached apart (shared) ==")
def split_cost(rs):
    return sum(bb[x] for x in rs) + sum(gcost[g] for g in set().union(*(groups(x) for x in rs)))
worst(lambda r: split_cost(N[r] | {r}), "current + neighbours, split")
worst(lambda r: split_cost({r}), "one room, split (body + its groups whole)")
P("sharing win on (a): see above vs monolithic")

P("\n== resident groups: greedy, to shrink the worst current+neighbours ==")
res = set()
def split_cost_res(rs):
    return sum(bb[x] for x in rs) + sum(gcost[g] for g in set().union(*(groups(x) for x in rs)) - res)
base_w = max(split_cost_res(N[r] | {r}) for r in N)
for step in range(8):
    best = None
    for g in gcost:
        if g in res: continue
        res.add(g)
        w = max(split_cost_res(N[r] | {r}) for r in N)
        res.discard(g)
        gain = base_w - w
        if gain > 0 and (best is None or (gain - gcost[g]) > best[0]):
            best = (gain - gcost[g], g, w, gain)
    if not best: break
    res.add(best[1]); base_w = best[2]
    P(f"  + {best[1] if isinstance(best[1],str) else '&%02X'%best[1]} ({gcost[best[1]]} resident): worst -> {best[2]} (gain {best[3]}, net {best[0]})")
P("frequency view: groups used by >= 10 rooms:", [(g if isinstance(g,str) else '&%02X'%g, gcost[g], use[g]) for g in gcost if use[g] >= 10])

P("\n== neighbour lists ==")
for r in range(1, 121):
    P(f"  {r:3d}: " + " ".join(f"{k}{v}" for k, v in sorted(G[r].items())) + f"   rec {rec[r]} ({sec(rec[r])}s) body {bb[r]} groups {sorted(str(g) if isinstance(g,str) else '&%02X'%g for g in groups(r))}")

P("\n== fit: rooms where current + all neighbours fit a budget (bytes, no fragmentation) ==")
full = {r: rec[r] + sum(rec[n] for n in N[r]) for r in N}
spl = {r: split_cost(N[r] | {r}) for r in N}
for B in (1582, 1940, 2048, 2277, 2304, 2560):
    P(f"  {B}: monolithic {sum(v <= B for v in full.values())}/120, split {sum(v <= B for v in spl.values())}/120; over: {sorted(r for r in N if full[r] > B)}")
P("current + k largest neighbours (worst):")
for k in (1, 2, 3):
    w = max((rec[r] + sum(sorted((rec[n] for n in N[r]), reverse=True)[:k]), r) for r in N)
    P(f"  k={k}: {w}")

P("\n== ZX02 per record (sprites + room + rest), for a compressed cache ==")
import zx02
from mkgfx import pack as _pack
zrec = {}
for r in range(1, 121):
    ptrs = sorted({frames[i] for i in room_frames(r)})
    blob = _pack(m, ptrs, plain_ptrs & set(ptrs))[0] if ptrs else b""
    zs = len(zx02.compress(bytes(blob))) if blob else 0
    zrec[r] = rec[r] - len(blob) + zs   # the room stream is at entropy already: kept raw
P(f"total {sum(zrec.values())} (raw {sum(rec.values())}), max {max(zrec.values())} (room {max(zrec, key=zrec.get)})")
P("sectors:", dict(sorted(Counter(sec(v) for v in zrec.values()).items())), "total", sum(sec(v) for v in zrec.values()))
zn = {r: sum(zrec[x] for x in N[r] | {r}) for r in N}
zn2 = {r: sum(zrec[x] for x in N[r]) for r in N}
P(f"compressed current + neighbours: max {max(zn.values())} (room {max(zn, key=zn.get)}), mean {sum(zn.values())/120:.0f}")
P(f"1K working buffer (current, unpacked) + compressed neighbours: max {1024 + max(zn2.values())}")
for B in (1582, 1940, 2277):
    P(f"  {B}: compressed cur+nbrs fit {sum(v <= B for v in zn.values())}/120")

P("\n== split design details ==")
gs = {g: sec(c) for g, c in gcost.items()}
P(f"group items on disc: {len(gs)}, sectors {sum(gs.values())} (hist {dict(sorted(Counter(gs.values()).items()))}); bodies: 120 sectors, one each (max {max(bb.values())})")
over = {B: sorted((spl[r], r) for r in N if spl[r] > B) for B in (1582, 1940, 2277)}
for B, o in over.items(): P(f"  split over {B}: {o}")
# allocation slack: groups read straight into the arena round up to a sector.
P("rounded up (sector granules) split cur+nbrs:", max(sum(256 * sec(bb[x]) for x in N[r] | {r}) + sum(256 * gs[g] for g in set().union(*(groups(x) for x in N[r] | {r}))) for r in N))
P("exact split, plus one sector of read slack:", max(spl.values()) + 255)
# What each room change has to fetch (new items) with the all-neighbours policy
newb = []
for r in N:
    for n in N[r]:
        have = N[r] | {r}
        need = N[n] | {n}
        hg = set().union(*(groups(x) for x in have))
        nb_ = [x for x in need - have]
        ng = set().union(*(groups(x) for x in need)) - hg
        newb.append((sum(bb[x] for x in nb_) + sum(gcost[g] for g in ng), len(nb_), len(ng), sum(1 for _ in nb_) + sum(gs[g] for g in ng), r, n))
newb.sort(reverse=True)
P(f"per room change, items to fetch (bodies, groups): worst bytes {newb[0][:3]} {newb[0][4:]}, worst sectors {max(x[3] for x in newb)}, mean bytes {sum(x[0] for x in newb)/len(newb):.0f}, mean sectors {sum(x[3] for x in newb)/len(newb):.1f}")
P(f"   distribution of new bodies per change: {dict(sorted(Counter(x[1] for x in newb).items()))}; new groups: {dict(sorted(Counter(x[2] for x in newb).items()))}")
