#!/usr/bin/env python3
"""Pack the room data into a bit stream a room at a time, and unpack it
again to prove the round trip.

    python3 tools/packrooms.py [--out src/data]

The packed form unpacks to the original's bytecode exactly, so the room
drawer (a transcription of the original's) is unchanged: unpack a room into
a buffer, draw from the buffer.

Each room is a stream of bits, most significant first:

    background attribute    8 bits
    records, until `end`    a class code, then the class's fields

Class codes (a prefix code, commonest shortest), and fields:

    0       run      tile* attr* row col vert len-1(5) type*
    100     capped   tile* attr* row col vert len-1(5) ends(8) type*
    101     single   attr* tile* row col type*
    1100    diag up      attr* row col len(5) type*
    1101    diag down    attr* row col len(5) type*
    11100   text         attr* row col chars(5 each) until 31
    11101   block        attr* row col h(5) w(5) type*
    111100  bend         which(2) attr* row col type*   (commands 3-6)
    111101  hopper       attr* row col rows(5) width(6)
    11111   end

The fields come in the bytecode's own order, so the unpacker emits each as
it decodes it.

row is 5 bits, col 5. One run in the whole game (room 33) says column 32
of row 11; the original's arithmetic makes that row 12 column 0, so it is
packed as that, and the round trip is checked against the room with that
one record normalised (normalise()). Fields marked * are move-to-front coded, one list
each for attribute, tile and type, kept per room: 0 = "the last one" (1
bit), 1 = '10', 2 = '110', otherwise '111' and the 8-bit value. Text
characters index TEXT_CHARS.
"""
import argparse
import os
import sys

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
    def __init__(self):
        self.items = []

    def encode(self, bits, v):
        if v in self.items[:3]:
            i = self.items.index(v)
            bits.code("1" * i + "0")
            self.items.remove(v)
        else:
            bits.code("111")
            bits.put(v, 8)
            if v in self.items:
                self.items.remove(v)
        self.items.insert(0, v)

    def decode(self, rd):
        i = 0
        while i < 3 and rd.get(1):
            i += 1
        v = rd.get(8) if i == 3 else self.items[i]
        if v in self.items:
            self.items.remove(v)
        self.items.insert(0, v)
        return v


CLASS_CODES = {
    "run": "0", "capped": "100", "single": "101", "diag_up": "1100",
    "diag_down": "1101", "text": "11100", "block": "11101", "bend": "111100",
    "hopper": "111101", "end": "11111",
}


def encode_room(room):
    room = normalise(room)
    b = Bits()
    attrs, tiles, types = MTF(), MTF(), MTF()
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
            b.put(row, 5)
            b.put(col, 5)
            b.put(ln >> 7, 1)
            n = ln & 0x7F
            assert 1 <= n <= 32, n
            b.put(n - 1, 5)
            if capped:
                b.put(ends, 8)
            types.encode(b, typ)
        elif c == 10:
            _, attr, tile, row, col, typ = room[p:p + 6]
            p += 6
            b.code(CLASS_CODES["single"])
            attrs.encode(b, attr)
            tiles.encode(b, tile)
            b.put(row, 5)
            b.put(col, 5)
            types.encode(b, typ)
        elif c in (8, 9):
            _, attr, row, col, ln, typ = room[p:p + 6]
            p += 6
            assert 1 <= ln <= 31
            b.code(CLASS_CODES["diag_up" if c == 8 else "diag_down"])
            attrs.encode(b, attr)
            b.put(row, 5)
            b.put(col, 5)
            b.put(ln, 5)
            types.encode(b, typ)
        elif c == 2:
            attr, row, col = room[p + 1:p + 4]
            p += 4
            b.code(CLASS_CODES["text"])
            attrs.encode(b, attr)
            b.put(row, 5)
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
            b.put(row, 5)
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
            b.put(row, 5)
            b.put(col, 5)
            types.encode(b, typ)
        elif c == 7:
            _, attr, row, col, rows, width = room[p:p + 6]
            p += 6
            assert rows < 32 and width < 64
            b.code(CLASS_CODES["hopper"])
            attrs.encode(b, attr)
            b.put(row, 5)
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


def decode_room(data):
    rd = Reader(data)
    attrs, tiles, types = MTF(), MTF(), MTF()
    out = [rd.get(8)]
    while True:
        k = read_class(rd)
        if k == "end":
            out.append(0)
            return bytes(out)
        if k in ("run", "capped"):
            out += [tiles.decode(rd), attrs.decode(rd), rd.get(5), rd.get(5)]
            vert = rd.get(1)
            out.append(vert << 7 | (rd.get(5) + 1))
            if k == "capped":
                out.append(rd.get(8))
            out.append(types.decode(rd))
        elif k == "single":
            out += [10, attrs.decode(rd), tiles.decode(rd), rd.get(5), rd.get(5), types.decode(rd)]
        elif k in ("diag_up", "diag_down"):
            out += [8 if k == "diag_up" else 9, attrs.decode(rd), rd.get(5), rd.get(5), rd.get(5),
                    types.decode(rd)]
        elif k == "text":
            out += [2, attrs.decode(rd), rd.get(5), rd.get(5)]
            while (ch := rd.get(5)) != 31:
                out.append(ord(TEXT_CHARS[ch]))
            out.append(0x80)
        elif k == "block":
            out += [1, attrs.decode(rd), rd.get(5), rd.get(5), rd.get(5), rd.get(5), types.decode(rd)]
        elif k == "bend":
            out += [3 + rd.get(2), attrs.decode(rd), rd.get(5), rd.get(5), types.decode(rd)]
        elif k == "hopper":
            out += [7, attrs.decode(rd), rd.get(5), rd.get(5), rd.get(5), rd.get(6)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write packed.bin and packed.6502 to this directory")
    args = ap.parse_args()
    rooms = load_rooms()
    packed = {}
    for r, room in rooms.items():
        packed[r] = encode_room(room)
        back = decode_room(packed[r])
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
        offs = [0]
        for r in range(1, 121):
            offs.append(offs[-1] + len(packed[r]))
        lines = ["\\ Generated by tools/packrooms.py: do not edit.", "",
                 "\\ Room r's bit stream is at packed_rooms + packed_offsets[r - 1].",
                 ".packed_offsets"]
        for i in range(0, 120, 8):
            lines.append("    EQUW " + ", ".join(f"{o:4d}" for o in offs[i:min(i + 8, 120)]))
        lines.append(f"ROOM_BUFFER_SIZE = {max(len(x) for x in rooms.values())}")
        with open(f"{args.out}/packed.6502", "w") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
