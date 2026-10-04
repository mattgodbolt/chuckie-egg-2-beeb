#!/usr/bin/env python3
"""
zx02.py - a Python port of Daniel Serpell's ZX02 compressor (the 6502-tuned
fork of Einar Saukas' ZX0), plus a decompressor for round-trip verification.

beeb-port-kit template: this is what this port compresses with, and the only
compressor in tools/. The kit also carries zx0.py, because the two shipping
ports (paradroid-beeb, edge-beeb) are ZX0 discs; the formats are not
interchangeable, so a project picks one compressor and one depacker.

WHY ZX02 AND NOT ZX0, measured 2026-09-07 over 43 real data files from both
ports (242,481 bytes: sprites, tiles, chars, music, loading screens, panels):
  - the depacker is 131 bytes, against zx0depack.6502's 257;
  - it decodes 2.14x faster - 53.9 cycles/byte against 115.4, every file
    between 2.04x and 2.19x, measured by stepping both depackers in py65 and
    comparing the output with the source file byte for byte;
  - it costs +0.11% on the packed total (90,891 bytes against 90,793). Per
    file the loss is under 1% except on data that is mostly one repeated run,
    where ZX02's 8-bit lengths tell: the template's near-empty panel.bin went
    67 -> 79 bytes. Nothing real lost more than 6 bytes.
Trade the 0.11% for half the code and twice the speed. Redo the measurement
if you doubt it - the harness is lib/test/bench/bench_depack.py in the kit,
and it checks every decode against the source file - but do not re-argue it
from the upstream READMEs, which claim ZX02 wins on ratio too. On this
corpus it does not.

Ported from the reference C (optimize.c + compress.c of
https://github.com/dmsc/zx02, MIT, (c) 2022 Daniel Serpell, over Einar
Saukas' BSD-3 ZX0) in its DEFAULT mode - forwards, elias_ending_bit = 0,
elias_short_code = 0, zx1_mode = 0, initial offset 1. `zx02.exe -f` with no
other flag produces exactly what compress() produces; py/tests/test_zx02.py
asserts that on every file it can find. Change a flag and you must change
lib/zx02depack.6502, which decodes exactly this.

FORKED into beeb-port-kit/template 2026-09-07, unchanged.

compress() is O(n * max_offset) pure Python and takes seconds on a 16K bank;
make_disc.py calls zx02.exe for the real streams and uses this module as the
oracle. For a file already compressed by the exe, decompress() is all you
need.

THE FORMAT, as the 6502 stream reader sees it (see lib/zx02depack.6502):
  - the stream opens in a literal run (no flag bit);
  - after literals, flag 0 = copy from the LAST offset, 1 = new offset;
  - after any copy,  flag 0 = literals,                1 = new offset;
  - a length is interlaced gamma: pairs of (continue=1, payload) bits,
    terminated by a 0, building the value MSB-first from an implicit leading
    1. The value is 8-BIT: 256 encodes as 0 and 0 means 256 - which is why
    the depacker's accumulator is a register and its copy loops are DEX/BNE;
  - a new offset is gamma MSB (payload NOT inverted; the value 256, read back
    as 0, is the end marker), then one byte: ((offset - 1) MOD 128) << 1,
    whose bit 0 is the FIRST control bit of the following gamma, which
    encodes length - 1;
  - offset = (MSB - 1) * 128 + (LSB >> 1) + 1.
That is where it differs from ZX0: positive offsets, the ending bit flipped,
gamma capped at 8 bits. Same shape, cheaper to decode.
"""

INITIAL_OFFSET = 1
MAX_OFFSET_ZX02 = 32640


class Block:
    __slots__ = ('chain', 'bits', 'index', 'offset')

    def __init__(self, bits, index, offset, chain):
        self.bits = bits
        self.index = index
        self.offset = offset
        self.chain = chain


BIG = 1 << 20


