#!/usr/bin/env python3
"""Turn a MIDI file (music/README.md: the pieces, their licences and the
options each was made with) into the in-game music's data (src/music.6502
plays it; decisions 46 and 47).

    python3 tools/mkmusic.py [--midi music/sugar-plum.mid] [--bass-top N]

Writes, committed (the build never runs this):
    src/data/music.bin      the tune: one byte an event (below)
    src/data/music.6502     the pitch table the events index: for each
                            entry, the SN76489's latch byte (its channel
                            and the divider's low four bits) and its data
                            byte (the top six)

The MIDI's timing is kept, a performance's rolled chords and ritardandos
included: times go to 50Hz frames through its tempo map. Each bar starts at a whole frame, the sum of the
rounded lengths of the bars before, and the notes in it are placed from
there, so that bars played alike (the repeats) come out alike.

Three voices from up to six notes at once: at each note's start, the notes
sounding (or struck within ROLL frames: a chord is spread) are ranked by
pitch. The highest goes to channel 0, the lowest to channel 2 (the bass),
any other to channel 1, the newest note replacing what a channel had. A
note alone is the tune's above BASS_TOP (the piece's: --bass-top), the
bass's at or below. The channels can't go under B2, so a note below that
is played an octave up. (Not periodic noise for the
bass, which would reach the lowest notes: its pitch depends on the length
of the chip's shift register, which isn't the same everywhere.) There are
no note-offs: the player lets each note decay, as a plucked or struck
string's does.

The events:
    00-BF   a note: the pitch table's entry
    C0-FD   the next events are (byte - &BF) frames on
    FE      lo hi len: play the len bytes at music + (hi lo), then carry on
            after the FE's three (a repeat: never nested)
    FF      back to the start
"""
import argparse
import bisect
import struct

ROLL = 3            # frames over which a spread chord's notes still count as one
BASS_TOP = 67       # G4: a lone note's highest for the bass (--bass-top)
TONE_LOW = 47       # B2: the lowest note the dividers reach
FPS = 50
GAP = 100           # frames of silence before it starts again
MIN_REPEAT = 6      # a repeat (4 bytes) must save at least this many


def vlq(d, i):
    v = 0
    while True:
        b = d[i]
        i += 1
        v = (v << 7) | (b & 127)
        if b < 128:
            return v, i


def parse(path):
    d = open(path, "rb").read()
    assert d[:4] == b"MThd"
    _fmt, ntr, div = struct.unpack(">HHH", d[8:14])
    i = 14
    tempos, metres, notes = [], [], []
    for _ in range(ntr):
        assert d[i:i + 4] == b"MTrk"
        end = i + 8 + struct.unpack(">I", d[i + 4:i + 8])[0]
        j, tick, run, on = i + 8, 0, None, {}
        i = end
        while j < end:
            dt, j = vlq(d, j)
            tick += dt
            s = d[j]
            if s == 0xFF:
                ty = d[j + 1]
                ln, k = vlq(d, j + 2)
                if ty == 0x51:
                    tempos.append((tick, int.from_bytes(d[k:k + ln], "big")))
                elif ty == 0x58:        # a time signature: its bar in ticks
                    metres.append((tick, d[k] * div * 4 >> d[k + 1]))
                j = k + ln
                continue
            if s in (0xF0, 0xF7):
                ln, k = vlq(d, j + 1)
                j = k + ln
                continue
            if s & 0x80:
                run = s
                j += 1
            n = 1 if run & 0xF0 in (0xC0, 0xD0) else 2
            a = d[j:j + n]
            j += n
            st = run & 0xF0
            if st == 0x90 and a[1]:
                on.setdefault(a[0], []).append(tick)
            elif st in (0x80, 0x90) and on.get(a[0]):
                notes.append((on[a[0]].pop(0), tick, a[0]))
    tempos.sort()
    metres = sorted(set(metres)) or [(0, 4 * div)]
    return div, tempos, metres, sorted(notes)


def seconds(tempos, div):
    """A function from ticks to seconds, through the tempo map."""
    marks = []          # (tick, seconds there, seconds a tick from there)
    t = 0.0
    last_tick, last_spt = 0, 500000 / 1e6 / div
    for tick, us in tempos:
        t += (tick - last_tick) * last_spt
        last_tick, last_spt = tick, us / 1e6 / div
        marks.append((tick, t, last_spt))
    if not marks or marks[0][0]:
        marks.insert(0, (0, 0.0, 500000 / 1e6 / div))

    def at(tick):
        m = max((m for m in marks if m[0] <= tick), key=lambda m: m[0])
        return m[1] + (tick - m[0]) * m[2]
    return at


