#!/bin/bash
# Runs curl requests in a Terminal.app window sized to 3/4 of the screen and saves a PNG of
# that window. Built-in tools only: osascript, screencapture, and jq if present.
#
# Usage: capture.sh --requests <file> --out <png> [--title <text>] [--headers] [--depth 1|2]
#                   [--secret NAME]...
#   --depth sets how many JSON levels of a plain curl response get one line per property
#   (default 1). Deeper values stay compact.
#   <file> starts with variable lines (CARD_ID=<uuid>), then holds one command per line: a plain
#   curl command, or a curl command piped into other tools (curl ... | jq '.data | length').
#   Commands use the variables as "$CARD_ID". Blank lines and lines starting with # are skipped.
#   A variable line is NAME=value or NAME='value', with an upper-case NAME and a literal value.
#   --secret NAME takes the value of the environment variable NAME (for example a token), so the
#   value is never in <file>. The screenshot shows it as NAME=<hidden>.
#   The screenshot shows every variable and every command in full, exactly as written in the file.
#
# The window uses its own Terminal profile ("make-curl-png"), so the user's profiles are never
# changed. If the output is taller than the window, the font shrinks step by step down to
# MIN_FONT and the saved output is redrawn - requests never run twice.
set -euo pipefail

BASE_FONT=12 MIN_FONT=8 PROFILE="make-curl-png"
REQUESTS="" OUT="" TITLE="" HEADERS=0 DEPTH=1 SECRETS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --requests) REQUESTS="$2"; shift 2 ;;
    --secret)   SECRETS+=("$2"); shift 2 ;;
    --out)      OUT="$2"; shift 2 ;;
    --title)    TITLE="$2"; shift 2 ;;
    --headers)  HEADERS=1; shift ;;
    --depth)    DEPTH="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -f "$REQUESTS" ] || { echo "requests file not found: $REQUESTS" >&2; exit 2; }
[ -n "$OUT" ] || { echo "--out is required" >&2; exit 2; }
case "$DEPTH" in 1|2) ;; *) echo "--depth must be 1 or 2" >&2; exit 2 ;; esac

# Every line is a variable line (before the first command) or a curl command, so a bad variable
# line fails here, before anything runs. The runner uses the same pattern.
VAR_RE="^([A-Z][A-Z0-9_]*)=('([^']*)'|([^\"'\$\`;&|<> ]*))\$"
seen_cmd=0
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|'#'*) continue ;; esac
  if [ "$seen_cmd" = 0 ] && [[ "$line" =~ $VAR_RE ]]; then continue; fi
  case "$line" in
    curl\ *) seen_cmd=1 ;;
    *) echo "not a curl command or a literal NAME=value line before the first command: $line" >&2; exit 2 ;;
  esac
done < "$REQUESTS"

WORK=$(mktemp -d /tmp/make-curl-png.XXXXXX)
RUN="$WORK/run.sh"
printf '%s' "$TITLE" > "$WORK/title"
printf '%s' "$DEPTH" > "$WORK/depth"

# The Terminal shell does not inherit this environment, so each secret goes to the runner in a
# file that only this user can read. The runner deletes it before the first request runs.
for name in ${SECRETS[@]+"${SECRETS[@]}"}; do
  [[ "$name" =~ ^[A-Z][A-Z0-9_]*$ ]] || { echo "--secret needs an upper-case name: $name" >&2; exit 2; }
  [ -n "${!name:-}" ] || { echo "--secret $name: the environment variable $name is empty" >&2; exit 2; }
  (umask 077; printf '%s' "${!name}" > "$WORK/secret.$name")
done
trap 'rm -f "$WORK"/secret.*' EXIT

# The script that runs inside the Terminal window. Values come from files and
# environment variables, so no request text is spliced into AppleScript.
cat > "$RUN" <<'RUNNER'
#!/bin/bash
W="$1" REQUESTS="$2" HEADERS="$3"; TITLE=$(cat "$W/title"); DEPTH=$(cat "$W/depth")
clear; tput civis
B=$'\033[1m' G=$'\033[32m' R=$'\033[31m' D=$'\033[2m' N=$'\033[0m'
STAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')

