#!/bin/bash
# One lock per repo, shared by every checkout and worktree of it, because they share host ports.
# A session holds the lock while it tests; other sessions wait or, on the user's order, take over.
#
# Usage: lock.sh <acquire|release|status|takeover> <repo-name> [purpose]
# Exit:  0 acquired / released / free   3 held by another live session   4 not the owner
set -uo pipefail

ACTION=${1:?action}; REPO=${2:?repo name}; PURPOSE=${3:-}
DIR=${DOCKER_TEST_LOCK_DIR:-$HOME/.claude/locks/docker-test}
F="$DIR/$REPO.lock"
mkdir -p "$DIR"

# The Claude Code session that runs this script. PPID is the claude process when
# CLAUDE_PID is not set; its liveness tells whether a lock is stale.
SID=${CLAUDE_CODE_SESSION_ID:-unknown}
PID=${CLAUDE_PID:-$PPID}

field() { sed -n "s/^$1=//p" "$F" 2>/dev/null; }
owned() { [ "$(field session)" = "$SID" ]; }
alive() { local p; p=$(field pid); [ -n "$p" ] && kill -0 "$p" 2>/dev/null; }
claim() {
  # noclobber makes the create atomic: two sessions cannot both succeed.
  ( set -C; printf 'session=%s\npid=%s\ncheckout=%s\npurpose=%s\nsince=%s\n' \
      "$SID" "$PID" "$(pwd)" "$PURPOSE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$F" ) 2>/dev/null
}

case "$ACTION" in
  acquire)
    if claim; then echo "ACQUIRED"; exit 0; fi
    if owned; then echo "ACQUIRED (already held by this session)"; exit 0; fi
    if ! alive; then
      echo "STALE - the holder's session has ended; replacing:"; cat "$F"
      rm -f "$F"; claim && { echo "ACQUIRED"; exit 0; }
    fi
    echo "HELD"; cat "$F"; exit 3 ;;
  release)
    [ -f "$F" ] || { echo "FREE"; exit 0; }
    if owned; then rm -f "$F"; echo "RELEASED"; exit 0; fi
    echo "NOT_OWNER"; cat "$F"; exit 4 ;;
  status)
    if [ -f "$F" ]; then alive && echo "HELD" || echo "STALE"; cat "$F"; else echo "FREE"; fi ;;
  takeover)
    [ -f "$F" ] && { echo "TAKING OVER from:"; cat "$F"; }
    rm -f "$F"; claim && echo "ACQUIRED" ;;
  *) echo "unknown action: $ACTION" >&2; exit 2 ;;
esac
