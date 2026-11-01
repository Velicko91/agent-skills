---
name: fix-pr-comments
description: Triages the unresolved review comments of a PR, checks each one against the code, fixes the real ones after approval (typos at once), and replies to every comment with the outcome. Use for "/fix-pr-comments", "address the PR comments", or "reply to the review".
allowed-tools: Bash(gh *), Bash(git *), Bash(jq *), Bash(make *), Bash(poetry *), Bash(uv *), Bash(npm *), Bash(~/.claude/skills/safe-push/push.sh *), Bash(~/.claude/skills/verify-stamp/stamp.sh *), Read, Edit, Grep, Glob, Agent, Skill
---

# Fix PR Comments

Fetch the open review comments of a PR, check each one, fix the real issues, and reply to every comment with the outcome.

## Hard rules

- NEVER skip the triage checkpoint (Step 4), unless `--auto` or `--unattended` is given.
- NEVER change code for a design or architecture comment without the user's approval.
- NEVER reply without addressing the issue: fix it, or explain why not.
- Read the file again immediately before each edit, because it can change during the session.
- Fix only what the comment describes, with minimal edits.
- NEVER script code changes (`sed -i`, `awk`, `perl -pi`, `python`, heredocs). Use Edit only, one clear change at a time. Scripts are fine for reading code.
- NEVER force-push. Always add a new commit.
- Start every reply with `Claude AI:`.
- NEVER give a decision to the `pr-comment-courier` subagent. It runs a cheaper model and has no code context. It only fetches and posts. You categorise each comment, write each reply, and make each edit.
- NEVER trust the courier's counts without the Step 2 reconciliation, because a silent drop looks like a clean run.
- Write a phase marker when each phase starts, as `~/.claude/skills/phase-markers/skill.md` says. The ID is the `⟨ph:…⟩` on the phase heading.

## Arguments

| Argument | Effect |
|---|---|
| `<number>` | The PR. Default: the PR of the current branch. |
| `--auto` | Skip the checkpoint. Fix typos only, and reply only to the rest. |
| `--unattended` | No user is present. Read `unattended.md` in this skill directory, and follow it. |
| `--dry-run` | Investigate and triage only. Change nothing, and post nothing. |
| `--no-delegate` | Run the `gh` steps on the session model, not on the courier |
| `--design <file>` | The design document of the PR, for example `plan-PROJ-1234.md`. Default: found from the ticket ID in the branch name (Step 2b). |
| `--escalate` | Tier 1: handle only the comments that need no session history, and list the rest on an `ESCALATE:` line. Read `tiers.md`. |
| `--only <ids>` | Tier 2: process only these comment ids, with the history of this session. Read `tiers.md`. |

If the run is automated (headless `claude -p`, `--bg`, cron, or called by another skill or agent), also read `unattended.md` for the scope guard.

## Model split

| Work | Runs on |
|---|---|
| Fetch and filter the comments (Step 2) | `pr-comment-courier` (Haiku) |
| Read the code, judge each comment, edit and review the fixes (Steps 3–5b, 7) | Session model |
| Post the reply bodies that the session wrote (Step 6) | `pr-comment-courier` (Haiku) |

The courier also keeps the raw `gh` JSON out of the session context. To change its model, edit `model:` in `~/.claude/agents/pr-comment-courier.md`.

## Workflow

### Step 1 — Identify the PR ⟨ph:caca814e⟩

Use the number in `$ARGUMENTS`. Otherwise run `gh pr view --json number,title,headRefName`.

### Step 2 — Fetch the comments ⟨ph:1c87b730⟩

```
Agent(
  subagent_type: "pr-comment-courier",
  description: "Fetch PR comments",
  prompt: "FETCH
           owner: <owner>
           repo: <repo>
           PR: <number>"
)
```

It returns `total_inline`, `newest_comment_at`, the `inline` list (newest first), `reviews`, `issue_comments`, and a `dropped` map.

**Reconcile the counts. This is required.** Count the inline comments yourself:

