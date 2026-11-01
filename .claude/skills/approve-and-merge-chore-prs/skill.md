---
name: approve-and-merge-chore-prs
description: Lists open PRs, then approves and queues the dependabot dependency-update PRs after one confirmation, and lists the other chore PRs. Use for "/approve-and-merge-chore-prs" or "approve the dependabot PRs". For an in-depth review of one bump, use /review-dependabot-pr.
allowed-tools: Bash(gh *)
model: haiku
---

# Approve and Merge Chore PRs

Bulk-process open PRs: auto-approve and queue all dependabot dependency-update PRs after confirmation, and surface any other `chore:` PRs in a summary table.

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| _(none)_ | — | Operates on the current repo |
| `--repo owner/repo` | Optional | Target a specific repo instead |

## Workflow

### Phase 1 — Fetch PRs

Run:
```bash
gh pr list --state open --json number,title,author,url --limit 100 --jq '.[] | [.number, .author.login, .author.is_bot, .title, .url] | @tsv'
# If --repo was passed:
gh pr list --repo <owner/repo> --state open --json number,title,author,url --limit 100 --jq '.[] | [.number, .author.login, .author.is_bot, .title, .url] | @tsv'
```

From the results, split into two buckets:

**Dependabot PRs** — author login is `app/dependabot` and `is_bot` is `true`. `gh pr list` reports dependabot this way, never as `dependabot[bot]`.

**Other chore PRs** — author is not dependabot, and the title starts with `chore:` or `chore(` (case-insensitive)

### Phase 2 — Present and Confirm

Display a summary to the user:

**If dependabot PRs exist**, list them:
```
Dependabot PRs to approve and queue:

  #142  chore(deps): bump sqlalchemy from 2.0.28 to 2.0.30
  #138  chore(deps): bump ruff from 0.3.4 to 0.3.7
  #135  chore(deps-dev): bump pytest from 8.1.1 to 8.2.0

Ready to approve and add all 3 to the merge queue.
```

**If other chore PRs exist**, show them in a table:
```
Other chore PRs (manual review needed):

  #  | Title                              | Author         | URL
  ---|------------------------------------|----------------|-----------------------------
  131 | chore: clean up legacy flags       | alice          | https://github.com/...
  129 | chore: remove deprecated endpoint  | bob            | https://github.com/...
```

**If no dependabot PRs exist**, say so clearly and stop.

# --- CHECKPOINT ---
Ask: **"Approve and queue these [N] dependabot PRs?"**
STOP and WAIT for the user to confirm. Do NOT proceed until they say yes (or equivalent).

### Phase 3 — Approve and Queue

For each dependabot PR, run in sequence:
```bash
gh pr review <number> --approve
gh pr merge <number> --auto
```

Report result for each PR as it completes:
```
✅ #142 — approved and queued
✅ #138 — approved and queued
❌ #135 — failed: <error message>
```

If any PR fails, continue with the rest and report all failures at the end.

## Rules

- NEVER approve a PR unless its author login is exactly `app/dependabot` and `is_bot` is `true`
- NEVER approve a PR whose title does not show a dependency update: it must contain `deps`, `dependencies`, or `bump`. The prefix can vary, for example `chore(deps):` or `feat: bump`.
- ALWAYS wait for user confirmation before approving anything
- If `--repo` is not passed, infer the repo from the current git context via `gh pr list` (no explicit `--repo` flag needed)

## Examples

- `/approve-and-merge-chore-prs` — process PRs in the current repo
- `/approve-and-merge-chore-prs --repo acme/payments-service` — process PRs in a different repo
