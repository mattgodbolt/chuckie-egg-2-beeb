#!/bin/sh
# Replay every scenario in tests/scenarios.txt on the original and the port
# and compare them pass by pass. Exits non-zero if any differs.
#
# The scenarios are independent, so they run side by side, JOBS at a time
# (default: the number of CPUs); the results are printed in the file's
# order. `tools/passcheck.sh --one N` runs the Nth scenario alone. The
# logs go in PASSDIR (the Makefile's: one per edition and model, so
# configurations can run side by side).
cd "$(dirname "$0")/.."
out=${PASSDIR:-build/passcheck}
export PASSDIR="$out"
scenarios() { grep -v '^#' tests/scenarios.txt | grep -v '^[[:space:]]*$'; }

if [ "$1" = "--one" ]; then
    scenarios | sed -n "$2p" | while IFS='|' read -r name inputs passes start flags; do
        name=$(echo $name); inputs=$(echo $inputs); passes=$(echo $passes); start=$(echo $start)
        set -- ${start:+--start "$start"} $flags
        # (The original's side, kept between runs: tools/zxcache.py.)
        .venv/bin/python tools/zxcache.py --out "$out/zx_$name.json" -- \
            .venv/bin/python tools/passlog.py "$inputs" "$passes" --out "$out/zx_$name.json" "$@" > /dev/null || exit 1
        node tools/passlog.mjs "$inputs" "$passes" --out "$out/bbc_$name.json" "$@" > /dev/null || exit 1
        if result=$(python3 tools/passcmp.py "$out/zx_$name.json" "$out/bbc_$name.json"); then
            echo "$name: $result"
        else
            echo "$name: DIFFERS"; echo "$result"; exit 1
        fi
    done
    exit $?
fi

rm -rf "$out" && mkdir -p "$out"
n=$(scenarios | wc -l)
seq "$n" | xargs -P "${JOBS:-$(nproc)}" -I{} sh -c \
    'tools/passcheck.sh --one {} > "$PASSDIR/{}.txt" 2>&1 || touch "$PASSDIR/{}.failed"'
fail=0
for i in $(seq "$n"); do
    cat "$out/$i.txt"
    [ -e "$out/$i.failed" ] && fail=1
done
exit $fail
