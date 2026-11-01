#!/bin/bash
# Records which exact code content passed the tests or the review, so a later step can skip a repeat run.
#
# Usage:
#   stamp.sh hash                       Print the content hash of the working tree.
#   stamp.sh check <kind>               FRESH (exit 0) if the last <kind> run passed on this exact content,
#                                       else STALE or NONE (exit 1).
#   stamp.sh record <kind> <result>     Record the result of a <kind> run on the current content.
#
#   <kind>    tests | review
#   <result>  tests: passed | failed     review: clean | blocking
#
# The hash covers the working tree: committed, staged, unstaged, and untracked files that are not
# ignored. A temporary index computes it, so the real index stays as it is. The stamp file sits in
# the git directory of the worktree, so git never commits it and each worktree has its own.
set -euo pipefail

CMD=${1:?usage: stamp.sh hash|check <kind>|record <kind> <result>}
ROOT=$(git rev-parse --show-toplevel)
STAMP=$(git rev-parse --path-format=absolute --git-path claude-verified)

# Files that change during a run but are not code: loop state and nested worktrees.
# They are removed after `git add`, because an exclude pathspec on an ignored path makes `git add` fail.
EXCLUDES=(.dev-loop-state.json .claude/worktrees)

content_hash() {
  local tmp idx
  tmp=$(mktemp -d)
  idx=$(git rev-parse --path-format=absolute --git-path index)
  [ -f "$idx" ] && cp "$idx" "$tmp/index"
  (cd "$ROOT" && export GIT_INDEX_FILE="$tmp/index" \
     && git add -A -- . \
     && git rm -r -q --cached --ignore-unmatch -- "${EXCLUDES[@]}" >/dev/null \
     && git write-tree)
  rm -rf "$tmp"
}

pass_value() { case "$1" in tests) echo passed ;; review) echo clean ;; *) echo "unknown kind: $1" >&2; exit 2 ;; esac; }

case "$CMD" in
  hash)
    content_hash ;;
  check)
    KIND=${2:?kind}; PASS=$(pass_value "$KIND"); NOW=$(content_hash)
    LINE=$( [ -f "$STAMP" ] && grep "^$KIND " "$STAMP" || true )
    if [ -z "$LINE" ]; then echo "NONE $KIND - no recorded run"; exit 1; fi
    read -r _ HASH RESULT WHEN <<<"$LINE"
    if [ "$HASH" = "$NOW" ] && [ "$RESULT" = "$PASS" ]; then echo "FRESH $KIND $RESULT $WHEN"; exit 0; fi
    if [ "$HASH" = "$NOW" ]; then echo "STALE $KIND - last run on this content: $RESULT ($WHEN)"; exit 1; fi
    echo "STALE $KIND - the content changed since the last run ($RESULT, $WHEN)"; exit 1 ;;
  record)
    KIND=${2:?kind}; RESULT=${3:?result}; pass_value "$KIND" >/dev/null
    case "$KIND:$RESULT" in tests:passed|tests:failed|review:clean|review:blocking) ;; *) echo "bad result: $KIND $RESULT" >&2; exit 2 ;; esac
    NOW=$(content_hash); WHEN=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    { [ -f "$STAMP" ] && grep -v "^$KIND " "$STAMP" || true; echo "$KIND $NOW $RESULT $WHEN"; } > "$STAMP.tmp"
    mv "$STAMP.tmp" "$STAMP"
    echo "RECORDED $KIND $RESULT $NOW" ;;
  *)
    echo "unknown command: $CMD" >&2; exit 2 ;;
esac
