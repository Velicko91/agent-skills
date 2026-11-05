---
name: implement-ticket
description: Implements a ticket from the configured tracker (Linear today) or a free-text spec — explores the code, writes a plan with three self-review passes, waits for approval, implements and tests, then follows the ticket through merge, dev tests, and prod checks. Use for "/implement-ticket PROJ-1234", a ticket URL, or "implement this ticket".
user-invocable: true
allowed-tools: "*"
---

# Implement Ticket

Build a reviewed plan from a ticket or a description. Get approval, then implement it. Follow the ticket until it is merged, tested on dev, and checked on prod.

## Hard rules

- NEVER write code before the user approves the plan.
- Ask all questions in one message.
- NEVER commit or stage the ticket document. It is working material, and a reviewer cannot tell a plan file in the diff from the product.
- NEVER use `git add .` or `git add -A`. Stage files by name.
- NEVER script a code change (`sed -i`, `awk`, `perl -pi`, `python`, heredocs). Use Edit and Write only, one clear change at a time, with no bulk find-and-replace. Scripts are fine for reading code.
- NEVER delete a work-log entry unless the user asks in this conversation. Silence, or approval of something else, is not permission.
- NEVER run `/create-pr` automatically. The user does that.
- NEVER set `prod-tested` or move the ticket to done before the user confirms that each prod check passes. A merge or a dev test is not the end of the ticket.
- NEVER send a call to prod. The user runs the prod checks, because a call on prod can change real customer data.
- Use `date -u +%Y-%m-%d` for every date. NEVER guess today's date.
- ALWAYS update the PR description after each push to an open PR, as "PR description" says. A stale description describes code that is not on the branch.
- Write a phase marker when each phase starts, as `~/.claude/skills/phase-markers/skill.md` says. The ID is the `⟨ph:…⟩` on the phase heading.

## Arguments

| Form | Example | Behaviour |
|------|---------|-----------|
| Ticket URL | `https://linear.app/<workspace>/issue/PROJ-1234/...` | Fetch the ticket |
| Ticket ID | `PROJ-1234` | Fetch the ticket |
| Free-text description | `"add rate limiting to the GQL API"` | Use it as the specification |
| *(empty)* | — | Ask: "What should I implement? Give a ticket URL or ID, or a description." |

Text after the ID is extra direction for the plan, for example "skip the gRPC layer".

By default, the skill builds the change in steps: it implements, tests, reviews, and commits each step before the next one starts. See Phase 6a.

Add `--no-incremental` to implement the whole plan at once, and to leave the changes staged for `/create-pr`, with no commit.

## Tracker

Follow "Select the tracker" in `~/.claude/skills/tracker/skill.md`, and read the adapter. Phase 1 uses its Identify and Tools sections, and every call follows its Rules.

## Workflow

### Phase 0 — Work log ⟨ph:00ad41f5⟩

Run `/work-log status`. Show its output first. It lists the open work, the work that waits for a test, and the open incidents.

- If the ticket in `$ARGUMENTS` has an open entry, say so, and offer to resume it with its `claude --resume` command.
- If the entry is `merged`, continue at Phase 9. If it is `dev-tested`, continue at Phase 10.
- If this session is resumed and its PR is open, first catch up on what happened without it: read the new PR comments and replies (`gh pr view <pr> --comments`) and the commits since your last one (`git log --oneline <your last commit>..origin/<branch>`). Tier 1 of `/sweep-pr-comments` fixes simple review comments in a fresh session, so this session did not see those changes.
### Phase 1 — Load the issue ⟨ph:92c74439⟩

If `$ARGUMENTS` matches the URL or ID pattern of the adapter (Identify):

1. Take the ID, from the URL if necessary.
2. Fetch the ticket with the Fetch tool of the adapter.
3. Take the title, description, acceptance criteria, labels, parent, project, and state. Ignore a suggested branch name.
4. Show: `🎫 PROJ-1234 — <title>`

