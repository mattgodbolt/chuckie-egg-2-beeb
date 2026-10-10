#!/bin/sh
# Run baron ($BARON) with these arguments, and fail on a warning as well as
# on an error: baron has no option for that, and a warning in a build the
# checks don't look at went unnoticed.
out=$("${BARON:-baron}" "$@" 2>&1); status=$?
[ -n "$out" ] && printf '%s\n' "$out"
[ $status -eq 0 ] || exit $status
if printf '%s\n' "$out" | grep -q 'warning:'; then
    echo "$0: baron warned, so the build fails" >&2
    exit 1
fi
