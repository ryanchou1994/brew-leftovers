#!/usr/bin/env bash
# Runs every suite against ../brew-leftovers (or $BREW_LEFTOVERS_BIN). Only mktemp directories are touched;
# `brew` and `lsof` are mocked, so this never looks at the real Homebrew installation.
# Each suite ends with "RESULT <name> ran=N bad=M xfail=K"; the run passes when every bad= is 0.
set -u
cd "$(dirname "$0")" || exit 2
export BREW_LEFTOVERS_BIN="${BREW_LEFTOVERS_BIN:-$(cd .. && pwd)/brew-leftovers}"
[ -f "$BREW_LEFTOVERS_BIN" ] || { echo "no script at $BREW_LEFTOVERS_BIN" >&2; exit 2; }
if ! command -v timeout >/dev/null 2>&1 && ! command -v gtimeout >/dev/null 2>&1; then
  echo "note: no timeout/gtimeout on PATH; install coreutils first. Without it the tool treats the missing time limit as a warning, so most verdicts collapse to unverified and 13 cases (the two timeout cases R20/R20b plus 11 removable/keep cases) are reported as failures." >&2
fi
fail=0
for s in r1/harness.py r2/script_harness.py r2/script_extra.py holdout/holdout.py; do
  echo "=== $s"
  if [ -n "${VERBOSE:-}" ]; then python3 "$s"; else python3 "$s" | grep -E '^(### |    \[(FAIL|XPASS)\]|RESULT )'; fi
  rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || fail=1
done
echo "=== overall: $([ "$fail" -eq 0 ] && echo PASS || echo FAIL)"
exit "$fail"