def elias_gamma_bits(value):
    """Bits to encode `value`. ZX02 gamma is 8-bit: outside 1..256 the value
    is unencodable, and the optimizer is told so with a cost it will never
    choose."""
    if value < 1 or value > 0x100:
        return BIG
    bits = 1
    while value >> 1:
        value >>= 1
        bits += 2
    return bits


def elias_gamma_bits_1(value):
    """Cost of a length written as gamma(length - 1), where 0 wraps to 256."""
    if value == 1:
        return elias_gamma_bits(256)
    if value > 256:
        return BIG
    return elias_gamma_bits(value - 1)


def offset_bits(value):
    return 8 + elias_gamma_bits(value // 128 + 1)


def offset_ceiling(index, offset_limit):
    return offset_limit if index > offset_limit else (
        INITIAL_OFFSET if index < INITIAL_OFFSET else index)


def optimize(input_data, skip=0, offset_limit=MAX_OFFSET_ZX02):
    input_size = len(input_data)
    max_offset = offset_ceiling(input_size - 1, offset_limit)

    last_literal = [None] * (max_offset + 1)
    last_match = [None] * (max_offset + 1)
    optimal = [None] * input_size
    match_length = [0] * (max_offset + 1)
    best_length = [0] * input_size
    if input_size > 1:
        best_length[1] = 1

    last_match[INITIAL_OFFSET] = Block(-1, skip - 1, INITIAL_OFFSET, None)

    for index in range(skip, input_size):
        best_length_size = 1
        max_offset = offset_ceiling(index, offset_limit)
        for offset in range(1, max_offset + 1):
            if index != skip and index >= offset and \
                    input_data[index] == input_data[index - offset]:
                ll = last_literal[offset]
                if ll is not None:
                    length = index - ll.index
                    bits = ll.bits + 1 + elias_gamma_bits(length)
                    last_match[offset] = Block(bits, index, offset, ll)
                    if optimal[index] is None or optimal[index].bits > bits:
                        optimal[index] = last_match[offset]
                match_length[offset] += 1
                if best_length_size < match_length[offset]:
                    bits = optimal[index - best_length[best_length_size]].bits + \
                        elias_gamma_bits_1(best_length[best_length_size])
                    while True:
                        best_length_size += 1
                        bits2 = optimal[index - best_length_size].bits + \
                            elias_gamma_bits_1(best_length_size)
                        if bits2 <= bits:
                            best_length[best_length_size] = best_length_size
                            bits = bits2
                        else:
                            best_length[best_length_size] = \
                                best_length[best_length_size - 1]
                        if best_length_size >= match_length[offset]:
                            break
                length = best_length[match_length[offset]]
                bits = optimal[index - length].bits + offset_bits(offset) + \
                    elias_gamma_bits_1(length)
                lm = last_match[offset]
                if lm is None or lm.index != index or lm.bits > bits:
                    last_match[offset] = Block(bits, index, offset,
                                               optimal[index - length])
                    if optimal[index] is None or optimal[index].bits > bits:
                        optimal[index] = last_match[offset]
            else:
                match_length[offset] = 0
                lm = last_match[offset]
                if lm is not None:
                    length = index - lm.index
                    bits = lm.bits + 1 + elias_gamma_bits(length) + length * 8
                    last_literal[offset] = Block(bits, index, 0, lm)
                    if optimal[index] is None or optimal[index].bits > bits:
                        optimal[index] = last_literal[offset]

    return optimal[input_size - 1]


class _Writer:
    def __init__(self):
        self.out = bytearray()
        self.bit_mask = 0
        self.bit_index = 0
        self.backtrack = True

    def write_byte(self, value):
        self.out.append(value & 0xFF)

    def write_bit(self, value):
        if self.backtrack:
            if value:
                self.out[-1] |= 1
            self.backtrack = False
        else:
            if not self.bit_mask:
                self.bit_mask = 128
                self.bit_index = len(self.out)
                self.write_byte(0)
            if value:
                self.out[self.bit_index] |= self.bit_mask
            self.bit_mask >>= 1

    def write_gamma(self, value):
        if not value:                               # 8-bit: 0 means 256
            value = 0x100
        i = 2
        while i <= value:
            i <<= 1
        i >>= 1
        while True:
            i >>= 1
            if not i:
                break
            self.write_bit(1)                       # continuation
            self.write_bit(1 if (value & i) else 0)
        self.write_bit(0)                           # terminator


def compress(input_data, skip=0, offset_limit=MAX_OFFSET_ZX02):
    """The default zx02 stream for input_data. Byte-identical to `zx02 -f`."""
    optimal = optimize(input_data, skip, offset_limit)

    # un-reverse the chain
    prev = None
    while optimal is not None:
        nxt = optimal.chain
        optimal.chain = prev
        prev = optimal
        optimal = nxt

    w = _Writer()
    w.backtrack = True
    last_offset = INITIAL_OFFSET
    last_literal = False
    input_index = skip

    node = prev.chain
    prev_node = prev
    while node is not None:
        length = node.index - prev_node.index
        if node.offset == 0:
            w.write_bit(0)
            w.write_gamma(length)
            for _ in range(length):
                w.write_byte(input_data[input_index])
                input_index += 1
            last_literal = True
        elif node.offset == last_offset and last_literal:
            w.write_bit(0)
            w.write_gamma(length)
            input_index += length
            last_literal = False
        else:
            w.write_bit(1)
            w.write_gamma((node.offset - 1) // 128 + 1)
            w.write_byte(((node.offset - 1) % 128) << 1)
            w.backtrack = True                      # the LSB's bit 0 is a flag
            w.write_gamma(length - 1)
            input_index += length
            last_offset = node.offset
            last_literal = False
        prev_node = node
        node = node.chain

    w.write_bit(1)
    w.write_gamma(256)
    return bytes(w.out)


def decompress(z):
    """Round-trip verifier: decodes exactly what lib/zx02depack.6502 decodes,
    8-bit wraparound included."""
    out = bytearray()
    pos = 0
    bit_mask = 0
    bit_byte = 0
    backtrack = [None]     # holds the offset-LSB byte whose bit 0 is the
                           # next control bit, mirroring the compressor

    def bit():
        nonlocal bit_mask, bit_byte, pos
        if backtrack[0] is not None:
            b = backtrack[0] & 1
            backtrack[0] = None
            return b
        if not bit_mask:
            bit_byte = z[pos]
            pos += 1
            bit_mask = 128
        b = 1 if (bit_byte & bit_mask) else 0
        bit_mask >>= 1
        return b

    def gamma():
        """The value the 6502's X register would hold: 8-bit, 0 meaning 256
        to the copy loops and END to the offset reader."""
        v = 1
        while bit():
            v = ((v << 1) | bit()) & 0xFF
        return v

    def count(v):
        return v if v else 256

    last_offset = INITIAL_OFFSET
    state = 'literals'
    while True:
        if state == 'literals':
            length = count(gamma())
            out.extend(z[pos:pos + length])
            pos += length
            state = 'new' if bit() else 'copy'
        elif state == 'copy':
            length = count(gamma())
            for _ in range(length):
                out.append(out[-last_offset])
            state = 'new' if bit() else 'literals'
        else:                                       # new offset
            msb = gamma()
            if msb == 0:                            # gamma 256 wrapped: END
                return bytes(out)
            lsb = z[pos]
            pos += 1
            last_offset = (msb - 1) * 128 + (lsb >> 1) + 1
            backtrack[0] = lsb                      # gamma starts in its bit 0
            length = (gamma() + 1) & 0xFF
            length = count(length)
            for _ in range(length):
                out.append(out[-last_offset])
            state = 'new' if bit() else 'literals'


if __name__ == '__main__':
    import sys
    data = open(sys.argv[1], 'rb').read()
    z = compress(data)
    print('%d -> %d' % (len(data), len(z)))
    assert decompress(z) == data, 'round-trip FAILED'
    print('round-trip ok')
    if len(sys.argv) > 2:
        open(sys.argv[2], 'wb').write(z)
