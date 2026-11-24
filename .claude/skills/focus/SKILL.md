---
name: focus
description: Ranks the open cmux sessions by priority, switches cmux to one by its row number, and pings for idle work. Use for "/focus", "what should I work on", or "go to the next session".
user-invocable: true
model: haiku
allowed-tools: Bash(~/.claude/skills/focus/focus.sh *), Bash(~/.claude/skills/focus/install.sh *)
---

# Focus

Run `focus.sh` in this skill directory. The scripts do all the work. Print the output exactly as it is, with no text before it and no text after it.

The scripts are for the shell first, so they use no tokens:

- `focus.sh` switches cmux to a row of the stored table, with no Python. It sends all other commands to `focus.py`.
- `focus.py` scans the sessions, prints and stores the table, and sends the pings.

## Setup

If the user asks to set up or install focus, run `install.sh` in this skill directory. It is safe to run again, because each step skips what is already done.

```bash
~/.claude/skills/focus/install.sh [<minutes>]
```

The script does these steps:

1. Copy `data.example.json` to `data.json`, if `data.json` is missing.
2. Make `focus.py`, `focus.sh`, and `cmux-pause` executable.
3. Link `~/.local/bin/focus` to `focus.sh`, and `~/.local/bin/cmux-pause` to `cmux-pause`. If one of these paths is a different file, the script skips it and tells the user.
4. Add `source "$HOME/.claude/skills/focus/focus.sh"` to `~/.zshrc` or `~/.bashrc`, from `$SHELL`. This gives the shell function `focus`.
5. Run `focus.py daemon install [<minutes>]`. With no `<minutes>`, the daemon uses `config.daemon.everyMinutes`.

After a new `data.json`, ask the user for the board keys in priority order.

## Hard rules

- NEVER edit `data.json` by hand. Use the script only, because it keeps the pauses and the ping times.
- NEVER change the work log, the incident log, Linear, or incident.io. This skill is read-only for all of them.
- NEVER pause an item that the user did not name in this conversation. A pause hides the item, so only the user decides it.

## Commands

`$ARGUMENTS` is the command. If `$ARGUMENTS` is empty, run the script with no arguments.

```bash
~/.claude/skills/focus/focus.sh <command>
```

| Command | Use |
|---|---|
| `focus` | Print the session table of all cmux windows, and store it in `~/.cache/focus/board.tsv` |
| `focus <n>` | Switch cmux to row `<n>` of the stored table |
| `focus next` | Switch to the next row of the stored table that needed input, after the current workspace |
| `focus prev` | Switch to the previous row of the stored table that needed input, before the current workspace |
| `focus items` | Print the ranked work log items |
| `focus items --attention` | Print only the work log items that need attention and are not paused |
| `focus --ping` | Send a cmux notification for the top items that need attention. The daemon runs it |
| `focus daemon install [<min>]` | Run `--ping` every `<min>` minutes with launchd. The default is `config.daemon.everyMinutes` |
| `focus daemon uninstall` | Stop the daemon |
| `focus daemon status` | Show if the daemon is loaded |
| `focus pause <key> <duration>` | Hide one item. `<duration>` is `30m`, `4h`, `2d`, or `1w` |
| `focus resume <key>` | End a pause now |
| `focus pauses` | List the active pauses |

`<key>` is a ticket key (`PROJ-1234`) or an incident reference (`INC-123`).

If the user writes "pause X for 2 days", run `focus.py pause X 2d`.

If the script exits with an error, print the error and stop. Do not try again with other arguments.

## The session table

One row for each cmux workspace in each window. The script skips the anchor workspace that cmux makes for each group. `*` marks the current workspace.

```
  #  group     state         last  workspace
--- active
  1  incident  waiting        20m  INC-123
  2  work      waiting         3m  PROJ-1234-retry
* 3  util      running         5m  scratch
--- idle
  4  work      idle            1d  PROJ-1188-cleanup
--- paused
  5  incident  waiting         1h  INC-120  · paused: reminder at 2026-11-04 14:47 CET
```

The script sorts the rows by these keys, in this order:

1. The section: `active` (Claude is `Needs input`, `Waiting`, or `Running`), then `idle` (Claude is `Idle`, or no Claude session), then `paused`.
2. The cmux group, in `config.groups` order. A workspace in no group is `incident` if its title starts with `INC-<n>`, else `other`. `other` goes after the groups.
3. The sessions that need input (`Needs input`, `Waiting`) before the others.
4. The oldest last message first.

`focus <n>`, `next`, and `prev` read the stored table and do no new scan, so the number is the one the user saw. They use the states of the last print, so run `focus` again to update them.

- `next` and `prev` wrap around. If the current workspace is not a row that needed input, `next` goes to the first such row, and `prev` goes to the last one.
- If there is no stored table, or the row is not in it, `focus.sh` stops with an error.

## Pauses

An item is paused in four cases:

- `focus pause <key>` paused it.
- `cmux-pause` in this folder paused its workspace, for example `cmux-pause 4h` or `cmux-pause until mon 10:00`. It shows the pill `paused until 18:30` in the cmux sidebar. `install.sh` links it into `~/.local/bin`.
- Its workspace title has the word `paused`, for example `INC-123 paused`. The pause ends when the word is removed.
- A live Claude session in its workspace has a `CronCreate` reminder that has not run yet. The pause ends at the reminder's next run, or when the session exits, because the reminder dies with the session.

Paused items go last, and `items --attention`, `next`, `prev`, and `--ping` skip them.

## The work log items

`focus items` ranks by `config.tiers` in `data.json`:

1. `incident` — a cmux workspace named `INC-<n>` that is not in the incident log of `/investigate-incident`.
2. `prod-test` — a work log entry at `merged` or `dev-tested`.
3. One tier for each key in `config.boards`, in order — open work log entries whose ticket key starts with that board key.
4. `other` — all other open work log entries.

An item needs attention when one of these is true:

| Item | Condition | Threshold in `config.idle` |
|---|---|---|
| Any session | cmux shows `Needs input` or `Waiting`, and you sent nothing for this long | `waitingMinutes` |
| Incident | You sent nothing to its session for this long | `incidentHours` |
| `in-progress`, `in-review` | You sent nothing to its session for this long | `sessionDays` |
| `merged`, `dev-tested` | The next test did not happen for this long | `testWaitDays` |

## Pings

`--ping` pings the work log items that need attention, then the other sessions of the table that need input. It sends at most `config.pingMax` notifications, highest rank first. It pings an item again after `config.repingHours` until the user pauses it. When a pause ends, the item can be pinged again.

`--ping` sends nothing outside `config.daemon.activeHours` on the ISO weekdays in `config.daemon.days`.

## Daemon

`focus daemon install` writes the launchd job `~/Library/LaunchAgents/local.focus.plist` and loads it. The job runs `focus.py --ping` with no Claude session, so it uses no tokens. It writes its output to `~/Library/Logs/focus.log`.

If a `loops` job runs `/focus --ping`, remove it after you install the daemon. Two jobs send each ping two times.

## Local configuration

The script reads `data.json` in this skill directory. If it is missing, the script stops with an error. Then copy `data.example.json` to `data.json`, and ask the user for the board keys in priority order.

If `config.groups` is missing, the script uses `incident`, `work`, `util`. If `config.daemon` is missing, the script uses every 30 minutes, `09:00-19:00`, days `1-5`.

## Examples

- `/focus`
- `/focus 2`
- `/focus next`
- `/focus prev`
- `/focus items --attention`
- `/focus pause PROJ-1234 2d`
- `/focus daemon install 15`
