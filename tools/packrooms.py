#!/usr/bin/env python3
"""Pack the room data into a bit stream a room at a time, and unpack it
again to prove the round trip.

    python3 tools/packrooms.py [--out src/data]

The packed form unpacks to the original's bytecode exactly, so the room
drawer (a transcription of the original's) is unchanged: unpack a room into
a buffer, draw from the buffer. All but the first byte, the background
attribute, of which the drawer only takes the paper: here the paper is in
bits 0-2 and the room's palette number (tools/mkrooms.py, roompal.txt) in
bits 3-7, where set_room_palette (screen.6502) reads it.

Each room is a stream of bits, most significant first:

    palette * 8 + paper     8 bits
    records, until `end`    a class code, then the class's fields

Class codes (a prefix code, commonest shortest), and fields:

    0       run      tile* attr* row+ col vert len-1+ type*
    100     capped   tile* attr* row+ col vert len-1+ ends+ type*
    101     single   attr* tile* row+ col type*
    1100    diag up      attr* row+ col len(5) type*
    1101    diag down    attr* row+ col len(5) type*
    11100   text         attr* row+ col chars(5 each) until 31
    11101   block        attr* row+ col h(5) w(5) type*
    111100  bend         which(2) attr* row+ col type*   (commands 3-6)
    111101  hopper       attr* row+ col rows(5) width(6)
    11111   end

The fields come in the bytecode's own order, so the unpacker emits each as
it decodes it.

Fields marked + are tier coded (Tiers): the values the field takes in the
whole game, commonest first, fall into three tiers, '0', '10' and '11',
each followed by a fixed number of bits indexing that tier. One code for
rows, one for the ends of capped runs, and one each for the lengths of
horizontal and vertical runs. The rest of row is near-flat: col stays 5
bits. (Rows 1352 bytes plain become 1195, run lengths 1136 become 952,
ends 232 become 125.)

col is 5 bits. One run in the whole game (room 33) says column 32
of row 11; the original's arithmetic makes that row 12 column 0, so it is
packed as that, and the round trip is checked against the room with that
one record normalised (normalise()). Fields marked * are move-to-front coded, one list
each for attribute, tile and type, kept per room: 0 = "the last one" (1
bit), 1 = '10', 2 = '110', otherwise '111' and the value's index in that
field's vocabulary: every value the field takes in the whole game, sorted,
in as few bits as hold them (attributes 38 values in 6 bits, tiles 49 in
6, types 8 in 3; the escapes were a quarter of the stream at 8 bits each).
Text characters index TEXT_CHARS.
"""
import argparse
import itertools
import os
import sys
from collections import Counter

ROOMDATA = "src/data/roomdata.bin"
DATA_START = 0xAA5C
TEXT_CHARS = " &ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def load_rooms():
    data = open(ROOMDATA, "rb").read()
    offsets = [0] + [int(x) for x in open("src/data/roomoffsets.txt").read().split()]
    rooms = {}
    for r in range(1, 121):
        p = offsets[r]
        start = p
        p += 1
        while True:
            c = data[p]
            if c == 0:
                p += 1
                break
            if c == 2:
                p += 4
                while data[p] != 0x80:
                    p += 1
                p += 1
            elif c < 0x20:
                p += {1: 7, 3: 5, 4: 5, 5: 5, 6: 5, 7: 6, 8: 6, 9: 6, 10: 6}[c]
            elif c < 0x2C:
                p += 7
            else:
                p += 6
        rooms[r] = data[start:p]
    # The first byte: the paper (the background attribute's bits 3-5) and
    # the palette number.
    pals = [int(x) for x in open("src/data/roompal.txt").read().split()]
    for r in rooms:
        assert pals[r - 1] < 32
        rooms[r] = bytes([rooms[r][0] >> 3 & 7 | pals[r - 1] << 3]) + rooms[r][1:]
    return rooms


def normalise(room):
    """The room with any column 32+ moved to the next row, as the original's
    position arithmetic does (asserting it doesn't cross a screen third,
    where the original would wrap differently)."""
    room = bytearray(room)
    p = 1
    while room[p]:
        c = room[p]
        if c == 10:
            ri, length = p + 3, 6
        elif c == 2:
            ri = p + 2
            q = p + 4
            while room[q] != 0x80:
                q += 1
            length = q + 1 - p
        else:
            ri = p + 2
            length = {1: 7, 3: 5, 4: 5, 5: 5, 6: 5, 7: 6, 8: 6, 9: 6}.get(c, 7 if c < 0x2C else 6)
        if room[ri + 1] >= 32:
            assert room[ri] & 7 != 7, "column overflow across a third"
            room[ri] += 1
            room[ri + 1] -= 32
        p += length
    return bytes(room)


