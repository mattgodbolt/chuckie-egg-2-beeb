#!/usr/bin/env python3
"""Find local labels that shadow global ones.

    python3 tools/lint_labels.py

A label inside a { } scope with the same name as a top-level label hides
it for the rest of the scope: `.visits` as a loop label inside egg_init made
`LDA visits,X` read egg_init's own code. Baron doesn't warn. Exits non-zero
if any local label shares a name with a global.
"""
import glob
import re
import sys

LABEL = re.compile(r"^\s*\.([A-Za-z_][A-Za-z0-9_]*)")
ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")
ZA = re.compile(r"^\s*ZA_AUTO\w*\s+(?:\d+\s*,\s*)?([A-Za-z_][A-Za-z0-9_]*)")


def scan(path):
    """(name, depth, line) for every label and ZA_AUTO, and every assignment."""
    depth = 0
    out = []
    for n, line in enumerate(open(path, encoding="latin1"), 1):
        code = line.split("\\", 1)[0].split(";", 1)[0]
        for m in (LABEL.match(code), ZA.match(code)):
            if m:
                out.append((m.group(1), depth, n))
        m = ASSIGN.match(code)
        if m and depth == 0:
            out.append((m.group(1), 0, n))
        depth += code.count("{") - code.count("}")
    return out


def main():
    files = sorted(glob.glob("src/*.6502") + glob.glob("src/data/*.6502"))
    entries = {f: scan(f) for f in files}
    globals_ = {name for es in entries.values() for name, depth, _ in es if depth == 0}
    bad = 0
    for f, es in entries.items():
        for name, depth, n in es:
            if depth > 0 and name in globals_:
                print(f"{f}:{n}: local '{name}' shadows a global of the same name")
                bad += 1
    print(f"{bad} shadowed labels" if bad else "no shadowed labels")
    return 1 if bad else 0


sys.exit(main())
