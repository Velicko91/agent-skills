# Placement rules

Step 4 reads this file to decide where a session opens: a new workspace, or a new tab.
Use the first rule that matches.

| # | Condition | Mode | Where |
|---|---|---|---|
| 1 | The new session works on the same ticket as a work-log session, on the next PR in the stack | fork the work-log session | a new tab in the workspace of that session |
| 2 | `--fork` is set, and the new session works on a different ticket | fork | a new workspace in `<group>` |
| 3 | `--resume` is set | resume | a new workspace in `<group>` |
| 4 | Any other case | new session | a new workspace in `<group>` |

## Rule 1 — next PR in the stack

- The ticket of the new session is the ticket in `--name` or `--prompt`. If neither has a ticket, it is the `ticket` of the fork source.
- Fork the session. Do not start a new one, because the fork keeps the context of the earlier PRs in the stack.
- Open the fork as a tab beside the source session, so all the PRs of one ticket stay in one workspace.
- If the source workspace is not open, open a new workspace in `<group>`, and say that the source workspace was not found.