class Bits:
    def __init__(self):
        self.bits = []

    def put(self, value, n):
        for i in range(n - 1, -1, -1):
            self.bits.append((value >> i) & 1)

    def code(self, s):
        self.bits += [int(b) for b in s]

    def bytes(self):
        b = self.bits + [0] * (-len(self.bits) % 8)
        return bytes(int("".join(map(str, b[i:i + 8])), 2) for i in range(0, len(b), 8))


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def get(self, n):
        v = 0
        for _ in range(n):
            v = v << 1 | (self.data[self.pos >> 3] >> (7 - (self.pos & 7))) & 1
            self.pos += 1
        return v


class MTF:
    """One field's move-to-front list. With a vocabulary, a miss is coded as
    its index in it; without, values are only collected (the first pass)."""
    def __init__(self, vocab=None, seen=None):
        self.items = []
        self.vocab = vocab
        self.seen = seen
        self.width = max(1, (len(vocab) - 1).bit_length()) if vocab else 8

    def encode(self, bits, v):
        if self.seen is not None:
            self.seen.add(v)
        if v in self.items[:3]:
            i = self.items.index(v)
            bits.code("1" * i + "0")
            self.items.remove(v)
        else:
            bits.code("111")
            bits.put(self.vocab.index(v) if self.vocab else v, self.width)
            if v in self.items:
                self.items.remove(v)
        self.items.insert(0, v)

    def decode(self, rd):
        i = 0
        while i < 3 and rd.get(1):
            i += 1
        v = self.vocab[rd.get(self.width)] if i == 3 else self.items[i]
        if v in self.items:
            self.items.remove(v)
        self.items.insert(0, v)
        return v


CLASS_CODES = {
    "run": "0", "capped": "100", "single": "101", "diag_up": "1100",
    "diag_down": "1101", "text": "11100", "block": "11101", "bend": "111100",
    "hopper": "111101", "end": "11111",
}

# The tier-coded fields; packed.6502 names each one's three bytes of
# tier_width and tier_base for unpack.6502 (TIER_ROW = 0, TIER_ENDS = 3...).
TIER_FIELDS = ("row", "ends", "len0", "len1")


class Tiers:
    """One field's tier code: its values commonest first, in three tiers
    ('0', '10', '11') of 2^width values each, the widths that make the
    game's whole stream shortest."""
    def __init__(self, counts):
        self.syms = sorted(counts, key=lambda v: (-counts[v], v))
        freq = [counts[v] for v in self.syms]
        best = None
        for ws in itertools.product(range(7), repeat=3):
            if sum(2 ** w for w in ws) < len(freq):
                continue
            bits = i = 0
            for t, w in enumerate(ws):
                bits += sum(freq[i:i + 2 ** w]) * (min(t + 1, 2) + w)
                i += 2 ** w
            if best is None or bits < best[0]:
                best = (bits, ws)
        self.widths = best[1]
        self.bases = [0, 2 ** self.widths[0], 2 ** self.widths[0] + 2 ** self.widths[1]]

    def encode(self, bits, v):
        i = self.syms.index(v)
        t = 0 if i < self.bases[1] else 1 if i < self.bases[2] else 2
        bits.code(("0", "10", "11")[t])
        bits.put(i - self.bases[t], self.widths[t])

    def decode(self, rd):
        t = 1 + rd.get(1) if rd.get(1) else 0
        return self.syms[self.bases[t] + rd.get(self.widths[t])]


class TierCount:
    """The first pass: count a field's values (written plain meanwhile)."""
    def __init__(self, counts):
        self.counts = counts

    def encode(self, bits, v):
        self.counts[v] += 1
        bits.put(v, 8)


