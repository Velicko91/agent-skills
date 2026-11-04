# Work log in SQLite — Design Alignment

## Problem
Move the `/work-log` skill from `data.json` to SQLite, and make it expandable to more types of work. The first two types are ticket work and incident investigation, each with its own states. At the end of an incident, the log holds a summary and a resolution. Ticket work comes first. The incident type is built now, but `/investigate-incident` writes to the log in a later change.

## Decisions
| # | Dimension | Decision | Why | Consequence |
|---|-----------|----------|-----|-------------|
| 1 | Data model | One `items` table with common columns (type, key, title, status, timestamps) and a JSON `data` column for the fields of each type. Python validates the fields of each type. | A new type needs no schema change. The current script already keeps fields that other skills add (`sweepLockedAt`). | SQLite does not check the shape of `data`. Only the script validates it. |
| 2 | Unit of work | One item for each ticket or incident. Branches and PRs are child rows, and these child rows are the same for all types. | An incident and its fix PRs show as one piece of work. The ticket status no longer comes from a set of branch rows. | Branch statuses move to the child rows. The item has its own status. |
| 3 | State history | The current status, plus an append-only `transitions` table for items and branches. | Every type gets timestamps with no new columns. The history gives durations and an audit trail. | `mergedAt`, `devTestedAt`, and `prodTestedAt` stop being fields. Each change writes one more row. |
| 4 | Type definitions and state machines | One Python dict for each type in `worklog.py`: states, allowed transitions, terminal states, the fields required at a terminal state, and the fields that `status` shows. Branches share one machine. The script refuses a move that is not an edge, and `--force` allows it. `worklog.py types` prints the machines. | There are two types, and the rules forbid speculative features such as a plugin loader. One definition in code cannot drift from the rule. Back edges (`in-review` → `in-progress`, `monitoring` → `fixing`) are explicit. | A third type is one more dict. A missing edge blocks a valid move until the dict is changed, or until the caller uses `--force`. `--force` does not skip the required fields. Automatic moves and the import never need `--force`. |
| 5 | Ticket states | Item: `open` → `done`. At reconcile, the script sets `done` when all branches are `prod-tested` or `abandoned`. Branch: `in-progress`, `in-review`, `merged`, `dev-tested`, `prod-tested`, `abandoned`. | A stored item status gets transitions. A status set by hand can disagree with the branches. | Reconcile writes the transition to `done`. |
| 6 | Incident states | `investigating` → `cause-found` → `fixing` → `monitoring` → `resolved` or `false-positive`. The script refuses `resolved` without a summary and a resolution. | The states track your investigation, not the incident in incident.io. `/investigate-incident` already handles false positives. Without the rule, the summary is optional in practice. | The terminal fields of each type are required (decision 4). |
| 7 | Incident key | The incident.io ID (`INC-123`). Without an ID, `inc-<YYYYMMDD-HHMM>`. | This matches the working folder of `/investigate-incident`. (My call.) | The later integration uses the same key with no mapping. |
| 8 | Incident scope | Build the incident type now. Do not change `/investigate-incident` in this change. | A real second type proves that the type system extends. | `/investigate-incident` keeps writing `incident-log.local.md` for now. |
| 9 | Access | Every skill uses `worklog.py` and nothing else. No skill reads or writes the SQLite file. | The schema can change with no change to other skills. | Each consumer must switch in this change (decision 16). |
| 10 | Reads | `list --json` and `show <key> --json` with these filters: `--type`, `--key`, `--search`, `--branch`, `--session-id`, `--open`, `--status`. `--search` matches the title and the JSON values only (with `json_tree`), not the key names, and it uses `LIKE`. | You asked for type, ID, and keyword. The current consumers also look up by branch, by session, and by open status. `LIKE` is enough for hundreds of rows. | A new consumer needs no new command. There is no FTS5 index to keep in sync. |
| 11 | Lock | `worklog.py lock` sets `sweepLockedAt` on the branch row with one conditional `UPDATE`. It fails if a lock is set and is not stale. | `sweep-pr-comments` writes `data.json` directly today, and that write can race with `worklog.py`. (My call on the mechanism.) | The race goes away. Sweep needs about five changed lines. |
| 12 | CLI | The current commands and flags stay (`status`, `show`, `add`, `update`, `merged`). New commands are added for items and types. | `/implement-ticket` then needs no change. | The old commands become shortcuts for the ticket type. |
| 13 | Retention | Keep all rows. `status` hides items that finished more than 30 days ago. Remove `readyToDelete` and `clean`. | A delete removes the history of decision 3 and, later, the incident summaries. The file stays small. | The `clean --confirmed` hard rule goes away. |
| 14 | Storage | `~/.claude/work-log/worklog.db`, outside the config repo. Set WAL, `synchronous=NORMAL`, and `busy_timeout` on each connection. Apply schema migrations in order with `PRAGMA user_version`. | The skill folder is in the config repo, and `.gitignore` does not cover `*.db*`. A cron sweep and sessions write at the same time. | No incident detail can be committed. A writer waits for the lock and does not fail. |
| 15 | Import | Import `data.json` one time, including the `readyToDelete` entries. Unknown fields go into `data`. Rename the file to `data.json.migrated` after the import. | Keep all history (decision 13), and keep the fields of other skills. | A consumer that still reads `data.json` fails with an error, and does not read old data with no warning. |
| 16 | Consumers | Switch `sweep-pr-comments`, `open-claude-session`, and `focus` to `worklog.py` in this change, after the import. `focus` keeps reading `incident-log.local.md` for its incident tier. | All three read `data.json` directly (`focus.py:36`), and they break after the import. | One change touches four skills. |
| 17 | Timestamps | One full UTC timestamp, `entered_at`, on each transition. | You chose a simpler system over exact times. Dates show a state that starts and ends on the same day as 0 days. | There is no `recorded_at` column. |
| 18 | Event time | `entered_at` is always the time of the run. | It is the simplest option, and exact times are not important. | The time in `in-review` can be wrong by up to the time between `status` runs, because reconcile finds `merged` late. |
| 19 | Import history | Import the old dates as they are, with no GitHub backfill. | Times for old rows are not important. | Old rows have day precision. They have no `in-review` or `dev-tested` transition. |
| 20 | Durations | `show --json` returns the total time in each state for each branch (the sum of all visits, and the current state up to now), plus the `open` → `done` time of the item. | `focus` and later reports do not each calculate durations. | There is no time-in-state total across branches, because branches run at the same time and their times overlap. |

