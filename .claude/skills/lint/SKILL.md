---
name: lint
description: Runs the project's formatter and linter, fixes what they report, and with --commit commits only the formatter's own changes. Use for "/lint" or "fix the lint errors".
allowed-tools: Bash(make *), Bash(git *), Bash(poetry run *), Bash(uv run *), Bash(npm run *), Bash(npx --no-install *), Read, Grep, Glob, Edit
model: haiku
---

# Lint

Run the formatter and the linter of the project, and fix the issues that they report.

## Hard rules

- NEVER use `git add -A` or `git add .`. Stage files by name, because other work can be in the tree.
- With `--commit`, commit only the files that the formatter changed **and** that had no other change before it ran. Report the others; do not commit them.
- Use only tools that the project has. Run `npx --no-install`, so `npx` never downloads a package.
- Try at most 5 rounds of fixes. Then stop, and report what is left.
- If another skill started this skill, or no user is present, report the remaining issues. Do not ask.

## Arguments

| Flag | Effect |
|---|---|
| *(none)* | Format, lint, and fix |
| `--format-only` | Format only |
| `--lint-only` | Lint and fix, with no formatting |
| `--no-fix` | Change nothing: run the checks, and report |
| `--commit` | After formatting, commit the formatter's own changes (see Hard rules) |
| `--verbose` | Show the full tool output |

## Workflow

### Step 1 — Find the commands

Read the `Makefile`, and look for the targets `format`, `lint`, `mypy`, and `check`. Prefer them. Without a `Makefile` target, use the tool that the project configures:

| Project | Format | Lint |
|---|---|---|
| Python, poetry | `poetry run ruff format .` | `poetry run ruff check .`, `poetry run mypy .` |
| Python, uv | `uv run ruff format .` | `uv run ruff check .`, `uv run mypy .` |
| JavaScript/TypeScript | `npm run format`, or `npx --no-install prettier --write .` | `npm run lint` |

If the project has neither a target nor a configured tool, say so, and stop.

### Step 2 — Format (unless `--lint-only` or `--no-fix`)

1. Record the files that already have changes: `git diff --name-only` and `git diff --cached --name-only`.
2. Run the formatter.
3. The files in `git diff --name-only` that were not in the list of step 1 are the formatter's own changes.

With `--no-fix`, run the formatter in check mode instead (for example `ruff format --check`), and only report.

### Step 3 — Commit the format changes (only with `--commit`)

Stage the formatter's own changes by name, and commit them:

```bash
git add <file> <file>
git commit -m "style: apply formatting"
```

If the formatter also changed a file that had other changes before, do not commit it. List it in the report, because its commit would include work that is not formatting.

### Step 4 — Lint (unless `--format-only`)

Run `make lint`, or the lint command of Step 1. If it passes, go to Step 6.

### Step 5 — Fix (unless `--no-fix`)

1. Run the auto-fix first, if the linter has one: `poetry run ruff check . --fix` (or `uv run …`), or `npm run lint -- --fix`.
2. Fix the rest with Edit. Read the file, and apply the fix that the message describes:

   | Error | Fix |
   |---|---|
   | Unused import | Remove it |
   | Line too long | Break it into lines |
   | Type mismatch | Add an annotation, or a cast if the types really match |
   | Undefined name | Add the import, or fix the typo |
   | Missing return type | Add the annotation |

3. Run the linter again. Repeat at most 5 rounds.

Typical messages: `file.py:123:45: F401 'os' imported but unused` (ruff), `file.py:123: error: Argument 1 has incompatible type "str"; expected "int"` (mypy), `file.js:123:45: error 'foo' is not defined (no-undef)` (ESLint).

### Step 6 — Report

```
✅ Lint passed — format: <N> files changed, <M> committed
```

or

```
❌ Lint failed — unresolved after 5 rounds:
- [file:line] <issue> — <fixable | configuration | false positive>
```

Name each issue's kind: **fixable** (a code change), **configuration** (a change in `pyproject.toml` or `.eslintrc`), or **false positive** (it should be suppressed). In an interactive run, ask how to continue. If another skill started this skill, return the report only.

## Examples

- `/lint`
- `/lint --format-only`
- `/lint --no-fix`
- `/lint --commit` ← used by `/create-pr`
