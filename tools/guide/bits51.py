"""Room 51's packed bit stream, field by field."""
import inspect
import sys
sys.path.insert(0, "tools")
import packrooms as P

log = []


def where():
    for fr in inspect.stack()[2:]:
        if fr.function == "encode_room":
            return fr.code_context[0].strip()
    return "?"


class LBits(P.Bits):
    def put(self, value, n):
        log.append((where(), "".join(str((value >> i) & 1) for i in range(n - 1, -1, -1))))
        super().put(value, n)

    def code(self, s):
        log.append((where(), s))
        super().code(s)


rooms = P.load_rooms()
vocabs = P.make_vocabs(rooms)
P.Bits = LBits
r = int(sys.argv[1]) if len(sys.argv) > 1 else 51
packed = P.encode_room(rooms[r], vocabs)
print(len(packed), "bytes:", packed.hex(" "))
total = 0
for w, b in log:
    total += len(b)
    print(f"{b:>14}  {w}")
print(total, "bits")
t = vocabs[3]
for k in P.TIER_FIELDS:
    print(k, t[k].widths, t[k].syms[:12])
print("vocab sizes", [len(v) for v in vocabs[:3]])
