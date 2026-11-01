---
name: sweep-pr-comments
description: Sweeps the open PRs in the /implement-ticket work log for new unanswered review comments, fixes the simple ones in a cheap fresh session, and sends only the hard ones to the PR's own session. Built for cron. Use for "sweep PR comments".
user-invocable: true
allowed-tools: Bash(gh *), Bash(jq *), Bash(mv *), Bash(date *), Bash(claude *), Bash(git -C *), Read, Glob
model: haiku
---

# Sweep PR Comments

Check every open PR in the work log. For each PR with new unanswered comments, run `/fix-pr-comments` in two tiers: a fresh session, with the design document of the ticket, fixes the simple comments, and the PR's own session gets only the comments that need its history. A fresh session costs about a tenth of a resumed one, because it does not send the whole implementation history with every call.

This skill runs **unattended**. It has no checkpoint. It asks no question.

## Arguments

None.

## Local configuration

The work log is `~/.claude/skills/work-log/data.json`. It is local state and is never committed.

- If the file is missing, print `No work log found` and stop.
- Read the entries in `active`. Use the fields `ticket`, `branch`, `session`, `sessionId`, `sessionCwd`, `pr`, `status`, `worktree`.
- NEVER guess a PR URL, a session name, or a path.

This skill adds two fields to an entry. Create them when they are absent:

| Field | Meaning |
|-------|---------|
| `sweepLockedAt` | ISO time. A run sets it before it starts `/fix-pr-comments`. A run clears it after. |
| `sweepCheckedAt` | ISO time of the last successful check of this PR. |

## How the skill uses other parts

| Work | Done by | Reason |
|------|---------|--------|
| Count new comments (ids only) | This session, with `gh` and `jq` | One cheap call. No comment text enters the context. |
| Fix and reply to the simple comments (tier 1) | A fresh session in the PR folder, with `/fix-pr-comments --escalate` and the design document | It needs no history, and costs about a tenth of the PR session. |
| Fix and reply to the escalated comments (tier 2) | The resumed PR session, with `/fix-pr-comments --only <ids>` | Only these comments need the implementation history. |
| Fetch comment bodies, post replies | `pr-comment-courier`, called by `/fix-pr-comments` | Cheap model. Handled inside the fresh session. |

## Workflow

### Step 1 — Select the PRs

1. Read `data.json`.
2. Keep the entries where `status` is `in-progress` or `in-review` and `pr` is not empty.
3. Skip an entry when `sweepLockedAt` is less than 2 hours old. Another run owns it.
4. Treat a lock that is 2 hours old or older as stale. Ignore it.

Parse each `pr` URL: `https://github.com/<owner>/<repo>/pull/<number>`. If the URL does not match, report the entry as `skipped: bad URL`.

### Step 2 — Check each PR (cheap)

For each PR:

1. Check that the PR is open. If the state is not `OPEN`, print `skipped: <state>` and go to the next PR. Do not change `status`.

   ```bash
   gh pr view <pr-url> --json state --jq '.state'
   ```

2. Count the unanswered inline root comments that are not in a resolved thread. Run all of this in one Bash call, because shell variables do not persist between calls. The command returns ids only:

   ```bash
   set -o pipefail
   ME=$(gh api user --jq '.login')
   RESOLVED=$(gh api graphql --paginate -f owner="<owner>" -f name="<repo>" -F number=<number> -f query='
     query($owner: String!, $name: String!, $number: Int!, $endCursor: String) {
       repository(owner: $owner, name: $name) { pullRequest(number: $number) {
         reviewThreads(first: 100, after: $endCursor) {
           pageInfo { hasNextPage endCursor }
           nodes { isResolved comments(first: 1) { nodes { databaseId } } } } } } }' \
     --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved) | .comments.nodes[0].databaseId' \
     | jq -sc '.') || { echo "resolved threads unavailable"; exit 1; }
   gh api "repos/<owner>/<repo>/pulls/<number>/comments?per_page=100" --paginate --slurp \
     | jq --arg me "$ME" --argjson resolved "$RESOLVED" 'flatten | . as $all
         | ($all | map(select(.in_reply_to_id != null and .user.login == $me) | .in_reply_to_id)) as $ans
         | [$all[] | select(.in_reply_to_id == null
             and ((.body // "") | startswith("Claude AI:") | not)
             and ((.id as $i | $ans | index($i)) == null)
             and ((.id as $i | $resolved | index($i)) == null)) | .id]'
   ```

   If it prints `resolved threads unavailable`, print `skipped: resolved threads unavailable`, and go to the next PR. Do not change `sweepCheckedAt`, so the next sweep checks this PR again.

