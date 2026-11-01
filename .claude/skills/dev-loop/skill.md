---
name: dev-loop
description: Runs a full autonomous loop — ticket, worktree, implementation, then review → test → fix until both pass or --max-iter is hit, then a PR. Resumes an existing worktree. Use for "/dev-loop <description or ticket>" or end-to-end feature work.
user-invocable: true
allowed-tools: "*"
---

# Dev Loop

```
task-creator (skip if ticket) → worktree → coder → [reviewer → tester → coder-fix] × N → PR
```

If a worktree for the ticket exists, the loop resumes it and skips the first three steps.

## Hard rules

- All subagents run in autonomous mode. They never pause for human input.
- `--max-iter` is a hard cap. NEVER exceed it.
- All coding, review, tests, and PR work happen in the worktree, NEVER in the main checkout.
- NEVER use `git add .` or `git add -A`. Stage files by name.
- NEVER script code changes (`sed -i`, `awk`, `perl -pi`, `python`, heredocs). Use Edit and Write only, one clear change at a time. Scripts are fine for reading code. This rule applies to every subagent.
- NEVER commit `.dev-loop-state.json`. It stays untracked.
- Leave the worktree after the loop, so the user can inspect it.

## Arguments

```
/dev-loop <description | ticket ID | ticket URL> [extra context] [--max-iter N]
```

| Argument | Default | Meaning |
|---|---|---|
| description, key, or URL | required | A free-text description, a ticket ID (`PROJ-123`), or a ticket URL of the configured tracker |
| extra context | — | Text after a key or URL. In resume mode it becomes reviewer feedback. |
| `--max-iter N` | `3` | The maximum number of reviewer → tester → fix iterations |

## State file

`<worktree_path>/.dev-loop-state.json` holds the loop state across sessions:

```json
{
  "input": "<user description or ticket>",
  "ticket": "PROJ-123",
  "repo_root": "/abs/path/to/repo",
  "worktree_path": "/abs/path/to/repo/.claude/worktrees/PROJ-123",
  "branch": "feat/PROJ-123-short-slug",
  "iteration": 0,
  "reviewer": { "satisfied": false, "blocking_issues": [] },
  "tester": { "satisfied": false, "blocking_issues": [] }
}
```

## Subagent prompts

Put this preamble in every subagent prompt from Phase 4 on, at the place marked `<preamble>`:

> **Working directory:** `<worktree_path>`
> **State file:** `<worktree_path>/.dev-loop-state.json`
>
> **First command:** Run `cd <worktree_path>` as a standalone Bash command, never as `cd <worktree_path> && <cmd>`. The working directory persists between Bash calls, so do not `cd` again or back to the main repo. Use absolute paths for files outside the worktree, such as `~/.claude/skills/`.
>
> **Autonomous mode:** Never pause for human input. Never script code changes; use Edit and Write. Never use `git add .` or `git add -A`.

The reviewer and the tester end their output with this block:

```
---LOOP-STATUS---
SATISFIED: yes | no
BLOCKING_ISSUES:
- none | <issue>
---END-STATUS---
```

Then they set `<role>.satisfied` and `<role>.blocking_issues` in the state file. If the block is missing, treat the result as `SATISFIED: no` with the issue `Status block missing from agent output`.

Set the `model` of each subagent:

| Subagent | `model` | Reason |
|---|---|---|
| task-creator | `sonnet` | It writes a ticket from a description. |
| worktree-creator | `haiku` | It runs git commands. |
| coder, coder-fix | session model | Implementation needs judgement. |
| reviewer | session model | Review needs judgement. |
| tester | `sonnet` | It updates and writes tests to a known pattern. |
| PR creator | session model | `/create-pr` gives its mechanical part to `pr-author` (Haiku). |

## Workflow

### Phase 1 — Initialize

1. Take `--max-iter N` out of `$ARGUMENTS` (default 3).
2. Find the input type:
   - A ticket URL or ID, by the Identify section of the tracker adapter (`~/.claude/skills/tracker/skill.md`) → `has_ticket = true`. The text after it is `user_context`.
   - Any other text → `has_ticket = false`, and `user_context` is empty.
3. Get the repo root: `git rev-parse --show-toplevel`.
4. If `has_ticket` is true and `<repo_root>/.claude/worktrees/<ticket>` exists, go to Phase 1b. Otherwise go to Phase 2.

### Phase 1b — Resume

1. Set `worktree_path = <repo_root>/.claude/worktrees/<ticket>`.
2. Read the state file. If it does not exist, write it with `iteration: 0`, both roles unsatisfied, and the branch from `git -C <worktree_path> branch --show-current`.
3. If `user_context` is not empty:
   - Set `reviewer.satisfied = false` and `reviewer.blocking_issues = ["User context: <user_context>"]`.
   - Show `🔄 Resuming <ticket> — injecting user context as reviewer feedback`.
   - Go to Step 5d. User context is always reviewer feedback; never implement again from the start.
4. If `user_context` is empty, show `🔄 Resuming <ticket> — jumping to review`, and go to Step 5a.

### Phase 2 — Task creator

Skip this phase if `has_ticket` is true.

