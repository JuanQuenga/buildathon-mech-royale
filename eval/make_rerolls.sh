#!/usr/bin/env bash
# Mass-produce gated re-roll tags of one policy (qualification insurance: each is an independent official draw).
#   eval/make_rerolls.sh <policy-profile> <first-n> <last-n> [tag-prefix=good-r] [parallel=3]
# For n in first..last: branch var/R<n> = main with DEFAULT_PROFILE="<policy>+r<n>x", full gate (eval/check.sh),
# annotated tag <prefix><n> only if the gate passes, then push branch + tag. Never overwrites an existing tag.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
POL="$1"; A="$2"; B="$3"; PFX="${4:-good-r}"; PAR="${5:-3}"
WORK="${TMPDIR:-/tmp}/rerolls"; mkdir -p "$WORK"
one() {
  local n="$1" br="var/R$1" tag="$PFX$1" prof="$POL+r$1x"
  git -C "$REPO" rev-parse -q --verify "refs/tags/$tag" >/dev/null && { echo "skip $tag (exists)"; return; }
  local d="$WORK/wt-$n"; rm -rf "$d"
  git -C "$REPO" worktree add -q -B "$br" "$d" main || return
  sed -i "s/^DEFAULT_PROFILE = .*/DEFAULT_PROFILE = \"$prof\"/" "$d/bot/brain.py"
  git -C "$d" commit -q -am "re-roll $n of $POL (behaviour-neutral scan phase r${n}x)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  local sha; sha="$(git -C "$d" rev-parse --short HEAD)"
  git -C "$REPO" worktree remove --force "$d"
  if nice -n 10 "$REPO/eval/check.sh" "$br" > "$WORK/gate-$n.log" 2>&1; then
    git -C "$REPO" tag -a "$tag" "$br" -m "re-roll $n of $POL (r${n}x)" && git -C "$REPO" push -q origin "$br" "$tag" && echo "PASS $tag $sha"
  else
    echo "FAIL $tag $sha (see $WORK/gate-$n.log)"
  fi
}
export -f one; export REPO POL PFX WORK
seq "$A" "$B" | xargs -P "$PAR" -I{} bash -c 'one {}'