def encode_room(room, vocabs=None, seen=None):
    """vocabs: (attr, tile, type) vocabularies and {field: Tiers}; seen:
    three sets and {field: Counter} to collect them into instead."""
    room = normalise(room)
    b = Bits()
    if vocabs:
        attrs, tiles, types = (MTF(v) for v in vocabs[:3])
        tiers = vocabs[3]
    else:
        attrs, tiles, types = (MTF(seen=x) for x in seen[:3])
        tiers = {k: TierCount(c) for k, c in seen[3].items()}
    b.put(room[0], 8)
    p = 1
    while True:
        c = room[p]
        if c == 0:
            b.code(CLASS_CODES["end"])
            break
        if c >= 0x2C or 0x20 <= c < 0x2C:
            cmd, attr, row, col, ln = room[p:p + 5]
            capped = c < 0x2C
            if capped:
                ends, typ = room[p + 5], room[p + 6]
                p += 7
            else:
                typ = room[p + 5]
                p += 6
            b.code(CLASS_CODES["capped" if capped else "run"])
            tiles.encode(b, cmd)
            attrs.encode(b, attr)
            tiers["row"].encode(b, row)
            b.put(col, 5)
            b.put(ln >> 7, 1)
            n = ln & 0x7F
            assert 1 <= n <= 32, n
            tiers["len%d" % (ln >> 7)].encode(b, n - 1)
            if capped:
                tiers["ends"].encode(b, ends)
            types.encode(b, typ)
        elif c == 10:
            _, attr, tile, row, col, typ = room[p:p + 6]
            p += 6
            b.code(CLASS_CODES["single"])
            attrs.encode(b, attr)
            tiles.encode(b, tile)
            tiers["row"].encode(b, row)
            b.put(col, 5)
            types.encode(b, typ)
        elif c in (8, 9):
            _, attr, row, col, ln, typ = room[p:p + 6]
            p += 6
            assert 1 <= ln <= 31
            b.code(CLASS_CODES["diag_up" if c == 8 else "diag_down"])
            attrs.encode(b, attr)
            tiers["row"].encode(b, row)
            b.put(col, 5)
            b.put(ln, 5)
            types.encode(b, typ)
        elif c == 2:
            attr, row, col = room[p + 1:p + 4]
            p += 4
            b.code(CLASS_CODES["text"])
            attrs.encode(b, attr)
            tiers["row"].encode(b, row)
            b.put(col, 5)
            while room[p] != 0x80:
                b.put(TEXT_CHARS.index(chr(room[p])), 5)
                p += 1
            b.put(31, 5)
            p += 1
        elif c == 1:
            _, attr, row, col, h, w, typ = room[p:p + 7]
            p += 7
            assert h < 32 and w < 32
            b.code(CLASS_CODES["block"])
            attrs.encode(b, attr)
            tiers["row"].encode(b, row)
            b.put(col, 5)
            b.put(h, 5)
            b.put(w, 5)
            types.encode(b, typ)
        elif 3 <= c <= 6:
            _, attr, row, col, typ = room[p:p + 5]
            p += 5
            b.code(CLASS_CODES["bend"])
            b.put(c - 3, 2)
            attrs.encode(b, attr)
            tiers["row"].encode(b, row)
            b.put(col, 5)
            types.encode(b, typ)
        elif c == 7:
            _, attr, row, col, rows, width = room[p:p + 6]
            p += 6
            assert rows < 32 and width < 64
            b.code(CLASS_CODES["hopper"])
            attrs.encode(b, attr)
            tiers["row"].encode(b, row)
            b.put(col, 5)
            b.put(rows, 5)
            b.put(width, 6)
        else:
            raise ValueError(f"command {c:02X}")
    return b.bytes()


def read_class(rd):
    code = ""
    names = {v: k for k, v in CLASS_CODES.items()}
    while code not in names:
        code += str(rd.get(1))
    return names[code]


def make_vocabs(rooms):
    seen = (set(), set(), set(), {k: Counter() for k in TIER_FIELDS})
    for room in rooms.values():
        encode_room(room, seen=seen)
    return tuple(sorted(x) for x in seen[:3]) + ({k: Tiers(c) for k, c in seen[3].items()},)


