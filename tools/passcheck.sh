#!/bin/sh
# Replay every scenario in tests/scenarios.txt on the original and the port
# and compare them pass by pass. Exits non-zero if any differs.
cd "$(dirname "$0")/.."
fail=0
grep -v '^#' tests/scenarios.txt | grep -v '^[[:space:]]*$' | while IFS='|' read -r name inputs passes start flags; do
    name=$(echo $name); inputs=$(echo $inputs); passes=$(echo $passes); start=$(echo $start)
    set -- ${start:+--start "$start"} $flags
    .venv/bin/python tools/passlog.py "$inputs" "$passes" --out "build/zx_$name.json" "$@" > /dev/null || exit 1
    node tools/passlog.mjs "$inputs" "$passes" --out "build/bbc_$name.json" "$@" > /dev/null || exit 1
    if result=$(python3 tools/passcmp.py "build/zx_$name.json" "build/bbc_$name.json"); then
        echo "$name: $result"
    else
        echo "$name: DIFFERS"; echo "$result"; exit 1
    fi
done
