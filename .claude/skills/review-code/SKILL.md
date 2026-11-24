---
name: review-code
model: opus
description: Reviews staged changes, or a whole branch with --branch, as a domain expert — applies nits and simple cleanups, and reports only what needs a decision: alternatives, architecture, domain logic, and issues. Use for "/review-code", "review my changes", or "review this branch".
user-invocable: true
allowed-tools: Bash(git *), Read, Grep, Glob, Edit
---

# Code Review

Review the changes as an expert in the domain and the language. **Fix the small things, and report the big things.** Report only the findings that need the user's decision.

## Hard rules

- Never fix domain logic: business rules, money, quantities, states and transitions, validation, permissions. Report it, because the user owns the rule.
- Never run `git add`, `git commit`, `git stash`, or `git checkout`, because they change the user's work. Leave each fix unstaged.
- If you are not sure whether a finding is a fix, report it. A wrong fix costs more than one extra line in the report.
- Be opinionated, specific, and practical. Pick a recommendation and justify it, with file paths, line numbers, and names. Prefer the patterns of the code base unless there is a strong reason.
- Write a phase marker when each phase starts, as `~/.claude/skills/phase-markers/SKILL.md` says. The ID is the `⟨ph:…⟩` on the phase heading.

## Arguments

`$ARGUMENTS` holds a review type and an optional scope. Combine types with `+`, for example `arch+alternatives` or `issues+report-only`.

| Type | Sections |
|---|---|
| *(empty)* / `full` | A–F |
| `rules` | F only |
| `arch` | B only |
| `alternatives` | A only |
| `best-practices` | C only |
| `comments` | D only |
| `issues` | E only |
| `quick` | One list of the top 3 observations, with no headings. Give each a location and one point. |
| `report-only` | Apply no fix. Report every finding, also the small ones. |

| Scope | Diff |
|---|---|
| *(default)* | Staged changes. If nothing is staged, unstaged changes. |
| `--branch [<base>]` | All changes since the branch left `<base>`: its commits, and the staged and unstaged changes. The default base is the default branch of `origin` (usually `main`). |

Fix only the categories in scope. `full` and `quick` fix all categories.

## Workflow

### Step 1 — Collect the changes ⟨ph:e6b8f365⟩

- Default: `git diff --cached --name-only`, `--stat`, and the diff. If nothing is staged, use `git diff`. If there are no changes at all, say so and stop.
- `--branch`: find the base with `git remote show origin | grep "HEAD branch" | sed 's/.*: //'` if none is given. Get the merge base with `git merge-base <base> HEAD`, where `<base>` gets an `origin/` prefix if it has none, then read `git diff <merge-base> --name-only`, `--stat`, and the diff. This compares the working tree with the merge base, so it includes commits, staged, and unstaged changes, also before the first commit.

Name the scope in the first line, so the reader knows what a clean review covers: `Scope: staged changes — 4 files, 212 lines.` or `Scope: branch vs main — 9 files, 640 lines.`

### Step 2 — Read the full context ⟨ph:4d093407⟩

Read each changed file in full, not only the diff. Also read the files that import it or that it imports, its parent classes and interfaces, and the config or enum files that the change uses.

Read the repo rules for Section F:
1. Find each `AGENTS.md` and `CLAUDE.md` in the repo root, and in each folder from the root down to a changed file.
2. Read each file that they import with `@<path>`.
3. Number the rules `R1`, `R2`, …, one for each top-level bullet or numbered item. A sub-bullet belongs to its parent rule.

### Step 3 — Triage each finding ⟨ph:c68db7bb⟩

Read `checklist.md` in this skill directory, and apply it with Sections A–E. Section F has its own fix rule.

**Fix** a finding now only if all of these are true:
- It changes only lines that the diff adds or changes.
- It does not change behaviour: the same inputs give the same outputs, errors, and side effects.
- It has one obvious correct form, so two reviewers would write the same fix.
- It needs no domain knowledge.

Typical fixes: formatting, import order, typos in names, strings, and comments; an unused import, variable, or parameter that the diff adds; redundant code such as `if x: return True else: return False`; a missing type hint where the type is clear; a simple idiom (a comprehension, `enumerate`, `dict.get`); a comment fix (Section D); a helper in a scope that is too narrow (Section B).

