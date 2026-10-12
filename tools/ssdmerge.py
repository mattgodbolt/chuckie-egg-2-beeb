#!/usr/bin/env python3
"""Add the files of one Acorn DFS disc image to another's.

    python3 tools/ssdmerge.py out.ssd base.ssd extra.ssd [NAME=file ...]

The two editions are two assemblies of src/main.6502 (docs/streaming.md):
the release disc's (MENU, CE2, CE2DATA, !BOOT) and the streaming
edition's (CE2S). This puts the second disc's files on the first, after
its last file, then each NAME=file, a file as it is (CE2ROOM, the
streaming edition's rooms, src/data/roomrecs.bin: past 64K, more than an
assembly can hold), loaded at &0000 in the I/O processor, and writes the
result. CE2ROOM starts a track (ten sectors): the game reads it by track
and sector, and none of its rooms' records crosses a track
(tools/mkrecords.py). A name on both discs is an error.

The catalogue (Acorn DFS): sector 0 has the title's first 8 bytes, then
eight bytes a file, its name (7) and directory (bit 7: locked); sector 1
the title's last 4, the write count, 8 * the number of files, the boot
option and the disc's size in sectors, then eight bytes a file: load,
exec, length (two bytes each), their top bits and the start sector's in
one byte, and the start sector's low byte. Files are listed from the
highest start sector down.
"""
import sys

SECTOR = 256
TRACK = 10                  # sectors


def catalogue(img):
    n = img[SECTOR + 5] // 8
    files = []
    for i in range(1, n + 1):
        name = bytes(img[8 * i:8 * i + 8])
        info = bytes(img[SECTOR + 8 * i:SECTOR + 8 * i + 8])
        mixed = info[6]
        length = info[4] | info[5] << 8 | (mixed >> 4 & 3) << 16
        start = info[7] | (mixed & 3) << 8
        files.append((name, info, length, start))
    return files


def raw_files(specs):
    """NAME=file arguments as an image of their own, catalogue and data,
    for main's loop: each in directory $, loaded at &FFFF0000."""
    img, files = bytearray(), []
    for spec in specs:
        name, path = spec.split("=", 1)
        data = open(path, "rb").read()
        start = len(img) // SECTOR
        assert len(name) <= 7 and len(data) < 1 << 18
        info = bytes([0, 0, 0, 0, len(data) & 0xFF, len(data) >> 8 & 0xFF,
                      0xCC | (len(data) >> 16 & 3) << 4, 0])
        files.append((name.encode().ljust(7) + b"$", info, len(data), start))
        img += data + bytes(-len(data) % SECTOR)
    return bytes(img), files


def main():
    out, base_path, extra_path = sys.argv[1:4]
    base = bytearray(open(base_path, "rb").read())
    have = catalogue(base)
    extra = open(extra_path, "rb").read()
    raw, raw_cat = raw_files(sys.argv[4:])
    # (The raw files after the extra disc's, as if on it: their sectors
    # after its last.)
    shift = len(extra) // SECTOR + 1
    extra += bytes(shift * SECTOR - len(extra)) + raw
    extra_cat = list(reversed(catalogue(extra))) + [(n, i, length, start + shift) for n, i, length, start in raw_cat]
    sectors = base[SECTOR + 7] | (base[SECTOR + 6] & 3) << 8
    names = {name for name, *_ in have}
    end = max([start + (length + SECTOR - 1) // SECTOR for _, _, length, start in have] + [2])
    added = []
    for name, info, length, start in extra_cat:
        if name in names:
            raise SystemExit(f"{bytes(name).decode().strip()}: on both discs")
        size = (length + SECTOR - 1) // SECTOR
        if name.startswith(b"CE2ROOM"):
            end += -end % TRACK
        if end + size > sectors:
            raise SystemExit("the disc is full")
        data = extra[start * SECTOR:start * SECTOR + length]
        if len(base) < (end + size) * SECTOR:
            base += bytes((end + size) * SECTOR - len(base))
        base[end * SECTOR:end * SECTOR + length] = data
        info = bytearray(info)
        info[6] = (info[6] & 0xFC) | end >> 8
        info[7] = end & 0xFF
        added.append((name, bytes(info)))
        end += size
    entries = [(name, info) for name, info in reversed(added)] + [(name, info) for name, info, *_ in have]
    if len(entries) > 31:
        raise SystemExit("too many files")
    for i, (name, info) in enumerate(entries, 1):
        base[8 * i:8 * i + 8] = name
        base[SECTOR + 8 * i:SECTOR + 8 * i + 8] = info
    base[SECTOR + 5] = 8 * len(entries)
    open(out, "wb").write(base)


if __name__ == "__main__":
    main()