Name the session `<TICKET>-<short-description>`. The description is the title in lowercase, with hyphens for other characters, cut to about 4 words. Show the command:

```
📎 Name this session:  /rename PROJ-1234-add-pagination-positions
```

Use this one name for the session, the work-log `session` field, `claude --resume`, and the `-n` value of any later session.

If `$ARGUMENTS` is a description, use it as the specification. Do not fetch anything.

### Phase 2 — Find the existing ticket document ⟨ph:f3607943⟩

`/plan`, `/drill-me`, or a tech spec can already hold a document for this ticket. Use that document. NEVER start a second one, because two plans drift apart.

```bash
git rev-parse --show-toplevel
ls *.md docs/*.md notes/*.md 2>/dev/null
```

Match in this order. Stop at the first match:

1. The identifier in the file name: `PROJ-1234-plan.md`, `plan-PROJ-1234.md`
2. The identifier in the first 20 lines of the file
3. The branch slug in the file name: `implementation-plan-add-pagination.md`

If two documents match, list them and ask which one to use. Do not merge them.

If a document matches:
- Read all of it before Phase 3.
- Show: `📄 Using existing document: plan-PROJ-1234.md`
- Use it as the plan base, and write each plan update back to it.
- If it disagrees with the issue, list the differences at the checkpoint and ask which one is current. Do not assume that the document is stale.

If no document matches, keep the plan in the conversation until the user approves it. Then write the approved plan to `plan-<ID>.md` (or `plan-<slug>.md` with no ticket) at the root of the repo or the worktree, so a later `/fix-pr-comments` in a fresh session can read the design and the reasons. It is working material: never stage or commit it.

### Phase 3 — Explore ⟨ph:0103e371⟩

Find the affected entry points, the models and schemas to change, the existing tests, and the patterns to follow.

### Phase 4 — Draft the plan ⟨ph:48471001⟩

If Phase 2 found a document, start from it. Keep its headings and wording where they still hold, because the user wrote or approved them. Use this template:

```
## Implementation Plan

**Issue:** PROJ-1234 — <title>        (or "Spec: <description>")

### What I'll implement
<one-paragraph summary>

### Files I'll change
- `path/to/file.py` — what changes and why
- `path/to/test_file.py` — which tests to add or update

### Approach
<functions, patterns, data structures>

### Edge cases and risks
- <item>

### Steps                              (omit with --no-incremental)
1. <type>: <what the step does> — `file_a.py`, `test_file_a.py`
2. <type>: <what the step does> — `file_b.py`, `test_file_b.py`

### Plan review notes
- Pass 1: <what was found and fixed>
- Pass 2: <what was found and fixed>
- Pass 3: <what was found and fixed>
```

### Phase 5 — Self-review (3 passes) ⟨ph:67679054⟩

Review the plan as `/review-code` reviews code. Run exactly 3 passes, and update the plan after each one. Do not show the passes. Show only the review notes.

Each pass checks:
1. **Design** — Is there a simpler approach, or one that matches the code base better?
2. **Architecture** — Is the separation of concerns correct? Does the plan add coupling or break a convention?
3. **Completeness** — Are files, tests, error handling, or acceptance criteria missing?
4. **Correctness** — Are there logic errors, performance traps, or other risks?

### CHECKPOINT — Present the plan ⟨ph:8988d3c9⟩

Show the plan. Put all open questions in the same message. Ask: "Shall I proceed, or do you want to adjust anything?"

STOP and WAIT. If the user asks for changes, update the plan, show it again, and wait again. After the approval, save the plan to the ticket document (Phase 2): the existing document, or `plan-<ID>.md`.

### Phase 6 — Implement ⟨ph:77c3efeb⟩

**Create the branch before the first edit.** `/create-pr` and the PR title check expect this format:

```
<type>/<TICKET>-<short-description>      e.g. feat/PROJ-1234-add-pagination-positions
```