def decode_room(data, vocabs):
    rd = Reader(data)
    attrs, tiles, types = (MTF(v) for v in vocabs[:3])
    row = vocabs[3]["row"].decode
    out = [rd.get(8)]
    while True:
        k = read_class(rd)
        if k == "end":
            out.append(0)
            return bytes(out)
        if k in ("run", "capped"):
            out += [tiles.decode(rd), attrs.decode(rd), row(rd), rd.get(5)]
            vert = rd.get(1)
            out.append(vert << 7 | (vocabs[3][f"len{vert}"].decode(rd) + 1))
            if k == "capped":
                out.append(vocabs[3]["ends"].decode(rd))
            out.append(types.decode(rd))
        elif k == "single":
            out += [10, attrs.decode(rd), tiles.decode(rd), row(rd), rd.get(5), types.decode(rd)]
        elif k in ("diag_up", "diag_down"):
            out += [8 if k == "diag_up" else 9, attrs.decode(rd), row(rd), rd.get(5), rd.get(5),
                    types.decode(rd)]
        elif k == "text":
            out += [2, attrs.decode(rd), row(rd), rd.get(5)]
            while (ch := rd.get(5)) != 31:
                out.append(ord(TEXT_CHARS[ch]))
            out.append(0x80)
        elif k == "block":
            out += [1, attrs.decode(rd), row(rd), rd.get(5), rd.get(5), rd.get(5), types.decode(rd)]
        elif k == "bend":
            out += [3 + rd.get(2), attrs.decode(rd), row(rd), rd.get(5), types.decode(rd)]
        elif k == "hopper":
            out += [7, attrs.decode(rd), row(rd), rd.get(5), rd.get(5), rd.get(6)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write packed.bin and packed.6502 to this directory")
    args = ap.parse_args()
    rooms = load_rooms()
    vocabs = make_vocabs(rooms)
    packed = {}
    for r, room in rooms.items():
        packed[r] = encode_room(room, vocabs)
        back = decode_room(packed[r], vocabs)
        if back != normalise(room):
            raise SystemExit(f"room {r}: round trip failed")
    raw = sum(len(x) for x in rooms.values())
    tot = sum(len(x) for x in packed.values())
    print(f"{raw} bytes raw, {tot} packed ({100 * tot / raw:.1f}%), largest room unpacked "
          f"{max(len(x) for x in rooms.values())}; round trip OK for all 120")
    if args.out:
        blob = b"".join(packed[r] for r in range(1, 121))
        with open(f"{args.out}/packed.bin", "wb") as f:
            f.write(blob)
        lens = [len(packed[r]) for r in range(1, 121)]
        assert max(lens) < 256
        lines = ["\\ Generated by tools/packrooms.py: do not edit.", "",
                 "\\ Each room's bit stream's length: room r's follows rooms 1 to r - 1's",
                 "\\ from packed_rooms (unpack.6502 adds them up).",
                 ".packed_lengths"]
        for i in range(0, 120, 12):
            lines.append("    EQUB " + ", ".join(f"{n:3d}" for n in lens[i:i + 12]))
        lines.append(f"ROOM_BUFFER_SIZE = {max(len(x) for x in rooms.values())}")
        # The tier codes: three widths and three starts in tier_syms each.
        tiers = vocabs[3]
        starts, syms = [], []
        for k in TIER_FIELDS:
            starts += [len(syms) + b for b in tiers[k].bases]
            syms += tiers[k].syms
        assert len(syms) <= 256
        lines += ["", "\\ The tier codes (row, ends, horizontal and vertical run lengths - 1):",
                  "\\ each one's three tiers' widths in bits, and where they start in",
                  "\\ tier_syms, where each code's values are, commonest first.",
                  " : ".join(f"TIER_{k.upper()} = {3 * i}" for i, k in enumerate(TIER_FIELDS)),
                  ".tier_width EQUB " + ", ".join(str(w) for k in TIER_FIELDS for w in tiers[k].widths),
                  ".tier_base EQUB " + ", ".join(str(s) for s in starts),
                  ".tier_syms"]
        for i in range(0, len(syms), 16):
            lines.append("    EQUB " + ", ".join(f"&{v:02X}" for v in syms[i:i + 16]))
        # The vocabularies, indexed by the unpacker's list bases (0, 3, 6).
        vocabs = vocabs[:3]
        widths = [MTF(v).width for v in vocabs]
        offs = [0, len(vocabs[0]), len(vocabs[0]) + len(vocabs[1])]
        lines += ["", "\\ The fields' vocabularies (attribute, tile, type) and, by list",
                  "\\ base (0, 3, 6), each one's index width and offset into vocab.",
                  f".vocab_width EQUB {widths[0]}, 0, 0, {widths[1]}, 0, 0, {widths[2]}",
                  f".vocab_off EQUB {offs[0]}, 0, 0, {offs[1]}, 0, 0, {offs[2]}",
                  ".vocab"]
        flat = [v for voc in vocabs for v in voc]
        for i in range(0, len(flat), 16):
            lines.append("    EQUB " + ", ".join(f"&{v:02X}" for v in flat[i:i + 16]))
        with open(f"{args.out}/packed.6502", "w") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
