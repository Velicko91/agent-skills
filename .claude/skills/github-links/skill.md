---
name: github-links
description: The rule for linking commits and PRs to GitHub in reports to the user, so the user can open and review them. Used by other skills.
user-invocable: false
disable-model-invocation: true
---

# GitHub links

A report to the user that names a commit or a PR links it, so the user can open it and review it.

## Build the links

1. Get `<owner>/<repo>`:
   ```bash
   gh repo view --json nameWithOwner -q .nameWithOwner
   ```
2. Get the full SHA and the subject of each commit, oldest first:
   ```bash
   git log --reverse --format='%H %s' <base>..HEAD
   ```
3. Write each commit as `[<short sha>](<url>) <subject>`:

   | The commit | URL |
   |---|---|
   | is in a PR | `https://github.com/<owner>/<repo>/pull/<n>/commits/<full sha>` |
   | is in no PR | `https://github.com/<owner>/<repo>/commit/<full sha>` |

4. Write a PR as `[#<n>](<PR url>)`.

## Rules

- Link a commit only after it is pushed, because GitHub gives 404 for an unpushed SHA. If `git branch -r --contains <sha>` prints nothing, write `<short sha> (not pushed)` with no link.
- List the commits oldest first.

## Example

```
PR: [#62](https://github.com/acme/api/pull/62)
1. [`1a2b3c4`](https://github.com/acme/api/pull/62/commits/1a2b3c4d5e6f708192a3b4c5d6e7f80912a3b4c5) feat: add cursor pagination
2. [`9f8e7d6`](https://github.com/acme/api/pull/62/commits/9f8e7d6c5b4a39281706f5e4d3c2b1a098f7e6d5) fix: reject a reused page token
```