- `type` is one of `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`, `ci`, `build`, `revert`. A defect is `fix`, a new capability is `feat`, and a change of structure with no change of behaviour is `refactor`.
- `short-description` is the same as in the session name.
- Do not use the branch name that the tracker suggests (for example the Linear `gitBranchName`), because it starts with a username.
- For a worktree, create it with the full branch name: `git worktree add -b <branch> <path> <base>`. The folder name can be anything.
- Each stacked PR branch also starts with its own type.
- If the work is on a branch with a different name and nothing is pushed, run `git branch -m <new-name>`. If the branch is pushed or has a PR, ask the user, because a rename needs a new PR.
- Check with `git branch --show-current` before the first commit.

When the branch exists, record it at once, because an entry written later is lost if the session stops:

```
/work-log add --ticket PROJ-1234 --title "<title>" --branch <branch> --session <session> --session-id <id> [--worktree <path>]
```

Get `<id>` with `echo $CLAUDE_CODE_SESSION_ID`. A resume by ID works also after a `/rename`.

Apply these rules to each code change:
- Change one file at a time. Follow the conventions of the code: naming, imports, docstrings, error handling.
- Add a code comment only when the code cannot explain itself. Keep a comment to 5 lines or fewer. Docstrings have no limit.

Then run Phase 6a.

With `--no-incremental`, do this instead of Phase 6a, then go to Phase 7:
- Implement the whole plan. Do not change test files in this phase.
- Stage each logical group with `git add <files>`.
- Report:

  ```
  ✅ Implementation complete — <N> files changed
  Staged: <files>
  ```

### Phase 6a — Steps ⟨ph:d94ee4b6⟩

Run this loop once for each step of the plan, in order:

1. Implement the source changes of the step, with the rules of Phase 6.
2. Add or update the tests of the step.
3. Run the tests of the modules that the step changes. Record no stamp, because this is not the full suite. If a test fails, fix it before you continue.
4. Stage the files of the step by name. Run `/review-code`: its default scope is the staged changes, so it reviews only this step. Fix each real problem, stage it again, and run it again until it finds no Critical or Major issue.
5. Commit the step:
   ```bash
   git commit -m "<type>: <what the step does>" -m "Refs: <TICKET>" -m "<attribution line>"
   ```
   The subject is a Conventional Commit: no ticket between the type and the colon. NEVER push, because `/create-pr` pushes the branch.
6. Report one line: `✅ Step 2/4 — <short sha> (not pushed) <subject> — tests: <N> passed — review: clean`. The step is not pushed yet, so it has no link; the `/create-pr` report links it.

A step is one logical change that builds and passes its own tests, usually 1–4 files, for example "add the model and the migration" or "add the resolver". Plan approval at the checkpoint is the permission to commit each step.

If a step review finds a design problem, or a step needs a change that the plan does not have, STOP. Show the problem and ask how to continue, because the later steps build on this one.

After the last step, run Phase 7, then Phase 8. The final `/review-code --branch` reads the whole branch again, but each step is already reviewed, so it looks mainly at how the steps fit together.

### Phase 7 — Tests ⟨ph:17aabef4⟩

With `--no-incremental`, first add or update the tests. Follow the patterns of the existing tests for that domain. Stage the tests after the source changes, so the diff is easy to review.

Run the full test suite, with the test stamp rules in `~/.claude/skills/verify-stamp/skill.md`: `check tests` before the run, and `record tests passed|failed` after it. If a test fails, fix it and run the suite again. Without `--no-incremental`, commit the fix as its own commit, as in Phase 6a step 5.

### Phase 8 — Review and finish ⟨ph:2976f0d6⟩

Without `--no-incremental`, commit the fixes of each review round in Phase 8 and Phase 8a as their own commit, as in Phase 6a step 5, before the next round. Then each round is a separate commit, and no fix stays staged.

