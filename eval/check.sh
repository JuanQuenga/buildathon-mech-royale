#!/usr/bin/env bash
# Release gate for one commit: native + Docker conformance (exact published sandbox flags) on the recorded
# stream and on synthetic stress streams. Fails on any missed reply, schema problem or stderr traceback.
#   eval/check.sh [commit]          (default HEAD; uses a temporary git worktree, leaves your checkout alone)
# Env: MECH_KIT=<path to mechfight-kit>, PY=<python for native run>
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
KIT="${MECH_KIT:-/home/juan/.t3/scratch/2026-11-20-you-are-the-coordinator-for-8d9ce8ed/mech-royale/starter/mechfight-kit}"
PY="${PY:-/home/juan/.t3/scratch/2026-11-20-you-are-the-coordinator-for-8d9ce8ed/venv/bin/python}"
[ -x "$PY" ] || PY=python3
REF="${1:-HEAD}"
SHA="$(git -C "$REPO" rev-parse --short=10 "$REF")" || exit 2
WORK="$(mktemp -d "${TMPDIR:-/tmp}/mechcheck.XXXXXX")"
trap 'git -C "$REPO" worktree remove --force "$WORK/src" >/dev/null 2>&1; rm -rf "$WORK"' EXIT
git -C "$REPO" worktree add -q --detach "$WORK/src" "$SHA" || exit 2
python3 "$REPO/eval/make_stress_stream.py" "$KIT/check/stream.jsonl.gz" "$WORK/streams" >/dev/null
IMG="mech-bot:$SHA"
docker build -q -t "$IMG" "$WORK/src" >/dev/null || { echo "FAIL $SHA: docker build"; exit 1; }
FLAGS=(--rm -i --network none --cpus 1 --memory 512m --memory-swap 512m --pids-limit 128 --cap-drop ALL --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "$KIT/arena:/arena:ro")
fail=0
run() {  # name, check args...
  local name="$1"; shift
  local out="$WORK/$name.out" err="$WORK/$name.err"
  python3 "$KIT/check/check.py" "$@" >"$out" 2>"$err"
  local rc=$?
  local summary; summary="$(grep -E '^(observations|answer time)' "$out" | tr '\n' ' ')"
  local tb; tb="$(grep -c Traceback "$err")"
  local miss; miss="$(sed -n 's/.*missed the 50 ms budget: \([0-9]*\).*/\1/p' "$out" | tail -1)"
  local stats; stats="$(grep '^stats ' "$err" | tail -1 | cut -c7- )"
  if [ $rc -ne 0 ] || [ "$tb" != "0" ] || [ "${miss:-1}" != "0" ]; then
    fail=1; echo "FAIL $name rc=$rc tracebacks=$tb missed=${miss:-?}"; grep -E '^(problem|warning)' "$out" | head -5; grep -A8 Traceback "$err" | head -30
  else
    echo "ok   $name  $summary"
  fi
  [ -n "$stats" ] && echo "     bot: $stats"
}
cd "$WORK/src"
run native        -- "$PY" -u bot/main.py
run docker        --map-dir /arena -- docker run "${FLAGS[@]}" "$IMG"
run docker_big    --map-dir /arena --stream "$WORK/streams/stress_big.jsonl.gz"  -- docker run "${FLAGS[@]}" "$IMG"
run docker_late   --map-dir /arena --stream "$WORK/streams/stress_late.jsonl.gz" -- docker run "${FLAGS[@]}" "$IMG"
cd "$REPO"
if [ $fail -eq 0 ]; then echo "PASS $SHA"; else echo "FAIL $SHA"; fi
exit $fail
