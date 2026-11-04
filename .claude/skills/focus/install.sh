#!/bin/bash
# Sets up focus once. You can run it again: each step skips what is already done.
#
# Usage: install.sh [<minutes>]
#   <minutes>  How often the daemon runs focus --ping. Default: config.daemon.everyMinutes.
#
# Steps:
#   1. Make data.json from data.example.json, if it is missing.
#   2. Make the scripts executable.
#   3. Link focus and cmux-pause into ~/.local/bin.
#   4. Add "source .../focus.sh" to the rc file of your login shell, for the shell function focus.
#   5. Install the launchd daemon (focus daemon install).
set -euo pipefail

SKILL="$HOME/.claude/skills/focus"
BIN="$HOME/.local/bin"

if [ ! -d "$SKILL" ]; then
  echo "error: $SKILL is missing. Link the skill there first." >&2
  exit 1
fi

new_config=0
if [ ! -f "$SKILL/data.json" ]; then
  cp "$SKILL/data.example.json" "$SKILL/data.json"
  chmod 600 "$SKILL/data.json"
  new_config=1
  echo "made data.json from data.example.json"
fi

chmod +x "$SKILL/focus.py" "$SKILL/focus.sh" "$SKILL/cmux-pause"

mkdir -p "$BIN"
link() {
  local name="$1" target="$SKILL/$2" path="$BIN/$1"
  if [ -L "$path" ] && [ "$(realpath "$path")" = "$(realpath "$target")" ]; then
    echo "ok: $path"
  elif [ -e "$path" ] || [ -L "$path" ]; then
    echo "skipped: $path exists and is not a link to $target. Remove it and run again."
  else
    ln -s "$target" "$path"
    echo "linked $path"
  fi
}
link focus focus.sh
link cmux-pause cmux-pause
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "warning: $BIN is not in PATH. Add it, or the commands focus and cmux-pause are not found." ;;
esac

case "$(basename "${SHELL:-}")" in
  zsh) rc="$HOME/.zshrc" ;;
  bash) rc="$HOME/.bashrc" ;;
  *) rc="" ;;
esac
line='source "$HOME/.claude/skills/focus/focus.sh"'
if [ -z "$rc" ]; then
  echo "skipped: unknown shell ${SHELL:-}. Add this line to your rc file: $line"
elif grep -qF "$line" "$rc" 2>/dev/null; then
  echo "ok: $rc sources focus.sh"
else
  printf '\n# focus: the shell function for the cmux session table\n%s\n' "$line" >>"$rc"
  echo "added focus.sh to $rc. Open a new shell, or run: $line"
fi

"$SKILL/focus.py" daemon install "$@"

if [ "$new_config" = 1 ]; then
  echo "next: set config.boards and config.tiers in $SKILL/data.json to your tracker team keys."
fi
echo "next: if a loops job runs /focus --ping, remove it. Two jobs send each ping two times."