```bash
gh api "repos/{owner}/{repo}/pulls/{PR}/comments?per_page=100" --paginate --slurp | jq 'flatten | length'
```

Run the fallback if any check fails:

| Check | Fails when |
|---|---|
| Your count against `total_inline` | The numbers differ |
| The sum of `dropped` plus the length of `inline` | The sum differs from `total_inline` |
| Each value in `dropped` | A value exceeds `total_inline` |
| `newest_comment_at` against the newest date in your count | The courier's date is older |

NEVER start Step 3 with a list that fails a check. Report your count, `total_inline`, and whether they match.

**Fallback.** If the courier fails, returns malformed JSON or an `error` field, fails a check, or `--no-delegate` is given, run the FETCH steps of `~/.claude/agents/pr-comment-courier.md` yourself, and tell the user. Do not let a model filter the list by reading. Use the `jq` pipeline of that file.

Only root comments (no `in_reply_to_id`) are items to process. Replies in a thread are context. Number the root comments. With `--only <ids>`, keep only the root comments with those ids.

### Step 2b — Read the design ⟨ph:91602219⟩

If the PR has a design document, read it once, before you judge the comments, because it holds the reasons for the decisions:

1. Use `--design` if given.
2. Otherwise, take the ticket ID and the slug from the branch name (`git branch --show-current`, for example `feat/PROJ-1234-add-pagination` → `PROJ-1234` and `add-pagination`). Search the root, `docs/`, and `notes/` of this folder and of the main checkout (the first entry of `git worktree list`), because untracked documents stay where they were written. Take the first `.md` file whose name holds the ID, else the slug. Compare without case, because branch names can hold the ID in lowercase (`arc-490`).
3. If there is none, continue without it.

Use it to answer a design comment with the reason that was decided. If a comment asks to change a decision of the document, say so in the triage, because it is a design change.

### Step 3 — Investigate each comment ⟨ph:9e79122c⟩

Before you decide:

1. Read only the lines around the comment: `Read` with `offset` and `limit`, about 20 lines on each side of `line`, and read the `diff_hunk`. Read a whole file only if the comment is about the whole file, because each line you read is sent again with every later call.
2. Check whether the line still exists, and whether the concern applies to the current file, not only to the diff. Check related files if necessary.
3. Put the comment in a category:

   | Category | Examples | Action |
   |---|---|---|
   | Typo / formatting | Misspelled word, wrong punctuation, stray whitespace in a string or comment | Fix with no confirmation |
   | Real code issue | Logic bug, missing validation, wrong algorithm, bad default | Confirm, then fix |
   | Style / naming | Rename, indentation, aesthetics | Confirm, then fix |
   | Design / architecture | Restructured modules, changed interfaces | Confirm, then fix |
   | Invalid / not applicable | The reviewer misread the code, the code is removed, it is already fixed | Reply with the reason |
   | Ambiguous | It is not clear whether it is a real issue | Ask the user |

### Step 4 — Triage checkpoint ⟨ph:13364ca1⟩

STOP before you change anything. Show:

```
## PR #{number} — Comment Triage

| # | Author | File:Line | Summary | Category | Proposed Action |
|---|--------|-----------|---------|----------|-----------------|
| 1 | alice  | foo.py:42 | "Missing null check" | Real issue | Fix + reply |
| 2 | bob    | bar.py:7  | "Typo: recieve → receive" | Typo | Auto-fix + reply |
| 3 | alice  | baz.py:99 | "Why not use X instead?" | Design | Ask user |
| 4 | carol  | qux.py:12 | "This looks wrong" | Invalid — line was removed | Reply only (no fix) |
```

Ask: "Which items should I proceed with? `all`, numbers such as `1,3`, `auto` (typos only), `skip N`, or instructions for each item."

WAIT for the answer.

### Step 5 — Fix ⟨ph:0dfbc5bb⟩

Process only the approved items.