**Report** a finding if any of these is true:
- It needs a bigger change: more than one function, a public interface, a schema, or a migration.
- It touches domain logic.
- A credible alternative can be better, with a trade-off for the user.
- It changes behaviour, also if it is a bug fix.

With `report-only`, every finding goes in the Report group.

### Step 4 — Apply the fixes ⟨ph:2e08a5d1⟩

Apply each fix with Edit, and leave it unstaged. The user sees the fixes with `git diff`, and the original change with `git diff --cached`. If the review used unstaged changes, say that the fixes mix with the user's work.

### Step 5 — Write the review ⟨ph:ce94dfd5⟩

Start with the applied fixes, one line each, or `No fixes applied.`:

```
### Applied fixes (unstaged — see `git diff`)
- `path/to/file.py:42` — remove the unused import `Optional`
- `path/to/file.py:88` — shorten the 5-line comment to 2 lines
```

Then write each section in scope, in this order, with Report findings only. Leave out the sections that are not in scope. If a section in scope finds nothing, write its heading and one line, for example `No architecture concerns.`, because a missing section reads as forgotten work.

Give every reported finding a location `path/to/file.py:120` on the new side of the diff, so a caller can anchor it to a line.

#### Section A — Alternatives

For each important design choice, write what was done in one line, then one or two alternatives with a short code sketch and pros and cons, then a verdict for this code base. Look at data modelling (inheritance vs composition, enums vs lookup tables), control flow (state machines vs if-chains, strategy vs switch), integration (sync vs async, polling vs events, retries), and API design (endpoints, payload shape, errors). Show only an alternative that can be better.

#### Section B — Architecture

Show only the concerns rated **Needs attention** or **Problem**:
- **Responsibility** — does each module or class have one clear purpose?
- **Coupling** — are the dependencies explicit and minimal?
- **Extensibility** — how easy is a second broker, a new asset type, another event handler?
- **Data flow** — is the path from input to persistence to event clear and auditable?
- **Error boundaries** — where do failures propagate? Is a fallback missing?
- **Consistency** — does the change follow the patterns of the code base?
- **Consolidation** — can near-duplicate blocks be one function, repeated literals a constant, branches one expression? Does the change re-implement a helper that exists? Name what merges with what.
- **Scope of reuse** — see the check below.

**Check: scope of reuse.** Find each function, class, or constant that the diff adds inside one endpoint, resolver, handler, or service class. It is too narrow if it does not depend on the endpoint (no request object, endpoint state, or endpoint-only model), and other endpoints can use it or have a copy.

1. Grep for its name and a key line of its body, to find copies.
2. Grep for the same operation in other endpoints: the same query, conversion, or validation.
3. Glob for the shared modules: `utils/`, `common/`, `shared/`, `core/`, `lib/`.

Choose the target: an existing shared file with helpers of the same kind (the default), else a new file in the shared package named for what its helpers do (never `misc` or `helpers`). If there is no shared package, report it, because a new package is a design decision.

Move the helper as a fix if the diff adds it, the target file exists, only the location and the imports change, and it has no domain logic. Update every affected import. In all other cases, report it with the shared module, the endpoints that can use it, and the new signature.

#### Section C — Best practices

Python: type hints, async patterns, SQLAlchemy 2.0 idioms, Pydantic validation, enums. FastAPI and Strawberry: dependency injection, resolver patterns, error responses. General: naming, immutability, defensive code, logging, testability. Fix the simple ones. Report only the practices that need a bigger change, and show the current and the recommended pattern side by side.

#### Section D — Comments

Check each comment that the diff adds or changes.

**The limit is two lines.** Fix each comment of three lines or more. One `#` block, consecutive `//` lines, one `/* */` or `<!-- -->` block, or a `"""..."""` note inside a function body is one comment. The limit does not apply to module, class, or function docstrings, license headers, generated-file headers, or pragma lines (`# noqa`, `# type: ignore`, `# pragma: no cover`).

Rewrite a long comment as the same point in two lines or fewer. If the knowledge does not fit, move it to a docstring in the same file. If it belongs in a design document, the commit message, or the ticket, report where. Never delete knowledge; move it.

