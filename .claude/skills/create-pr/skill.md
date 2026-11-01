---
name: create-pr
description: Creates a GitHub pull request for the current branch — reviews the diff and test coverage, runs lint and tests, then opens a draft PR with a short Why/What body and requests the Copilot review. Use for "/create-pr", "open a PR", or "create a pull request".
allowed-tools: Bash(git *, gh *), Bash(make *), Bash(poetry *), Bash(uv *), Bash(npm *), Bash(~/.claude/skills/verify-stamp/stamp.sh *), Bash(~/.claude/skills/safe-push/push.sh *), Read, Edit, Grep, Glob, Agent, Skill
---

# Create Pull Request

Review the branch, run the checks, then open a pull request.

## Hard rules

- NEVER give a decision to the `pr-author` subagent, because it runs a cheaper model. You review the code, fix what breaks, and decide the PR type.
- NEVER put a test count, a coverage number, or a file list in the PR description. Report them to the user.
- NEVER invent the `Why` section. Omit it if no ticket, branch, or commit gives the reason.
- NEVER use `git add .` or `git add -A`. Stage files by name.
- NEVER guess a tracker host. If the host is unknown, omit the ticket link.
- Write a phase marker when each phase starts, as `~/.claude/skills/phase-markers/skill.md` says. The ID is the `⟨ph:…⟩` on the phase heading.

## Arguments

| Flag | Effect |
|---|---|
| *(none)* | Draft PR, with the full review, the checks, and the Copilot request |
| `--ready` | A regular PR. This is the only way to skip draft. |
| `--draft` | Draft. It is already the default. |
| `--no-copilot` | Skip the Copilot review request |
| `--no-delegate` | Run every step on the session model |
| `--skip-code-review` | Skip Step 2 |
| `--no-review` | In Step 3, check only that test files exist |
| `--skip-tests` | Skip Step 3 |
| `--skip-checks` | Skip Step 4 |
| `--skip-format`, `--skip-lint`, `--skip-pytest` | Skip one part of Step 4 |

## Local configuration

Read `~/.claude/config.local.json` for `jira.host` and `linear.workspace` before you build a ticket link. If it is missing, copy `config.example.json` and ask the user.

## Model split

| Work | Runs on |
|---|---|
| Read the diff, review the code and the test coverage (Steps 1–3) | Session model |
| Run lint and tests, and fix what breaks (Step 4) | Session model |
| Write the title and body, push, create the PR, request and verify Copilot (Step 5) | `pr-author` subagent (Haiku) |

To change the subagent model, edit `model:` in `~/.claude/agents/pr-author.md`.

## Workflow

### Step 1 — Read the branch ⟨ph:3d669dd6⟩

1. Find the base branch: `git remote show origin | grep "HEAD branch" | sed 's/.*: //'`.
2. Read `git log <base>..HEAD --oneline`, `git diff <base>..HEAD --stat`, and the diff.
3. Take the type and the ticket from the branch name `{type}/{ticket}-{description}`, for example `feat/PROJ-123-add-pagination` → `feat`, `PROJ-123`. Also accept the old forms `feature/PROJ-123-...` and `bugfix/123-...`.
4. Build the ticket link: Jira `https://<jira.host>/browse/<ticket>`, Linear `https://linear.app/<linear.workspace>/issue/<ticket>`.

If you create a new branch, use `{type}/{ticket}-{description}`. `type` is one of `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`, `ci`, `build`, `revert`.

### Step 2 — Code review ⟨ph:56881fc0⟩

Run `~/.claude/skills/verify-stamp/stamp.sh check review`. If it prints `FRESH`, an earlier step (for example `/implement-ticket`) reviewed this exact content with no Critical or Major issue. Skip Steps 2 and 3, and report `review: reused — clean on this exact content at <date>`.

Otherwise run `/review-code full+report-only --branch <base>`. If it reports no Critical or Major issue, run `stamp.sh record review clean`; else run `stamp.sh record review blocking`.