- **Typo:** apply the minimal fix with Edit. Run `make lint 2>&1 | tail -20`. If lint fails, revert the edit and tell the user. Do not try a second edit without telling the user.
- **Confirmed fix:** read the file again, apply the fix with Edit, and run the tests of the affected module if practical: `make test`, or the runner of the project, for example `poetry run pytest tests/path/test_affected.py -x -q 2>&1 | tail -30`. Keep test and lint output short with `-q` and `tail`, because a long output is sent again with every later call. If the tests fail, revert the edit and tell the user before you continue.
- **No fix:** change no code. Reply only.

### Step 5b — Review the fixes ⟨ph:b494d394⟩

If Step 5 changed files, review them before you reply and commit, because a reply must describe the final code:

1. Stage the changed files by name: `git add <files>`.
2. Run `/review-code`. Its default scope is the staged changes, so it reviews only the fixes of this run, not the whole branch.
3. It leaves its own small fixes unstaged. Check them with `git diff`, and stage them by name.
4. If it reports a Critical or Major issue in a fix:
   - **Interactive:** show the issue, and ask: fix it, keep the fix as it is, or undo the fix. WAIT.
   - **Unattended:** undo that fix with Edit, stage the file again, and reply to its comment `Claude AI: No change — the fix did not pass review.`
5. If you changed a fix, run `/review-code` again. Continue when it reports no Critical or Major issue.

### Step 6 — Reply to every processed comment ⟨ph:496aeea7⟩

Write every reply body yourself. Then give the whole batch to the courier:

```
Agent(
  subagent_type: "pr-comment-courier",
  description: "Post PR replies",
  prompt: "REPLY
           owner: <owner>
           repo: <repo>
           PR: <number>
           replies:
           - comment_id: 987
             kind: inline
             body: |
               Claude AI: Fixed — <what changed>.
           - comment_id: 77
             kind: issue
             body: |
               Claude AI: No change — <reason>."
)
```

It returns `posted` and `failed` lists. Report each `failed` entry in Step 8, and never count it as posted. If the courier fails or `--no-delegate` is given, run the REPLY steps of `~/.claude/agents/pr-comment-courier.md` yourself.

Reply examples:

```
Claude AI: Fixed — removed the redundant null check on line 42; the upstream validator already guarantees a non-null value here.
Claude AI: No change — this line was removed in the latest commit; the concern no longer applies.
Claude AI: No change — the empty list default is intentional; the docstring documents that callers provide their own list.
Claude AI: Acknowledged — this is a valid design concern but out of scope for this PR. Filed as a follow-up.
```

### Step 7 — Commit and push ⟨ph:8807174c⟩

If files changed:

```bash
git diff --name-only
git add <changed files>
git commit -m "fix: address PR review comments"
~/.claude/skills/safe-push/push.sh <base of the PR>
```

If more than one file changed, list the fixes in the commit message. `push.sh` pulls new commits of the branch, checks for a conflict with the base, and pushes only if both are clean:
- `CONFLICT_REMOTE` or `CONFLICT_BASE`: resolve it with "Resolve a conflict" in `~/.claude/skills/safe-push/skill.md`: automatically when you can, and ask only when it says that you cannot resolve it. Report each resolved file in Step 8.
- `PULLED …` before `PUSHED`: say that the branch now holds commits from others.

### Step 8 — Report ⟨ph:1eb00b85⟩

```
## Done — PR #{number}

| # | Comment | Action | Status |
|---|---------|--------|--------|
| 1 | Missing null check | Fixed in foo.py:42 | ✅ |
| 2 | Typo: recieve | Fixed in bar.py:7 | ✅ |
| 3 | Design question | No change — replied with rationale | 💬 |

**Files changed:** foo.py, bar.py
**Commits pushed:** 1
```

Then offer: "If new comments arrive or you change more, say **retry** for a fresh pass."

## Examples

- `/fix-pr-comments` ← the PR of the current branch
- `/fix-pr-comments 123`
- `/fix-pr-comments 123 --dry-run`

## Retry

If the user says "retry", use no cached comment data. Fetch the comments again, read the files again, and run the workflow from Step 1.
