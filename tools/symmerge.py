#!/usr/bin/env python3
"""Join two of baron's --symbols files (format 2) into one.

    python3 tools/symmerge.py out.json a.json b.json

The streaming edition's discs are two assemblies (docs/streaming.md):
MENU's and the release files', then CE2S's. The tools look names up in
one file (tools/beeb.mjs's loadSymbols, where a later assembly's name
wins), so b's game symbols, listed last, are the ones they find.
"""
import json
import sys

out, *paths = sys.argv[1:]
files = [json.load(open(p)) for p in paths]
assert all(f["format"] == 2 for f in files)
json.dump({"format": 2, "assemblies": [a for f in files for a in f["assemblies"]]}, open(out, "w"))
