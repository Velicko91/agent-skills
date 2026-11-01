---
name: post-pr-comment
description: Posts one comment, prefixed "Claude AI:", on a GitHub pull request. Use for "/post-pr-comment <number> <text>" or "comment on PR 123 that …".
allowed-tools: Bash(gh pr comment *), Bash(gh pr view *)
model: haiku
---

# Post PR Comment

Post one comment on a pull request.

## Hard rules

- Start every comment with `Claude AI:` on the first line, so readers know that an AI wrote it.
- Pass the text on stdin with a quoted heredoc and `--body-file -`. NEVER put the text inside `--body "…"`, because a `"` breaks the command, `$VAR` is replaced, and backticks or `$(…)` run as commands.

## Arguments

```
/post-pr-comment <PR number or URL> <comment text> [--repo owner/repo]
```

Without `--repo`, the PR is in the current repository.

## Workflow

1. Take the PR and the text from `$ARGUMENTS`. If one is missing, ask for it.
2. Post it:
   ```bash
   gh pr comment <PR> [--repo owner/repo] --body-file - <<'EOF'
   Claude AI: <comment text, exactly as given>
   EOF
   ```
3. Report the comment URL that `gh` prints. If `gh` fails, report its error.

## Examples

- `/post-pr-comment 123 LGTM! Great work on the refactor.` → posts `Claude AI: LGTM! Great work on the refactor.`
- `/post-pr-comment 456 Please add a test for \`parse_amount()\`.` → the backticks stay as text
- `/post-pr-comment https://github.com/acme/api/pull/42 Rebased on main.`