## Explicitly out of scope
- `/investigate-incident` writing to the log — deferred to the incident integration. The incident type exists so that integration needs no schema change.
- A file or plugin loader for each type — two types do not justify it.
- A read-only SQL command, and per-consumer commands — both expose the schema or multiply commands.
- FTS5 full-text search — `LIKE` is enough at this size, and FTS5 needs a second table that must stay in sync.
- A `--since` date filter — no consumer needs it yet.
- `recorded_at` and a GitHub backfill — you chose one timestamp and a simpler system.
- Time-in-state totals across branches — overlapping branches make the total ambiguous.

## Deferred
| Dimension | Why deferred | What would unblock it |
|-----------|--------------|----------------------|
| `/investigate-incident` writes its states, summary, and resolution to the log | Ticket work comes first | This change is merged, and the incident type is tested |
| `focus` reads incidents from the log, not from `incident-log.local.md` | It depends on the integration above | `/investigate-incident` writes to the log |
| The weekly report reads the log, with `--since` | The weekly report reads `incident-log.local.md` today | The incident integration is done, and the log replaces `incident-log.local.md` |

## Assumptions
- Every machine that runs the script has SQLite 3.38 or later, for `->>` and `json_tree`. This machine has Python 3.13.11 with SQLite 3.51.0. Other machines are not checked.
- `/implement-ticket` uses only the current commands and flags (`add`, `update`, `merged`, `show`, `status`). Check its `skill.md` before you change the CLI.
- The new `lock` uses the same stale threshold as the current `sweepLockedAt` logic in `sweep-pr-comments`.
- `open-claude-session` needs only the lookups in decision 10. Check its `rules.md`.

## Prior art consulted
- [SQLite JSON functions](https://www.sqlite.org/json1.html) — JSON stored as TEXT, the `->>` operator, and deterministic functions for expression indexes. This is the basis for decisions 1 and 10.
- [SQLite PRAGMA reference](https://www.sqlite.org/pragma.html) — `user_version` for ordered migrations, WAL, and `busy_timeout` set on each connection. This is the basis for decision 14.
- [Appropriate uses for SQLite](https://www.sqlite.org/whentouse.html) — one writer at a time, short locks, and no network filesystems. This confirms a local file for a single user.
- [DoltHub: choosing a schema for polymorphic data](https://www.dolthub.com/blog/2024-06-25-polymorphic-associations/) — a single table, tables per type, and a JSON column compared. The JSON column was chosen for extensibility, and its missing validation is accepted.
- [incident.io lifecycle](https://docs.incident.io/incidents/lifecycle) — Triage, Active (Investigating, Fixing, Monitoring), Post-incident, Closed, with one timestamp for each status. Its timestamps for each transition shaped decision 3. Its states were changed to track the investigation (decision 6).

## Open risks
- A skill can still open the SQLite file directly, and that bypasses the validation in Python. Only the access rule (decision 9) prevents it.
- If the import fails partway, the log can be half full. Run the import in one transaction, and rename `data.json` only after the commit.
- The four skills switch in one change. If one is missed, it fails on the missing `data.json` (this is intended), and that skill stops until it is fixed.
- The durations of `in-review` and `merged` are only as exact as the frequency of `status` runs (decision 18).

## Implementation plan (approved 2026-11-01)

Branch `feat/work-log-sqlite`, worktree `../claude-work-log-sqlite`. Work-log key `work-log-sqlite`.

- `work-log/worklog.py`: SQLite store (`items`, `branches`, `transitions`), `user_version` migrations, WAL, and a `TYPES` dict with the state machines. Edges are enforced, and `--force` skips only the edge check. The script imports `data.json` one time.
- CLI: the current commands stay. `add --key` is an alias of `--ticket`. Other changes:
  - `update --set k=v --force`
  - `item add` and `item update`
  - `lock` and `unlock` (2-hour stale limit)
  - `list` and `show` print JSON with durations
  - `types`
  - `clean` goes away
- Import:
  - Duplicate branches keep the `active` entry.
  - The `merged` entries in `readyToDelete` become `prod-tested` at `movedAt`.
  - The import drops `sweepLockedAt`.
  - If the current status has no date, the script records it at the import time.
- `work-log/test_worklog.py`: `unittest`.
- The script is the only access for these skills:
  - `sweep-pr-comments`: `list`, `lock`, `unlock`, `update --set`
  - `open-claude-session`: `list`
  - `implement-ticket`: the Phase 0 text changes
- `focus`: left out of the commit, because the skill is untracked.
- Nothing about the business or its names goes into the repo, because the repo is private and personal. The tests use `PROJ-1234` and `acme`.
