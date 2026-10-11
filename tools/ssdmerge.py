#!/usr/bin/env python3
"""Add the files of one Acorn DFS disc image to another's.

    python3 tools/ssdmerge.py out.ssd base.ssd extra.ssd

The two editions are two assemblies of src/main.6502 (docs/streaming.md):
the release disc's (MENU, CE2, CE2DATA, !BOOT) and the streaming
edition's (CE2S). This puts CE2S on the release disc, after its last file,
and writes the result. A name on both discs is an error.

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


def main():
    out, base_path, extra_path = sys.argv[1:4]
    base = bytearray(open(base_path, "rb").read())
    extra = open(extra_path, "rb").read()
    have = catalogue(base)
    sectors = base[SECTOR + 7] | (base[SECTOR + 6] & 3) << 8
    names = {name for name, *_ in have}
    end = max([start + (length + SECTOR - 1) // SECTOR for _, _, length, start in have] + [2])
    added = []
    for name, info, length, start in reversed(catalogue(extra)):
        if name in names:
            raise SystemExit(f"{bytes(name).decode().strip()}: on both discs")
        size = (length + SECTOR - 1) // SECTOR
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
