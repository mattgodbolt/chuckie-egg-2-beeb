import sys
sys.path.insert(0, "tools")
from packrooms import load_rooms, make_vocabs, encode_room

data = open("src/data/roomdata.bin", "rb").read()
offsets = [0] + [int(x) for x in open("src/data/roomoffsets.txt").read().split()]


def parse(r):
    p = offsets[r]
    recs = []
    bg = data[p]
    p += 1
    while True:
        c = data[p]
        if c == 0:
            break
        if c == 2:
            q = p + 4
            while data[q] != 0x80:
                q += 1
            recs.append(data[p:q + 1])
            p = q + 1
        elif c < 0x20:
            n = {1: 7, 3: 5, 4: 5, 5: 5, 6: 5, 7: 6, 8: 6, 9: 6, 10: 6}[c]
            recs.append(data[p:p + n])
            p += n
        elif c < 0x2C:
            recs.append(data[p:p + 7])
            p += 7
        else:
            recs.append(data[p:p + 6])
            p += 6
    return bg, recs


def kind(c):
    if c >= 0x2C:
        return 'run'
    if c >= 0x20:
        return 'cap'
    return {1: 'blk', 2: 'txt', 3: 'bend', 4: 'bend', 5: 'bend', 6: 'bend', 7: 'hop', 8: 'dg', 9: 'dg', 10: 'one'}[c]


if __name__ == "__main__":
    rooms = load_rooms()
    vocabs = make_vocabs(rooms)
    if len(sys.argv) > 1:
        for r in map(int, sys.argv[1:]):
            bg, recs = parse(r)
            print(f"room {r}: bg {bg:02X}, {len(recs)} records, {sum(len(x) for x in recs) + 2} bytes, "
                  f"packed {len(encode_room(rooms[r], vocabs))}")
            for x in recs:
                print("  ", " ".join(f"{b:02X}" for b in x), (bytes(x[4:-1]).decode() if x[0] == 2 else ""))
    else:
        for r in range(1, 121):
            bg, recs = parse(r)
            kinds = sorted(set(kind(x[0]) for x in recs))
            print(r, len(recs), sum(len(x) for x in recs) + 2, len(encode_room(rooms[r], vocabs)), kinds)