**Fix each comment that repeats an explanation from somewhere else**, because two copies drift apart. Before you accept a comment, Glob for `README*` and `docs/**` next to the file, Grep for a key phrase of the comment, and read the docstring of the class or method.

| The explanation covers | It belongs in | Delete the copy in |
|---|---|---|
| What the module or package is for | The README | The inline comment |
| What the class holds and how to use it | The class docstring | The comment above the class body |
| What the method does, its arguments, its return value | The method docstring | The comment above the first statement |
| Why one line is written this way | The inline comment | Nowhere |

If the copy to delete is outside the diff, report it. Also delete a comment that only restates the code, and commented-out code, because git holds the old version. Report a comment that contradicts the code, and a `TODO` with no ticket id. If there is nothing, write `No comment issues.`

#### Section E — Issues

List the reported issues by severity:
1. **Critical** — bugs, data corruption risks, security holes, race conditions
2. **Major** — logic errors, missing error handling, performance traps, wrong assumptions
3. **Minor** — unclear naming of a domain concept, a missing test for a domain rule, other small issues that need a decision

For each one, give the location, quote the code, explain the problem, and suggest a fix. Do not apply it.

#### Section F — Repo rules

Check each rule from Step 2 against the diff. List every rule, also the ones that do not apply, so the reader sees that none was skipped:

```
| # | Rule (short) | Source | Status | Evidence |
|---|---|---|---|---|
| R1 | Verify with `make lint` and `make test` | AGENTS.md:5 | 📋 PR step | Run both before /create-pr |
| R2 | New public field → sandbox CSV + loader | AGENTS.md:10 | ❌ broken | `api/v1/openapi.yaml:812` adds `fields`; no change in `sandbox/` |
| R3 | `x-enum-varnames` on a new enum | AGENTS.md:11 | ✅ followed | `api/v1/openapi.yaml:840` |
| R4 | Audit trail on every write | AGENTS.md:16 | ➖ n/a | The diff adds no write |
```

| Status | When |
|---|---|
| ✅ followed | The diff does what the rule asks. Give the location. |
| ❌ broken | The diff does not. See "Fix a broken rule" below. |
| 📋 PR step | The rule asks for an action outside the code, for example a command to run, a line in the PR description, or a flag to create. Say what to do. |
| ➖ n/a | The diff touches nothing that the rule covers. Give the reason in a few words. |

**Fix a broken rule.** Fix it, also if the fix is larger than the Step 3 fix rules allow, for example a missing sandbox row or a missing `x-enum-varnames`. The repo owners already decided the rule, so the fix needs no decision. List it under Applied fixes, and mark the row `❌ → fixed`.

Do not fix it, and report it, if either of these is true:
- The rule does not fit this change, for example it was written for a different case. Say why.
- The fix changes the design: a public interface, a database schema, a migration, the module structure, or domain logic (Hard rules). Say what the fix needs.

Then ask how to continue, with the options, for example "add the audit entries in the handler, or skip the rule for this read-only path?". STOP and WAIT. With `report-only`, or in an automated run (headless `claude -p`, `--bg`, cron, or a call from an autonomous skill or agent such as `/dev-loop`), do not ask: report each such broken rule as a **Major** issue in Section E, so the caller treats it as blocking.

Also report:
- **A stale rule:** a rule names a file, a command, or a pattern that the code no longer has. Give the rule and what changed.
- **A missing rule update:** the diff adds or changes a convention that a rule describes. Name the rule file and the line to change.

### Step 6 — Summary ⟨ph:7affeec1⟩

```
## Summary

**Overall**: <one sentence>

**Strongest aspect**: <what is done well>
**Biggest opportunity**: <the most important improvement>
**Repo rules**: <followed>/<applicable> followed, <broken> broken, <PR steps> PR steps
```

Then offer: "Say **retry** for a fresh review after changes, or ask for another focus, for example `/review-code arch`."

## Examples

- `/review-code` ← staged changes, full review
- `/review-code issues+report-only`
- `/review-code --branch` ← the whole branch, committed or not, vs the default branch
- `/review-code full+report-only --branch origin/main` ← used by `/create-pr` and `/github-review`

## Retry

If the user says "retry", use no cached data. Read the diffs, the source files, and the related files again, and run the workflow from Step 1.