1. Run `/review-code --branch`: it reviews the whole change compared with the default branch (usually `main`), committed or not. Fix each real problem, stage it again, and run `/review-code --branch` again. Write down each false positive or intentional trade-off. When it finds no Critical or Major issue, run `~/.claude/skills/verify-stamp/stamp.sh record review clean`.
   - If the review changed files, run the full suite again with the test stamp rules. Then `/create-pr` can reuse both stamps.
2. Run the built-in Claude Code review at the high level: `/code-review high <branch>`. This is `code-review`, not the `/review-code` skill of step 1. It is a second review that is not anchored on step 1, so it finds other bugs.
   - Check each finding against the code. Fix each real one by hand with Edit, and write down each false positive.
   - Do not pass `--fix` or `--comment`, because each fix needs a check, and the PR does not exist yet.
   - If you changed files, run the full suite again with the test stamp rules, and run `stamp.sh record review clean` again.
3. Check that the ticket document is not staged:
   ```bash
   git diff --cached --name-only
   ```
   If it is staged, run `git restore --staged <document>` and tell the user.
4. If `git ls-files <document>` shows that an earlier commit tracks the document, tell the user. Offer to add it to `.gitignore` and run `git rm --cached <document>`. Do not remove a tracked file without permission.
5. Run Phase 8a. If it fails, STOP, and do not report ready.
6. When both reviews find no blocking issue, and Phase 8a passes or is skipped, report:
   ```
   ✅ Ready for review

   Files changed:
   - <file>: <what changed>

   Docker test: passed | skipped — <reason>
   Screenshots: <PNG paths, or none>

   Run /create-pr when ready to open a pull request.
   ```
7. When the PR is open, run `/work-log update --branch <branch> --pr <url> --status in-review`. Show the PR and its commits as links, as `~/.claude/skills/github-links/skill.md` says.
   - If Phase 8a saved screenshots, ask: "Attach the screenshots to <PR>?" After a yes, run `/make-curl-png --pr <url>` with the same requests.
8. Start the merge check at once, with no question. Run this with Bash `run_in_background`:

   ```bash
   while s=$(~/.claude/skills/work-log/worklog.py merged --branch <branch>) && [ "$s" = no ]; do sleep 3600; done; echo "${s:-error}"
   ```

   The loop uses no model tokens until it exits, and it stops when the session closes. When it exits:
   - `yes`: send a PushNotification `<TICKET> merged`, and start Phase 9.
   - `closed`: tell the user that the PR is closed without a merge. The entry is now `abandoned`.
   - `error`: show the error of the script. Do not start the loop again.

### Phase 8a — Local Docker test ⟨ph:c4c549b2⟩

Phase 8 step 5 runs this phase. Run it after the reviews, because a defect on the running stack must not reach `/create-pr`, and the unit tests mock the request binding, the middleware, and the flag client.

1. Skip the phase, and give the reason in the ready report, if either of these is true:
   - The change touches only docs, CI, or config.
   - `~/.claude/skills/docker-test/rules/<repo>.local.md` does not exist. `<repo>` is the last part of `git remote get-url origin`, without `.git`.
2. From the worktree, run `/docker-test <what is tested>`. Name each acceptance criterion and each new error case in `<what is tested>`.
   - If the change adds a feature flag, test the flag on and off. Use the local flag setting that the rules file names. If it names none, ask the user.
   - If another session holds the lock, ask whether to wait (`--wait`) or skip. In an automated run, skip the phase and report it.
3. If a test fails, STOP. Show the failure, fix it, and run the full suite with the test stamp rules. Then run Phase 8 again from step 1, because the fix changes the reviewed content.
4. Save the proof: run `/make-curl-png --no-attach` for one or two representative requests, for example one success and one new error case. Keep the PNG paths for the ready report.

### Phase 9 — After the merge ⟨ph:8c9baf91⟩

Start this phase when the merge check prints `yes`, or when the user says that the PR is merged or asks to run the dev tests. If the merge check still runs, stop it with TaskStop.