> You are the **task-creator** in an automated development loop.
> **Input:** `<$ARGUMENTS>`
> Read `~/.claude/skills/create-ticket/skill.md` and follow it exactly. Do not pause or ask for confirmation.
> On the last line, write: `TICKET: <key>`

Take `ticket` from the last line.

### Phase 3 — Worktree

> You are the **worktree-creator** in an automated development loop.
> **Ticket:** `<ticket>`
> Read `~/.claude/skills/create-worktree/skill.md` and follow it exactly. At the plan checkpoint ("Shall I create the worktree?"), confirm and continue. But if the branch exists already, or `.claude/worktrees/` is not ignored, do not decide: stop, and on the last line write `WORKTREE: blocked — <reason>`.
> On the last line, write: `WORKTREE: <worktree_path>`

If the last `WORKTREE:` line says `blocked`, stop the loop, and report the reason to the user. Otherwise, take `worktree_path` from it. Get `branch` with `git -C <worktree_path> branch --show-current`. Then write the state file.

### Phase 4 — Coder (first pass)

> You are the **coder** in an automated development loop. Implement the ticket `<ticket>`.
> <preamble>
> Read `~/.claude/skills/implement-ticket/skill.md` and follow it exactly from the worktree. If the skill says "STOP and WAIT for the user to approve the plan", approve the plan and continue. Complete all phases, including the tests.
> On the last line, write: `CODER: done`

### Phase 5 — Review → test → fix loop

Repeat until `reviewer.satisfied` and `tester.satisfied` are both true, or `iteration >= max_iter`. At the start of each iteration, add 1 to `iteration` in the state file.

**Step 5a — Reviewer**

> You are the **reviewer** in an automated development loop. Review all staged changes.
> <preamble>
> Read `~/.claude/skills/review-code/skill.md`, and run `full --branch`: a full review of the whole branch, committed or not, compared with the default branch (usually `main`).
> `SATISFIED: yes` means that no Critical or Major issue exists. Minor issues and nits do not block. List each blocking issue as `<file>:<line> — <issue>`.
> End with the status block, then update the state file. Then run `~/.claude/skills/verify-stamp/stamp.sh record review clean` if you are satisfied, or `record review blocking` if not.

**Step 5b — Tester**

> You are the **tester** in an automated development loop. Make sure that all changes are tested.
> <preamble>
> 1. Read `~/.claude/skills/update-tests/skill.md`, and follow it with `--auto --branch`: fix all failing tests, write all missing tests, and run the full suite with the test stamp rules. If `check tests` prints `FRESH`, the suite already passed on this exact content; do not run it again.
> 2. Report each function that `--auto` left out as a blocking issue.
> `SATISFIED: yes` means that all tests pass and all new code paths have tests.
> End with the status block, then update the state file.

**Step 5c — Check.** Read the state file.
- If both roles are satisfied, go to Phase 6.
- If `iteration >= max_iter`, go to Phase 6 with a warning.
- Otherwise, go to Step 5d.

**Step 5d — Coder fix**

> You are the **coder** in iteration `<N>` of an automated development loop. The feature exists. Fix the issues below.
> <preamble>
> **Reviewer issues:** <reviewer.blocking_issues, or "none">
> **Tester issues:** <tester.blocking_issues, or "none">
> 1. Read the related source files.
> 2. Fix each issue. Do not refactor unrelated code.
> 3. For a tester issue, fix the test or the source code, whichever is wrong.
> 4. Stage the changes by file name.
> 5. Run the full test suite with the test stamp rules in `~/.claude/skills/verify-stamp/skill.md` (`check tests` first, `record tests passed|failed` after): `make test` if it exists, else the runner of the project, for example `poetry run pytest -x`.
> 6. Report each issue as fixed, or say why you could not fix it.

Then go to Step 5a.

### Phase 6 — PR creator

> You are the **PR creator** in an automated development loop. Open a pull request.
> <preamble>
> **Branch:** `<branch>` **Ticket:** `<ticket>`
> Run `/create-pr --skip-code-review --skip-tests`, or read `~/.claude/skills/create-pr/skill.md` and follow it with those flags. The reviewer and the tester already did those steps. Do not pause for human input.
> On the last line, write: `PR: <url>`

Take the PR URL from the last line.

### Phase 7 — Output

```
✅ Dev loop complete

🎫 Ticket:     <ticket> — <title>
🌿 Branch:     <branch>
📁 Worktree:   <worktree_path>
🔄 Iterations: <N> / <max_iter>
🔗 PR:         <url>

Reviewer:  ✅ satisfied
Tester:    ✅ satisfied
```

If the loop stopped at `max_iter` with open issues, add:

```
⚠️  Max iterations reached — open issues remain:

Reviewer issues:
- <issue>

Tester issues:
- <issue>

PR was still created — inspect the branch before merging.
```

## Examples

- `/dev-loop add pagination to the positions GraphQL resolver`
- `/dev-loop PROJ-123`
- `/dev-loop https://linear.app/<workspace>/issue/PROJ-123`
- `/dev-loop add rate limiting to the GQL API --max-iter 5`
- `/dev-loop PROJ-123 the pagination offset is off by one and needs a test` ← resume with reviewer feedback
- `/dev-loop PROJ-123` ← resume with no extra context, start at the reviewer
