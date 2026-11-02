---
name: work-log
description: Keeps the work log of tickets and incidents in SQLite — reconciles branches with GitHub, lists open work, adds and updates items and branches, and prints JSON for other skills. Use for "/work-log", "what work is open", or when another skill records a branch, a PR, or an incident.
user-invocable: true
model: haiku
context: fork
allowed-tools: Bash(~/.claude/skills/work-log/worklog.py *)
---

# Work Log

Run `worklog.py` in this skill directory. The script does all the work. Print its output exactly as it is, with no text before it and no text after it.

## Hard rules

- NEVER open `~/.claude/work-log/worklog.db` with another tool. Use the script only, because it checks the state machines and keeps the schema private.
- NEVER use `--force` unless the caller wrote that the user asked for the forced move in this conversation.

## Model

| Part | Meaning |
|---|---|
| Item | One piece of work: a `ticket` or an `incident`. Its `key` is unique, for example `PROJ-1234` or `INC-123`. |
| Branch | A branch and its PR. A branch belongs to one item. All types use the same branch states. |
| Transition | One status change of an item or a branch, with its `enteredAt` time. The durations come from the transitions. |

`worklog.py types` prints the state machine of each type and of the branches. A status change must be an edge of its machine, else the script exits 1 and names the allowed next states. A ticket item is automatic: it is `done` when all its branches are `prod-tested` or `abandoned`, else `open`. An incident needs `summary` and `resolution` before `resolved`.

## Commands

`$ARGUMENTS` is the command. If `$ARGUMENTS` is empty, the command is `status`. Run:

```bash
~/.claude/skills/work-log/worklog.py <command>
```

| Command | Use |
|---|---|
| `status` | Reconcile with GitHub, then print open work, the work that waits for a dev or prod test, and the open incidents |
| `show <key>` | Print one item as JSON, with its branches, transitions, and durations |
| `list [--type T] [--key K] [--search TEXT] [--branch B] [--session-id ID] [--open] [--status S]` | Print the matching items as JSON. `--search` matches the title and the field values |
| `types` | Print the state machines as JSON |
| `add --ticket <K> --title "<title>" --branch <B> --session <S> --session-id <id> [--worktree <path>]` | Add a branch when it is created. `--key` is the same as `--ticket`. The branch attaches to the item with that key, else to a new ticket |
| `update --branch <B> [--pr <url>] [--status <status>] [--worktree <path>] [--session-id <id>] [--set K=V] [--force]` | Change a branch |
| `merged --branch <B>` | Read the PR state of one branch, set `merged` or `abandoned`, and print `yes`, `no`, or `closed` |
| `item add --type <T> --key <K> --title "<title>" [--set K=V]` | Add an item, for example an incident |
| `item update --key <K> [--title "<title>"] [--status <status>] [--set K=V] [--force]` | Change an item |
| `lock --branch <B>` | Set `sweepLockedAt`. Exit 1 if another run set it less than 2 hours ago |
| `unlock --branch <B>` | Clear `sweepLockedAt` |

`--set K=V` stores a field, for example `--set summary="..."`. An empty `V` removes the field. `--session-id` also stores `sessionCwd`, the folder that owns the session. The script finds it from the session file.

Finished items stay in the log. `status` does not show them.

If the script exits with an error, print the error and stop. Do not try again with other arguments.

## Examples

- `/work-log`
- `/work-log show PROJ-1234`
- `/work-log update --branch feat/PROJ-1234-add-pagination --pr https://github.com/acme/api/pull/42 --status in-review`
- `/work-log item add --type incident --key INC-123 --title "Checkout errors"`
- `/work-log item update --key INC-123 --status resolved --set summary="..." --set resolution="..."`
