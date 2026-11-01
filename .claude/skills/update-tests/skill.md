---
name: update-tests
description: Updates the Python tests for a change — fixes failing tests and writes the missing ones for staged changes, the last commit, or the whole branch. Interactive by default; --auto runs with no questions. Use for "/update-tests", "write tests for this", or "fix the failing tests".
user-invocable: true
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(git *), Bash(poetry *), Bash(pytest *), Bash(python -m pytest *), Bash(make *), Bash(~/.claude/skills/verify-stamp/stamp.sh *)
model: sonnet
---

# Update Tests

Find the tests that a change affects, fix the failing ones, and write tests for each new code path.

## Hard rules

- Change only test files. NEVER change source code. Flag a source bug instead.
- Fix failing tests before you write new ones. Preserve the intent of each test.
- Write tests only for code in the scope of the change.
- Write one test, run it, then write the next. Try at most 3 times for each test, then ask (interactive) or report it (`--auto`).
- Follow the patterns of the existing tests: fixtures from `conftest.py`, mocking, assertions, imports, and names. NEVER guess how a fixture works; read it.
- Interactive mode: NEVER go from the analysis to writing code without the user's direction.
- NEVER script code changes (`sed -i`, `awk`, `perl -pi`, `python`, heredocs). Use Edit and Write only, one clear change at a time. Scripts are fine for reading code.

## Arguments

| Argument | Effect |
|---|---|
| *(none)* | Staged changes. If nothing is staged, the last commit. |
| `--last-commit` | The last commit, even if changes are staged |
| `--branch [<base>]` | All changes on the branch: `git diff <base>...HEAD`. The default base is the default branch of `origin`. |
| `<file>` | Only this source file |
| `--auto` | No checkpoints: fix all failing tests, write all missing tests, consolidate, and report |
| `--coverage` | Add a coverage report (`--cov=<module>`) to the final run |
| `--dry-run` | Run Phase 1 only, and change nothing |

## Phase 1 — Analyze

1. **Read the change.** Default: `git diff --cached --name-only` and `git diff --cached`. If that is empty, or with `--last-commit`: `git show HEAD --name-only --oneline` and `git show HEAD -p`. With `--branch`: `git diff <base>...HEAD`. Record the new, changed, and removed functions, the changed signatures, and the changed logic. Leave out test files.
2. **Find the tests.** For `pkg/foo/bar.py`, look for `tests/foo/test_bar.py` or `tests/test_bar.py`. Read similar existing tests as a model. Also read `git diff -- tests/`, so you do not repeat tests that the user already wrote.
3. **Map each change to coverage:**

   | Change | Check |
   |---|---|
   | New function or method | Do tests exist? |
   | New branch, loop condition, or state transition | Is each path tested? |
   | New `try/except`, validation, or error condition | Is each failure tested? |
   | New parameter, return value, or config option | Is it asserted? |
   | Edge cases | Empty input, `None`, boundaries |
   | New external call | Are the call arguments asserted? |
   | Removed method or property | Are its old tests removed? |
   | Renamed field or changed formula | Are the assertions and expected values updated? |

   For each function, plan the happy path, the edge cases, the error cases, and the integration points (database, external APIs, files).
4. **Flag source bugs**, for example a missing required argument or a type mismatch. Do not fix them.

## CHECKPOINT 1 (interactive mode)

```
## Changes Analysis (<staged | last commit: <hash> | branch vs <base>>)

| File | Changes |
|------|---------|

**Test files found:** <list>

## Already Written
<test changes that the user already made>

## Failing Tests
| Test | File | Failure Reason |
|------|------|----------------|
(or "None — not run yet")

## Missing Test Coverage
### 1. `function_name()` — summary
| Test Case | Description |
|-----------|-------------|

## Source Code Issues
- <potential bug>

| Category | Count |
|----------|-------|
| Tests already written | N |
| Failing tests to fix | N |
| New tests needed | N |
| Source issues flagged | N |
```

Ask: "What should I do next? Fix the failing tests, write specific tests (which?), write all missing tests, run the existing tests first, or something else?" WAIT. With `--auto`, continue at once with all of them.

## Phase 2 — Fix and write

**Fix a failing test** with the smallest change:

| Failure | Fix |
|---|---|
| Assertion error from changed behaviour | Update the expected value |
| Missing mock | Add or update the mock |
| Changed signature | Update the call |
| Removed code | Remove or update the test |

Then run it: `poetry run pytest tests/path/test_file.py::test_name -v`.

**Write a new test** for one behaviour, as a top-level function (no test classes), named `test_<function>_<scenario>`:

```python
async def test_function_scenario(fixtures):
    # GIVEN
    ...
    # WHEN
    result = await function_under_test(...)
    # THEN
    assert result == expected
```

Use the existing fixtures, and create a new one only if no fixture fits. Mock external dependencies. Run each test right after you write it.

If a test still fails after 3 attempts, or it shows a source bug:
- **Interactive:** stop, and ask, with this format:
  ```
  ⚠️ Need Help
  Test: `test_calculate_total_with_discount` — File: `tests/billing/test_totals.py`
  Issue: the test expects the discount before tax, but the change applies tax first.
  Options: 1. Update the test to the new behaviour  2. This is a bug in the change  3. Skip this test for now
  ```
- **`--auto`:** leave the tests of that function out, and list the issue in the final report.

Also ask (interactive) or report (`--auto`) if you cannot understand the intent of a test, or if it needs a complex refactor.

## CHECKPOINT 2 (interactive mode)

```
## Done

**Tests fixed:** N
- test_name — what was changed

**Tests added:** N
- test_name — what it covers

**Tests passing:** ✅ / ❌
```

Ask: "Write more tests, consolidate, run the full suite, or done?" WAIT.

## Phase 3 — Consolidate (on request, or always with `--auto`)

Read `consolidate.md` in this skill directory, and follow it.

## Phase 4 — Final run (on request, or always with `--auto`)

1. Run the tests of each affected file: `poetry run pytest tests/path/test_file.py -v`, with `--cov=<module>` if `--coverage` is given.
2. Run the full suite with the test stamp rules in `~/.claude/skills/verify-stamp/skill.md`: `check tests` first, and skip the run if it prints `FRESH`. After the run, `record tests passed|failed`.

With `--auto`, end with:

```
✅ Tests: <N> fixed, <M> added, <K> passing
⚠️ Left out: <function> — <source bug or 3 failed attempts>     (only if any)
Full suite: <passed | failed | reused (FRESH)>
```

## Examples

- `/update-tests` ← staged changes, interactive
- `/update-tests pkg/billing/totals.py`
- `/update-tests --auto --branch` ← all branch changes, no questions (used by `/solve-*` and `/dev-loop`)
- `/update-tests --dry-run`

## Retry

If the user says "retry", reuse nothing from the earlier run. Read the change, the source files, and the test files again, and run the workflow from Phase 1.