# Prints the position of the first "|" outside quotes, or nothing. "||" is not a pipe.
pipe_at() {
  local s=$1 q="" i c
  for (( i = 0; i < ${#s}; i++ )); do
    c=${s:i:1}
    if [ -n "$q" ]; then [ "$c" = "$q" ] && q=""; continue; fi
    case "$c" in
      \'|\") q=$c ;;
      '|') [ "${s:i+1:1}" = '|' ] && { i=$((i + 1)); continue; }; echo "$i"; return ;;
    esac
  done
}

# Exports each secret, deletes its file, and records its name for the screenshot.
: > "$W/vars"
for f in "$W"/secret.*; do
  [ -e "$f" ] || continue
  name=${f##*/secret.}; export "$name=$(cat "$f")"; rm -f "$f"
  printf '%s=<hidden>\n' "$name" >> "$W/vars"
done

# Runs every request once and saves its command, body, headers, errors and timing.
# Variable lines before the first command are exported and shown at the top of the screenshot.
# For "curl ... | rest", curl writes the body to a file (so the status and time are known),
# then the same bytes go into "rest" - the output is what the full command prints.
VAR_RE="^([A-Z][A-Z0-9_]*)=('([^']*)'|([^\"'\$\`;&|<> ]*))\$"
run_all() {
  n=0
  while IFS= read -r cmd || [ -n "$cmd" ]; do
    case "$cmd" in ''|'#'*) continue ;; esac
    if [ "$n" = 0 ] && [[ "$cmd" =~ $VAR_RE ]]; then
      export "${BASH_REMATCH[1]}=${BASH_REMATCH[3]}${BASH_REMATCH[4]}"
      printf '%s\n' "$cmd" >> "$W/vars"
      continue
    fi
    n=$((n + 1))
    printf '%s' "$cmd" > "$W/cmd.$n"
    at=$(pipe_at "$cmd")
    curl_part=${cmd:0:${at:-${#cmd}}}
    eval "$curl_part -sS -o '$W/body.$n' -D '$W/hdrs.$n' -w '%{http_code} %{time_total}'" \
      > "$W/meta.$n" 2> "$W/err.$n" || true
    if [ -n "$at" ]; then
      eval "cat '$W/body.$n' | ${cmd:at+1}" > "$W/piped.$n" 2>> "$W/err.$n" || true
    fi
  done < "$REQUESTS"
  echo "$n" > "$W/count"
}

# Puts each property (or array element) of the first $depth levels on its own line and keeps
# every deeper value compact, so a deep response stays short and the levels that matter stay readable.
LAYOUT='def lay($d; $ind):
    if $d > 0 and type == "object" and length > 0 then
      "{\n" + (to_entries | map($ind + "  " + (.key | tojson) + ": " + (.value | lay($d - 1; $ind + "  "))) | join(",\n")) + "\n" + $ind + "}"
    elif $d > 0 and type == "array" and length > 0 then
      "[\n" + (map($ind + "  " + lay($d - 1; $ind + "  ")) | join(",\n")) + "\n" + $ind + "]"
    else tojson end;
  lay($depth; "")'
K=$'\033[34;1m'

# Prints the saved results. The command line is always the full command, as written.
# A piped command shows its own output unchanged. A plain curl command shows the body:
# mode "depthN" lays JSON out N levels deep; mode "raw" prints it as the server sent it.
render() {
  mode=$1
  [ -n "$TITLE" ] && printf '%s%s%s  %s%s%s\n\n' "$B" "$TITLE" "$N" "$D" "$STAMP" "$N"
  if [ -s "$W/vars" ]; then
    while IFS= read -r v; do printf '%s$ %s%s\n' "$G" "$v" "$N"; done < "$W/vars"
    echo
  fi
  for i in $(seq 1 "$(cat "$W/count")"); do
    printf '%s$ %s%s\n' "$G" "$(cat "$W/cmd.$i")" "$N"
    [ -s "$W/err.$i" ] && printf '%s%s%s\n' "$R" "$(cat "$W/err.$i")" "$N"
    [ "$HEADERS" = 1 ] && [ -s "$W/hdrs.$i" ] && tr -d '\r' < "$W/hdrs.$i"
    if [ -f "$W/piped.$i" ]; then
      [ -s "$W/piped.$i" ] && { cat "$W/piped.$i"; [ -n "$(tail -c 1 "$W/piped.$i")" ] && echo; }
    elif [ -s "$W/body.$i" ]; then
      if command -v jq >/dev/null && jq -e . "$W/body.$i" >/dev/null 2>&1 && [ "$mode" != raw ]; then
        jq -r --argjson depth "${mode#depth}" "$LAYOUT" "$W/body.$i" \
          | sed -E 's/^( +)("[^"]*")(:)/\1'"$K"'\2'"$N"'\3/'
      else
        cat "$W/body.$i"; [ -n "$(tail -c 1 "$W/body.$i")" ] && echo
      fi
    fi
    meta=$(cat "$W/meta.$i"); code=${meta%% *}
    ms=$(awk -v s="${meta##* }" 'BEGIN { printf "%.0f", s * 1000 }')
    color=$G; case "$code" in [45]*|000) color=$R ;; esac
    printf '%sHTTP %s%s %s- %s ms%s\n\n' "$color$B" "$code" "$N" "$D" "$ms" "$N"
  done
}

# Clears the screen and the scrollback: with nothing to scroll, Terminal shows no scroll bar.
wipe() { printf '\033[H\033[2J\033[3J'; }

run_all
# Render every layout once, so the caller can pick one without a round trip per layout.
for m in depth2 depth1 raw; do render "$m" > "$W/out.$m"; done
cp "$W/out.depth$DEPTH" "$W/out"; wipe; cat "$W/out"
# Report the real window size ("rows cols") all the time: Terminal's AppleScript keeps
# reporting the old rows and columns after a font change, the terminal itself does not.
stty size > "$W/size"
touch "$W/done"
while [ ! -f "$W/release" ]; do
  if [ -f "$W/redraw" ]; then
    mode=$(cat "$W/redraw"); rm "$W/redraw"
    cp "$W/out.$mode" "$W/out"; wipe; cat "$W/out"; touch "$W/redrawn"
  fi
  stty size > "$W/size.new" && mv "$W/size.new" "$W/size"
  sleep 0.05
done
tput cnorm
RUNNER
chmod +x "$RUN"

# Three quarters of the main screen's visible width and height, as AppleScript bounds (top-left origin).
BOUNDS=$(osascript -l JavaScript -e '
ObjC.import("AppKit");
const s = $.NSScreen.mainScreen, f = s.frame, v = s.visibleFrame;
const left = v.origin.x, top = f.size.height - (v.origin.y + v.size.height);
const w = Math.floor(v.size.width * 0.75), h = Math.floor(v.size.height * 0.75);
[left, top, left + w, top + h].map(Math.round).join(",");')

# AppleScript lives in files: bash misparses a heredoc with an apostrophe inside $( ).
cat > "$WORK/launch.applescript" <<'APPLESCRIPT'
on run argv
  set launchCmd to item 1 of argv
  set AppleScript's text item delimiters to ","
  set b to text items of item 2 of argv
  set profileName to item 3 of argv
  set fontSize to (item 4 of argv) as integer
  set windowTitle to item 5 of argv
  tell application "Terminal"
    if not (exists settings set profileName) then
      make new settings set with properties {name:profileName}
    end if
    set p to settings set profileName
    set font name of p to "Menlo"
    set font size of p to fontSize
    set background color of p to {7710, 7710, 7710}
    set normal text color of p to {58000, 58000, 58000}
    set bold text color of p to {65535, 65535, 65535}
    set cursor color of p to {7710, 7710, 7710}
    set title displays custom title of p to true
    set title displays shell path of p to false
    set title displays window size of p to false
    set title displays device name of p to false
    set title displays settings name of p to false
  end tell
  -- Remember what the user is working in, so focus can go back to it.
  set prevApp to path to frontmost application as text
  set prevWin to missing value
  tell application "Terminal"
    if frontmost and (count of windows) > 0 then set prevWin to id of front window
    set t to do script launchCmd
    set current settings of t to p
    set custom title of t to windowTitle
    delay 0.2
    set w to front window
    set bounds of w to {(item 1 of b) as integer, (item 2 of b) as integer, (item 3 of b) as integer, (item 4 of b) as integer}
    set wid to id of w
    -- Put the user's Terminal window back in front; the capture window works from behind it.
    if prevWin is not missing value then set index of window id prevWin to 1
  end tell
  tell application prevApp to activate
  return wid
end run
APPLESCRIPT

# Sets the profile font size, restores the window bounds, and prints "rows cols".
# An open tab ignores a font change on the profile it already uses, so each step sets the
# font on the other of two identical profiles ("<profile>" and "<profile>-alt") and switches
# the tab to it. Terminal's AppleScript rows/columns stay stale - the runner reports the real size.
cat > "$WORK/fit.applescript" <<'APPLESCRIPT'
on run argv
  set wid to (item 1 of argv) as integer
  set AppleScript's text item delimiters to ","
  set b to text items of item 2 of argv
  set profileName to item 3 of argv
  set fontSize to (item 4 of argv) as integer
  tell application "Terminal"
    set w to window id wid
    set t to selected tab of w
    set target to profileName
    if name of current settings of t is profileName then set target to profileName & "-alt"
    if not (exists settings set target) then make new settings set with properties {name:target}
    set p to settings set target
    set font name of p to "Menlo"
    set font size of p to fontSize
    set background color of p to {7710, 7710, 7710}
    set normal text color of p to {58000, 58000, 58000}
    set bold text color of p to {65535, 65535, 65535}
    set cursor color of p to {7710, 7710, 7710}
    set title displays custom title of p to true
    set title displays shell path of p to false
    set title displays window size of p to false
    set title displays device name of p to false
    set title displays settings name of p to false
    set current settings of t to p
    delay 0.1
    set bounds of w to {(item 1 of b) as integer, (item 2 of b) as integer, (item 3 of b) as integer, (item 4 of b) as integer}
  end tell
end run
APPLESCRIPT

LAUNCH="clear; bash '$RUN' '$WORK' '$REQUESTS' '$HEADERS'; exit"
WID=$(osascript "$WORK/launch.applescript" "$LAUNCH" "$BOUNDS" "$PROFILE" "$BASE_FONT" "${TITLE:-curl verification}")

for _ in $(seq 1 1200); do [ -f "$WORK/done" ] && break; sleep 0.05; done
[ -f "$WORK/done" ] || { echo "timed out waiting for the requests to finish (window $WID)" >&2; touch "$WORK/release"; exit 1; }

# Lines a layout needs at a given width, after wrapping. +1 keeps the last line off the edge.
needed() { sed $'s/\033\\[[0-9;]*m//g' "$WORK/out.$1" | fold -w "$2" | wc -l | awk '{ print $1 + 1 }'; }
fits() { [ "$(needed "$1" "$cols")" -le "$rows" ]; }

# Changes the font, then waits until the window reports its new real size (see the runner).
set_font() {
  local before; before=$(cat "$WORK/size")
  osascript "$WORK/fit.applescript" "$WID" "$BOUNDS" "$PROFILE" "$1" >/dev/null
  font=$1
  for _ in $(seq 1 40); do [ "$(cat "$WORK/size")" != "$before" ] && break; sleep 0.05; done
  read -r rows cols < "$WORK/size"
}
redraw() {
  rm -f "$WORK/redrawn"; echo "$1" > "$WORK/redraw"
  for _ in $(seq 1 40); do [ -f "$WORK/redrawn" ] && break; sleep 0.05; done
}

# Pick the layout and font from the size at BASE_FONT, without trying each one: the window
# holds about rows*BASE/f lines and cols*BASE/f columns at font f. Layouts in order of
# preference: depth 2 (if asked), depth 1, raw - each with the largest font that fits.
read -r rows cols < "$WORK/size"
base_rows=$rows base_cols=$cols
MODE="raw" font=$MIN_FONT
modes="depth1 raw"; [ "$DEPTH" = 2 ] && modes="depth2 depth1 raw"
for m in $modes; do
  for (( f = BASE_FONT; f >= MIN_FONT; f-- )); do
    if [ "$(needed "$m" $(( base_cols * BASE_FONT / f )))" -le $(( base_rows * BASE_FONT / f )) ]; then
      MODE=$m font=$f; break 2
    fi
  done
done
[ "$MODE" != "depth$DEPTH" ] && redraw "$MODE"
if [ "$font" -lt "$BASE_FONT" ]; then
  # The estimate is close, not exact: step down while the real size still does not fit.
  set_font "$font"
  while ! fits "$MODE" && [ "$font" -gt "$MIN_FONT" ]; do set_font $((font - 1)); done
  redraw "$MODE" # rewrap at the new width
fi
sleep 0.3 # let Terminal paint the last lines

mkdir -p "$(dirname "$OUT")"
screencapture -x -o -l "$WID" "$OUT"
touch "$WORK/release"
sleep 0.1
osascript -e "tell application \"Terminal\" to close (every window whose id is $WID)" >/dev/null 2>&1 || true

[ -s "$OUT" ] || { echo "screencapture wrote nothing - check Screen Recording permission" >&2; exit 1; }

# Crop the title bar: it shows the shell's working directory and the launch command, and
# Terminal's AppleScript cannot hide those. The height comes from this macOS version.
TITLEBAR_PT=$(osascript -l JavaScript -e '
ObjC.import("AppKit");
const m = $.NSWindowStyleMaskTitled | $.NSWindowStyleMaskClosable | $.NSWindowStyleMaskMiniaturizable | $.NSWindowStyleMaskResizable;
$.NSWindow.frameRectForContentRectStyleMask($.NSMakeRect(0, 0, 800, 600), m).size.height - 600;')
png_w=$(sips -g pixelWidth "$OUT" | awk '/pixelWidth/ { print $2 }')
png_h=$(sips -g pixelHeight "$OUT" | awk '/pixelHeight/ { print $2 }')
IFS=, read -r x1 _ x2 _ <<< "$BOUNDS"
crop=$(awk -v t="$TITLEBAR_PT" -v pw="$png_w" -v ww="$((x2 - x1))" 'BEGIN { printf "%.0f", t * pw / ww }')
# One pixel short of the bottom edge: sips ignores a crop box that ends exactly on it.
sips --cropOffset "$crop" 0 -c "$((png_h - crop - 1))" "$png_w" "$OUT" --out "$OUT" >/dev/null

lines=$(needed "$MODE" "$cols")
[ "$MODE" = raw ] && echo "NOTE: the formatted response did not fit, so the body is shown without jq formatting" >&2
[ "$MODE" = depth1 ] && [ "$DEPTH" = 2 ] && echo "NOTE: the depth-2 layout did not fit, so the body is laid out one level deep" >&2
if [ "$lines" -gt "$rows" ]; then
  echo "WARNING: output is $lines lines but the window shows $rows at ${font}pt - the top is cut off" >&2
elif [ "$font" -lt "$BASE_FONT" ]; then
  echo "NOTE: font reduced to ${font}pt to fit $lines lines" >&2
fi
echo "$OUT"
