---
name: work-log
description: Keeps the work log of /implement-ticket — reconciles entries with GitHub, lists open work, and adds or updates entries. Use for "/work-log", "what work is open", or when another skill records a branch or a PR.
user-invocable: true
model: haiku
context: fork
allowed-tools: Bash(~/.claude/skills/work-log/worklog.py *)
---

# Work Log

Run `worklog.py` in this skill directory. The script does all the work. Print its output exactly as it is, with no text before it and no text after it.

## Hard rules

- NEVER edit `data.json` by hand. Use the script only, because it keeps the fields of other skills.
- NEVER run `clean --confirmed` unless the caller wrote that the user asked for the clean in this conversation.

## Commands

`$ARGUMENTS` is the command. If `$ARGUMENTS` is empty, the command is `status`. Run:

```bash
~/.claude/skills/work-log/worklog.py <command>
```

| Command | Use |
|---|---|
| `worklog.py status` | Reconcile with GitHub, move entries finished over 30 days ago to `readyToDelete`, print open work and the work that waits for a dev or prod test |
| `worklog.py show <ticket>` | Print the entries of one ticket as JSON |
| `worklog.py add --ticket <T> --title "<title>" --branch <B> --session <S> --session-id <id> [--worktree <path>]` | Add an entry when a branch is created |
| `worklog.py update --branch <B> [--pr <url>] [--status <status>] [--worktree <path>] [--session-id <id>]` | Change an entry |
| `worklog.py merged --branch <B>` | Read the PR state of one entry, set `merged` or `abandoned`, and print `yes`, `no`, or `closed` |
| `worklog.py clean --confirmed` | Empty `readyToDelete` |

`<status>` is one of `in-progress`, `in-review`, `merged`, `dev-tested`, `prod-tested`, or `abandoned`. An entry is finished only at `prod-tested` or `abandoned`. When `update` sets `merged`, `dev-tested`, or `prod-tested`, the script sets `mergedAt`, `devTestedAt`, or `prodTestedAt` to today if that date is empty.

`--session-id` also stores `sessionCwd`, the folder that owns the session. The script finds it from the session file.

If the script exits with an error, print the error and stop. Do not try again with other arguments.

## Examples

- `/work-log`
- `/work-log show PROJ-1234`
- `/work-log update --branch feat/PROJ-1234-add-pagination --pr https://github.com/acme/api/pull/42 --status in-review`