1. Run `/work-log status`. It reads the PR state from GitHub, sets the branch to `merged`, and records the transition.
2. If the entry is still not `merged`, tell the user that GitHub does not show the PR as merged. If the user confirms the merge, run `/work-log update --branch <branch> --status merged`.
3. If the user already asked for the dev tests, go to step 4. Otherwise ask:

   > Run the full tests on dev? `/test-on-dev <service> <ticket>` tests the acceptance criteria, then `--random` tests the change. (yes / no)

   `<service>` is the name of a file in `~/.claude/skills/test-on-dev/services/`, from the repo name. If no file matches, ask for the service.
4. Run `/test-on-dev <service> <ticket>`, then `/test-on-dev <service> --random` from the ticket's branch, so the exploratory tests read the merged diff. Report both results.
5. If no test fails, run `/work-log update --branch <branch> --status dev-tested`, and go to Phase 10. A `blocked` test does not stop this, but name it in Phase 10. If a test fails, keep the status `merged`, show the failure, and ask how to continue.

### Phase 10 — Prod checks ⟨ph:ba1a965d⟩

Start this phase after Phase 9, or when the user resumes an entry that is `dev-tested`.

1. Read `prod-checks.md` in this skill directory, and write the prod checklist from it.
2. Show the checklist, and ask:

   > Run these checks when the change is on prod, then tell me the result of each one.

   STOP and WAIT.
3. If the user reports that each check passes:
   1. Run `/work-log update --branch <branch> --status prod-tested`.
   2. Ask: "Move <TICKET> to done?" After a yes, use the Done row in "States" of the tracker adapter.
4. If a check fails, keep the status `dev-tested`. Help find the cause with `/get-gcloud-logs`, or `/investigate-incident` for an incident. Give the rollback step of the checklist.

## Automated runs — scope guard

A run is automated when no user is present: headless (`claude -p`), background (`--bg`), cron, or a call from another skill or agent. An automated run changes only the worktree of this ticket, because no reviewer sees a wrong write outside it.

- Get the worktree path with `git rev-parse --show-toplevel`. Before each write, check that the full file path starts with it.
- Run `git` only in that worktree. Push only the branch of this ticket. NEVER force-push.
- Do not touch `~/.claude`, settings, skills, other repositories, other worktrees, or the main checkout. The only exception is the work log, through `/work-log`.
- If a step needs a path outside the worktree, skip the step, report it, and stop. Ask no question.

## Other rules

- Follow the Rules of the tracker adapter on every tracker call.
- When you push more commits to an open PR, for example after a follow-up change or a review fix, report each new commit as a link, as `~/.claude/skills/github-links/skill.md` says.

## PR description

Keep the working copy of the PR description in `/tmp/pr-body/<owner>-<repo>/<branch>.md`. Replace each `/` in the branch name with `-`. Get `<owner>-<repo>` with `gh repo view --json nameWithOwner -q .nameWithOwner | tr / -`.

After each push to an open PR:

1. Write the current body from GitHub to the working copy, with `mkdir -p` first: `gh pr view <pr> --json body -q .body > <file>`. ALWAYS start from GitHub, because a person can edit the description there.
2. Read the commits of the push and their diff. Edit the working copy with Edit:
   - Add each new change to the section where it belongs.
   - Remove or correct each line that the push makes wrong, for example a removed function, a renamed term, or a changed value or example.
   - Keep each line that is still true, and the attribution and ticket lines at the end.
3. If the working copy changed, run `gh pr edit <pr> --body-file <file>`.
4. Report one line: `PR description: <what changed>`, or `PR description: still current`.

## Examples

- `/implement-ticket PROJ-1234`
- `/implement-ticket https://linear.app/<workspace>/issue/PROJ-1234/some-slug`
- `/implement-ticket add page_number pagination to the positions resolver`
- `/implement-ticket PROJ-1234 focus only on the Kafka handler, skip the gRPC layer`
- `/implement-ticket` ← asks for an issue or a description

## Retry

Say **"retry"** to start again. Fetch the issue again, explore the code again, and use no earlier plan or notes.
