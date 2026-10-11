#!/usr/bin/env python3
"""Run a Spectrum logger once and keep what it wrote: the original never
changes, so its side of make passes and make entry is the same every run.

    .venv/bin/python tools/zxcache.py [--out FILE] -- COMMAND ARGS...

With --out, FILE is what COMMAND writes (passlog.py's --out); without, its
standard output. Either is kept in build/zxcache under a key made of the
command line (FILE's name aside), the sources the loggers run
(tools/zx.py, passlog.py, entrylog.py, this file), the snapshot they start
from and SkoolKit's version, so a change to any of them runs the original
again. CI keeps the
directory between runs (.github/workflows/check.yml).
"""
import hashlib
import importlib.metadata
import os
import shutil
import subprocess
import sys

CACHE = "build/zxcache"
DEPS = ["tools/zx.py", "tools/passlog.py", "tools/entrylog.py", "tools/zxcache.py", "build/ce2.z80"]


def key(command, out):
    h = hashlib.sha256()
    # (Not where the output goes: every configuration's run shares it.)
    h.update("\0".join("<out>" if arg == out else arg for arg in command).encode())
    for path in DEPS:
        h.update(b"\0" + path.encode() + b"\0")
        with open(path, "rb") as f:
            h.update(f.read())
    h.update(importlib.metadata.version("skoolkit").encode())
    return h.hexdigest()


def main():
    args = sys.argv[1:]
    out = None
    if args[:1] == ["--out"]:
        out, args = args[1], args[2:]
    if args[:1] != ["--"] or len(args) < 2:
        sys.exit(__doc__)
    command = args[1:]
    kept = os.path.join(CACHE, key(command, out))
    if os.path.exists(kept):
        if out:
            shutil.copyfile(kept, out)
        else:
            with open(kept, "rb") as f:
                sys.stdout.buffer.write(f.read())
        return
    os.makedirs(CACHE, exist_ok=True)
    if out:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        shutil.copyfile(out, kept + ".tmp")
    else:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE)
        sys.stdout.buffer.write(result.stdout)
        with open(kept + ".tmp", "wb") as f:
            f.write(result.stdout)
    os.replace(kept + ".tmp", kept)     # (whole or not at all: runs side by side share it)


if __name__ == "__main__":
    main()
