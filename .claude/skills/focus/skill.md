---
name: focus
description: Ranks open work sessions and incident sessions by priority, flags idle ones, and pings for them until you pause them. Use for "/focus", "what should I work on", or "what is idle".
user-invocable: true
model: haiku
allowed-tools: Bash(~/.claude/skills/focus/focus.py *)
---

# Focus

Run `focus.py` in this skill directory. The script does all the work. Print its output exactly as it is, with no text before it and no text after it.

## Hard rules

- NEVER edit `data.json` by hand. Use the script only, because it keeps the pauses and the ping times.
- NEVER change the work log, the incident log, Linear, or incident.io. This skill is read-only for all of them.
- NEVER pause an item that the user did not name in this conversation. A pause hides the item, so only the user decides it.

## Commands

`$ARGUMENTS` is the command. If `$ARGUMENTS` is empty, run the script with no arguments.

```bash
~/.claude/skills/focus/focus.py <command>
```

| Command | Use |
|---|---|
| `focus.py` | Print all open items, ranked |
| `focus.py --idle` | Print only the items that need attention and are not paused |
| `focus.py --ping` | Send a cmux notification for the top items that need attention. The loop job uses it |
| `focus.py pause <key> <duration>` | Hide one item. `<duration>` is `30m`, `4h`, `2d`, or `1w` |
| `focus.py resume <key>` | End a pause now |
| `focus.py pauses` | List the active pauses |

`<key>` is a ticket key (`PROJ-1234`) or an incident reference (`INC-123`).

If the user writes "pause X for 2 days", run `focus.py pause X 2d`.

An item is also paused, with no `/focus` command, in three cases:

- `cmux-pause` in this folder paused its workspace, for example `cmux-pause 4h` or `cmux-pause until mon 10:00`. It shows the pill `paused until 18:30` in the cmux sidebar. Link it once: `ln -s ~/.claude/skills/focus/cmux-pause ~/.local/bin/cmux-pause`.

- Its workspace title has the word `paused`, for example `INC-123 paused`. The pause ends when the word is removed.
- A live Claude session in its workspace has a `CronCreate` reminder that has not run yet. The pause ends at the reminder's next run, or when the session exits, because the reminder dies with the session.

The list shows paused items last, and `--idle` and `--ping` skip them.

If the script exits with an error, print the error and stop. Do not try again with other arguments.

## How the script ranks

The rank order comes from `config.tiers` in `data.json`:

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

`--ping` sends at most `config.pingMax` notifications, highest rank first. It pings an item again after `config.repingHours` until the user pauses it. When a pause ends, the item can be pinged again.

## Local configuration

The script reads `data.json` in this skill directory. If it is missing, the script stops with an error. Then copy `data.example.json` to `data.json`, and ask the user for the board keys in priority order.

## Loop job

The `loops` daemon runs `/focus --ping` on a schedule. The job in `loops.json`:

```json
{ "name": "focus", "every": "30m", "active_hours": "09:00-19:00", "days": "1-5", "prompt": "/focus --ping" }
```

The session of the job must allow `Skill(focus)` and `Bash(~/.claude/skills/focus/focus.py *)`.

## Examples

- `/focus`
- `/focus --idle`
- `/focus pause PROJ-1234 2d`
- `/focus resume INC-123`