If it reports critical or major issues, list all issues with numbers, grouped by severity:

```
## Code Review Issues

### Critical
1. **[orders.py:143]** `payload` may not be defined if the download fails

### Major
2. **[orders.py:144]** Use `raise` instead of `raise e` to keep the traceback

### Minor
3. **[test_orders.py:516]** Redundant pytest import (already at module level)
```

Then ask:

```
Which issues should I fix before creating the PR?
- "all", "critical", or numbers such as "1,2"
- "skip" to continue without fixes
- or your own instructions
```

STOP and WAIT. Fix the selected issues, review again, and continue only when the user approves.

### Step 3 — Test coverage ⟨ph:2a2001d2⟩

Skip this step for changes to documentation, configuration, or CI only. Report the result to the user in Step 6, never in the PR.

1. List the changed source files without tests:
   ```bash
   git diff <base>..HEAD --name-only | grep -E "\.py$" | grep -v -E "(test_|_test\.py|/tests/|conftest)"
   ```
2. In each file, find the classes, the methods, and the module functions: `grep -n -E "^class |^    def |^def " <file>`.
3. Find the test file: `tests/<path>/test_<module>.py` or `tests/test_<module>.py`. Search it for `def test_*` and `async def test_*` that cover each name.
4. Make two lists: ✅ covered and ❌ missing.

### Step 4 — Lint and tests ⟨ph:7a35db17⟩

1. Run `/lint --commit`. If you cannot run the skill, follow its workflow.
2. Run the full test suite with the test stamp rules in `~/.claude/skills/verify-stamp/skill.md`: `check tests` first, and skip the run if it prints `FRESH`. Else run `make test` if it exists, or the runner of the project, for example `poetry run pytest`, then `record tests passed|failed`. If lint changed files, the stamp is stale, and the suite runs.
3. If a test fails, fix it, run `/lint` again, and run the suite again with the same rules.
4. If fixes leave changes, check `git status --porcelain`, stage the changed files by name, and commit them with `style: apply formatting`.

### Step 5 — Open the PR ⟨ph:7a0952a9⟩

The PR is a draft unless the user passed `--ready`. The test results never change the PR type.

Give the work to the `pr-author` subagent:

```
Agent(
  subagent_type: "pr-author",
  description: "Write and open the PR",
  prompt: "Base branch: <base>
           PR type: draft | ready
           Ticket: <id and link, or none>
           User instructions: <anything the user asked for, or none>
           Copilot review: request | skip"
)
```

It returns JSON with `url`, `draft`, `title`, `body`, `copilot`, and `warnings`.

If the user passed `--no-delegate`, or the subagent fails, do Steps 1–7 of `~/.claude/agents/pr-author.md` yourself. Report which path ran.

If the subagent returns a `CONFLICT_REMOTE` or `CONFLICT_BASE` warning from `push.sh`, resolve the conflict with "Resolve a conflict" in `~/.claude/skills/safe-push/skill.md`: automatically when you can, and ask only when it says that you cannot resolve it. Then run Step 5 again, and list the resolved files in the Step 6 report.

### Step 6 — Report ⟨ph:3f36bb50⟩

Report in the terminal, not in the PR:

1. The PR URL, and draft or regular
2. The Copilot result: confirmed by `gh pr view --json reviewRequests`, or the reason it is not
3. The classes and methods that still need tests (Step 3)
4. Each warning: a diff over 500 lines, a sensitive file (`.env`, credentials, secrets), or a model change with no migration
5. Whether the `pr-author` subagent or the session model opened the PR

Then offer: "If you change something and want a fresh run, say **retry**."

## Examples

- `/create-pr` ← draft PR with the Copilot review
- `/create-pr --ready` ← regular PR
- `/create-pr --no-copilot --skip-tests`
- `/create-pr --no-delegate` ← every step on the session model

## Retry

If the user says "retry", use no cached data. Read the diffs, commits, and test files again, and run the workflow from Step 1.
