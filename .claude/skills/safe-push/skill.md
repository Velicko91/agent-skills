---
name: safe-push
description: Pushes the current branch only after it pulls new remote commits and finds no conflict with the base branch. Used by pr-author and /fix-pr-comments.
user-invocable: false
disable-model-invocation: true
---

# Safe Push

Other skills run `push.sh` in this directory instead of `git push`. It is not a slash command.

```bash
~/.claude/skills/safe-push/push.sh [<base>]
```

Run it inside the repository or the worktree. `<base>` is the base branch of the PR; the default is the default branch of `origin`.

It does this, in order:
1. Stops with `DIRTY` if tracked files have uncommitted changes.
2. Merges the commits that others pushed to the same branch. It never rebases, so it never rewrites pushed commits.
3. Checks with `git merge-tree` whether the branch conflicts with `<base>`, without changing the working tree.
4. Pushes, with `-u`, only if steps 2 and 3 found no conflict. It never force-pushes.

| First line of output | Exit | What the caller does |
|---|---|---|
| `PUSHED <branch>` | 0 | Continue |
| `CONFLICT_REMOTE <files>` | 3 | Others pushed commits to this branch that conflict. The merge was aborted. Resolve it (below), with no question. |
| `CONFLICT_BASE <files>` | 4 | The branch conflicts with `<base>`. Nothing was pushed. Resolve it (below), with no question. |
| `DIRTY` | 5 | Commit or stash the changes first. |
| `ERROR <reason>` | 2 | Report the reason. |

A line `PULLED new commits of origin/<branch>` before `PUSHED` means that the branch now holds commits from others. Say so in the report.

## Resolve a conflict

Resolve a conflict automatically, with no question, whenever you can (steps 1–7). Ask for a decision only in the cases of "When you cannot resolve it". Only the session model resolves: a subagent on a cheaper model returns the conflict to its caller.

1. Merge the side that conflicts: `git merge --no-edit origin/<branch>` for `CONFLICT_REMOTE`, or `git merge --no-edit origin/<base>` for `CONFLICT_BASE`. NEVER rebase, and NEVER use `-X ours` or `-X theirs`, because they drop one side without reading it.
2. List the files: `git diff --name-only --diff-filter=U`. For each file, read the common base (`git show :1:<file>`), this branch (`:2:`), and the other side (`:3:`). Find what each side meant to change.
3. Write the result with Edit, so that it keeps the intent of both sides, and remove every conflict marker:
   - Both sides add different things: keep both.
   - Both sides change the same line in compatible ways: combine them.
   - Both sides change the same rule in incompatible ways: you cannot resolve it. See below.
   - A lockfile: take the other side's version, and generate the lock again with the project's resolver (for example `poetry lock`, `uv lock`, or `npm install --package-lock-only`). NEVER merge lockfile hunks by hand.
4. Check that no marker is left: `git diff --check`, and search the files for `<<<<<<<`, `=======`, and `>>>>>>>`.
5. Stage the resolved files by name, and finish the merge: `git commit --no-edit`.
6. Run the full test suite with the test stamp rules of `~/.claude/skills/verify-stamp/skill.md`. If a test fails because of the merge, fix it.
7. Run `push.sh` again. If it reports a conflict again, repeat once.

Report each resolved file in one line: the file, and how both sides were kept.

### When you cannot resolve it

You cannot resolve a conflict safely if:
- both sides change the same rule, value, or behaviour in incompatible ways, so one intent must lose;
- the tests fail after the merge, and the cause is not an obvious result of the merge;
- the resolver cannot generate the lockfile again;
- `push.sh` still reports a conflict after 2 rounds.

Then:
- **Interactive run:** stop. For each such file, show both versions in short, what each side meant, and the options (keep ours, keep theirs, or a combination that you propose). Ask which to use. WAIT. Resolve the other files automatically, as above.
- **Unattended run** (no user present, for example a cron sweep): run `git merge --abort`, push nothing, and report the files with the reason, so a person can decide.