def to_frames(notes, div, tempos, metres):
    at = seconds(tempos, div)
    # The bars' ticks, through the time signatures, to past the last note.
    last = max(e for s, e, p in notes)
    bars, tick, m = [], 0, 0
    while tick <= last:
        while m + 1 < len(metres) and metres[m + 1][0] <= tick:
            m += 1
        bars.append(tick)
        tick += metres[m][1]
    bars.append(tick)
    starts = [0]
    for b in range(len(bars) - 1):
        starts.append(starts[-1] + round((at(bars[b + 1]) - at(bars[b])) * FPS))

    def frame(tick):
        b = bisect.bisect_right(bars, tick) - 1
        return starts[b] + round((at(tick) - at(bars[b])) * FPS)
    return [(frame(s), max(frame(e), frame(s) + 1), p) for s, e, p in notes]


def voices(notes, bass_top):
    """(frame, channel, pitch) for each note kept: channel 0, 1 or 2 (the bass)."""
    out = {}
    for s, e, p in notes:
        near = [q for s2, e2, q in notes if s2 <= s + ROLL and e2 > s]
        hi, lo = max(near), min(near)
        if len(near) == 1:
            ch = 0 if p > bass_top else 2
        elif p == hi:
            ch = 0
        elif p == lo:
            ch = 2
        else:
            ch = 1
        while p < TONE_LOW:
            p += 12
        # The newest note on a channel wins; in a frame, the one ranked first.
        key = (s, ch)
        if key not in out or (ch == 0 and p > out[key]) or (ch == 2 and p < out[key]) or ch == 1:
            out[key] = p
    return sorted((s, ch, p) for (s, ch), p in out.items())


def divider(ch, p):
    n = round(125000 / (440 * 2 ** ((p - 69) / 12)))
    assert 1 <= n <= 1023, (ch, p, n)
    return n


def encode(events):
    table = sorted({(ch, divider(ch, p)) for _, ch, p in events})
    assert len(table) <= 0xC0
    index = {k: i for i, k in enumerate(table)}
    raw, now = [], 0
    for s, ch, p in events:
        while s > now:
            n = min(s - now, 0xFE - 0xC0)
            raw.append(0xBF + n)
            now += n
        raw.append(index[(ch, divider(ch, p))])
    gap = GAP
    while gap:
        n = min(gap, 0xFE - 0xC0)
        raw.append(0xBF + n)
        gap -= n
    return table, raw


def compress(raw):
    """Greedy: the longest earlier run of bytes that went out as they were."""
    out, where = bytearray(), {}        # where: raw position -> out position, for bytes out as they were
    i = 0
    while i < len(raw):
        best_len, best_at = 0, 0
        for j in range(i):
            if j not in where:
                continue
            n = 0
            while (i + n < len(raw) and n < 255 and j + n < i and j + n in where
                   and where[j + n] == where[j] + n and raw[j + n] == raw[i + n]):
                n += 1
            if n > best_len:
                best_len, best_at = n, where[j]
        if best_len >= MIN_REPEAT:
            out += bytes([0xFE, best_at & 255, best_at >> 8, best_len])
            i += best_len
        else:
            where[i] = len(out)
            out.append(raw[i])
            i += 1
    out.append(0xFF)
    return bytes(out)


def expand(data):
    """The player's reading, for a check."""
    out, i = [], 0
    while data[i] != 0xFF:
        if data[i] == 0xFE:
            at, n = data[i + 1] | data[i + 2] << 8, data[i + 3]
            out += data[at:at + n]
            i += 4
        else:
            out.append(data[i])
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--midi", default="music/sugar-plum.mid")
    ap.add_argument("--bass-top", type=int, default=BASS_TOP)
    args = ap.parse_args()
    div, tempos, metres, notes = parse(args.midi)
    events = voices(to_frames(notes, div, tempos, metres), args.bass_top)
    table, raw = encode(events)
    data = compress(raw)
    assert expand(data) == raw
    assert all(b < 0xFE for b in raw)
    open("src/data/music.bin", "wb").write(data)
    with open("src/data/music.6502", "w") as f:
        f.write(f"\\ Made by tools/mkmusic.py from {args.midi}: don't edit.\n")
        f.write("\\ The pitch table: each entry's SN76489 latch byte, then its data byte.\n")
        f.write(".music_latch\n")
        for i in range(0, len(table), 8):
            f.write("    EQUB " + ", ".join(f"&{0x80 | ch << 5 | n & 15:02X}" for ch, n in table[i:i + 8]) + "\n")
        f.write(".music_data\n")
        for i in range(0, len(table), 8):
            f.write("    EQUB " + ", ".join(f"&{n >> 4:02X}" for ch, n in table[i:i + 8]) + "\n")
    frames = sum(b - 0xBF for b in raw if b >= 0xC0)
    print(f"{len(events)} notes, {frames / FPS:.0f}s; table {len(table)}; "
          f"events {len(raw)} bytes, {len(data)} with repeats")


if __name__ == "__main__":
    main()