3. Count the new discussion comments. Use `sweepCheckedAt`, or `1970-01-01T00:00:00Z` when it is absent:

   ```bash
   gh api "repos/<owner>/<repo>/issues/<number>/comments?per_page=100" --paginate --slurp \
     | jq --arg since "<sweepCheckedAt>" 'flatten
         | [.[] | select(.created_at > $since and .user.type == "User"
             and ((.body // "") | startswith("Claude AI:") | not)) | .id]'
   ```

4. If both lists are empty, set `sweepCheckedAt` to now and go to the next PR. Print `no new comments`.

### Step 3 — Fix the comments in two tiers

The expensive PR session handles only the comments that need its history. Tier 1 handles the rest in a fresh session, at about a tenth of the cost.

If a list has ids:

1. Set `sweepLockedAt` to now in `data.json`.
2. Choose the folder: the `worktree` of the entry, else its `sessionCwd`. If both are `null`, record `failed: no folder`.
3. Check that the PR branch is checked out there: `git -C "<folder>" branch --show-current` must print the `branch` of the entry. If it does not, record `failed: <branch> not checked out in <folder>`, because the fixes would go to the wrong branch.
4. Find the design document. Search the root, `docs/`, and `notes/` of the folder and of the main checkout (the first entry of `git -C "<folder>" worktree list`), because untracked documents stay in the checkout where they were written. Take the first `.md` file whose name holds the `ticket` ID (for example `plan-<ticket>.md`), else the slug of the branch (the part after `<ticket>-`, for example `design-alignment-add-pagination.md`). Compare without case, because branch names can hold the ID in lowercase (`arc-490`).
5. **Tier 1 — a fresh session.** Do not resume the PR session here:

   ```bash
   cd "<folder>" && claude --permission-mode acceptEdits -p "/fix-pr-comments <number> --unattended --escalate [--design <document>]"
   ```

   Add `--design` only if step 4 found a document. Take the last `ESCALATE:` line of the output.
6. **Tier 2 — the PR session, only if `ESCALATE:` lists ids.** Resume the session of the entry, in its `sessionCwd`, because `claude --resume` finds a session only from the folder that owns it:

   ```bash
   cd "<sessionCwd>" && claude --resume "<sessionId>" --permission-mode acceptEdits -p "/fix-pr-comments <number> --unattended --only <ids>"
   ```

   If the entry has no `sessionId`, use `session`. If the session is not found, record `escalated: <ids> — PR session not found`; do not start a new session for tier 2, because a new session has no history.
7. If a command fails, or the `ESCALATE:` line is missing, record `failed: <short reason>`.
8. If tier 1 (and tier 2, if it ran) succeeded, set `sweepCheckedAt` to the time at the start of Step 2 for this PR.
9. Always clear `sweepLockedAt` after the commands end, also after a failure.

Write `data.json` with a temporary file, then move it over the original. Use the full path, because a cron run starts in another folder:

```bash
L=~/.claude/skills/work-log/data.json
jq '<update>' "$L" > "$L.tmp" && mv "$L.tmp" "$L"
```

Update only the fields of the entries you changed. Read the file again just before each write, because another skill can change it.

Process the PRs one after the other.

### Step 4 — Report

Print one table. Add no other text.

```
| Ticket | PR | New comments | Escalated | Result |
|--------|----|--------------|-----------|--------|
| INV-1234 | #56 | 3 | 1 | fixed (1 in the PR session) |
| INV-1301 | #61 | 0 | 0 | no new comments |
| INV-1400 | #70 | 1 | 0 | failed: feat/INV-1400-x not checked out in <folder> |
```

## Rules

- NEVER ask the user a question. A cron job cannot answer.
- ALWAYS run tier 1 in a fresh session, and resume the PR session only for the comments that tier 1 escalates.
- NEVER read comment text in this session. Count ids only.
- NEVER edit code in this session. The tier 1 and tier 2 `/fix-pr-comments` sessions edit code.
- NEVER write a field other than `sweepLockedAt` and `sweepCheckedAt`.
- ALWAYS clear `sweepLockedAt` when the `/fix-pr-comments` run ends.
- Pass `--unattended` to both tiers. It skips the triage checkpoint. With `--escalate`, tier 1 fixes the simple comments and escalates the rest; with `--only`, tier 2 handles those with the session history.

## Cron

Call the skill from cron:

```bash
claude -p "/sweep-pr-comments"
```

## Examples

- `/sweep-pr-comments`
- `claude -p "/sweep-pr-comments"` (cron entry)
