#!/bin/bash
# Switches cmux to a row of the session table that focus.py stored. Works in bash and zsh.
#
# Usage:
#   focus             Scan the sessions, print the table, and store it (runs focus.py).
#   focus <n>         Switch to row <n> of the stored table.
#   focus next        Switch to the next row that needed input, after the current workspace.
#   focus prev        Switch to the previous row that needed input, before the current workspace.
#   focus <other>     Run focus.py <other>, for example: focus items, focus pause PROJ-1 2d.
#
# Run it as a command, or source it to get the shell function "focus":
#   source ~/.claude/skills/focus/focus.sh
#
# next and prev wrap around. If the current workspace is not a row that needed input,
# next goes to the first such row and prev to the last one.

_focus_board() { printf '%s' "${FOCUS_BOARD:-$HOME/.cache/focus/board.tsv}"; }

_focus_cmux() {
  local bin="${FOCUS_CMUX:-$(command -v cmux || echo /Applications/cmux.app/Contents/Resources/bin/cmux)}"
  CMUX_QUIET=1 "$bin" "$@"
}

_focus_current() {
  if [ -n "${CMUX_WORKSPACE_ID:-}" ]; then
    printf '%s' "$CMUX_WORKSPACE_ID" | tr '[:lower:]' '[:upper:]'
  else
    _focus_cmux --json current-workspace \
      | python3 -c 'import json, sys; print(json.load(sys.stdin)["workspace"]["id"].upper())'
  fi
}

# Switch to one stored row: n, section, needs input, ref, window, id, title.
_focus_switch() {
  local n section input ref window id title
  IFS="$(printf '\t')" read -r n section input ref window id title <<EOF
$1
EOF
  _focus_cmux workspace select --workspace "$ref" --window "$window" >/dev/null || return 1
  printf -- '-> %s\n' "$title"
}

_focus_row() {
  local line
  line="$(awk -F '\t' -v n="$1" '$1 == n' "$(_focus_board)")"
  if [ -z "$line" ]; then
    echo "error: row $1 is not in the last table: run focus again" >&2
    return 1
  fi
  _focus_switch "$line"
}

_focus_step() {
  local line
  line="$(awk -F '\t' -v dir="$1" -v cur="$(_focus_current)" '
    $3 == "1" { row[++k] = $0; if (toupper($6) == cur) at = k }
    END {
      if (!k) exit 1
      if (dir == "next") i = at ? at % k + 1 : 1
      else i = at ? (at + k - 2) % k + 1 : k
      print row[i]
    }' "$(_focus_board)")" || {
    echo "Nothing needed input in the last table: run focus again"
    return 0
  }
  _focus_switch "$line"
}

focus() {
  case "${1:-}" in
    next | prev | [0-9]*)
      if [ ! -f "$(_focus_board)" ]; then
        echo "error: no table yet: run focus first" >&2
        return 1
      fi
      ;;
  esac
  case "${1:-}" in
    next | prev) _focus_step "$1" ;;
    '' | *[!0-9]*) "${FOCUS_PY:-$HOME/.claude/skills/focus/focus.py}" "$@" ;;
    *) _focus_row "$1" ;;
  esac
}

# Run as a command, not sourced: call the function.
if [ -n "${ZSH_EVAL_CONTEXT:-}" ]; then
  case "$ZSH_EVAL_CONTEXT" in *:file*) ;; *) focus "$@" ;; esac
elif [ "${BASH_SOURCE[0]:-$0}" = "$0" ]; then
  focus "$@"
fi
