---
name: verify-stamp
description: Records the content hash of the working tree after a full test run or a review, so a later step skips the run when the code is unchanged. Used by other skills.
user-invocable: false
disable-model-invocation: true
---

# Verify Stamp

Other skills run `stamp.sh` in this directory. It is not a slash command.

## Rules for a calling skill

**Before a full test run:**

```bash
~/.claude/skills/verify-stamp/stamp.sh check tests
```

- `FRESH tests passed <date>` → do not run the suite. Report `tests: reused — passed on this exact content at <date>`.
- `STALE …` or `NONE …` → run the suite.

**After each full test run**, also after a failure:

```bash
~/.claude/skills/verify-stamp/stamp.sh record tests passed    # or: failed
```

**Review:** use `check review` before a review of the whole change, and `record review clean` (no Critical or Major finding) or `record review blocking` after it. Record after the review fixes are applied, because the fixes change the content.

- Record only a run of the **full** suite. A run of one module or one test proves nothing about the rest, so record nothing for it.
- Run `check` and `record` in the repository or the worktree that holds the code. Each worktree has its own stamp.
- A content change of any kind gives a new hash: committed, staged, unstaged, or a new untracked file. Ignored files, `.dev-loop-state.json`, and `.claude/worktrees` do not count.
- The stamp is the file `claude-verified` in the git directory, so git never commits it.
