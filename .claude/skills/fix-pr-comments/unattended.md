# Unattended mode and scope guard

## Unattended mode (`--unattended`)

No user can answer, for example when `/sweep-pr-comments` runs this skill from cron. Ask no question, and skip Step 4.

| Category | Action |
|----------|--------|
| Typo / formatting | Fix and reply |
| Real code issue | Fix if you verified it in Step 3, then reply |
| Style / naming | Fix if the comment names the exact change, then reply |
| Design / architecture | Do not edit. Reply: `Claude AI: Acknowledged — this needs a human decision.` |
| Ambiguous | Do not edit. Reply: `Claude AI: Acknowledged — the request is unclear. Please clarify.` |
| Invalid / not applicable | Reply with the reason |

- After each fix, run lint and the tests of the affected module. If they fail, revert that edit and reply `Claude AI: No change — the fix failed lint or tests.`
- Review the fixes with `/review-code` as in Step 5b, before the replies. Undo a fix that has a Critical or Major issue, and reply `Claude AI: No change — the fix did not pass review.`
- Commit and push as in Step 7, with `push.sh`. If it reports a conflict, resolve it as in Step 7. If it cannot be resolved safely, abort the merge, push nothing, and report the files for a person to decide. NEVER force-push.
- Do not offer a retry in the report.
- With `--escalate` or `--only`, also read `tiers.md`. In tier 1, escalate instead of the "Design / architecture" and "Ambiguous" replies. In tier 2, `tiers.md` replaces those two rows.

## Scope guard (every automated run)

A run is automated when no user is present: headless (`claude -p`), background (`--bg`), cron, or a call from another skill or agent. An automated run changes only the worktree of this PR, because no reviewer sees a wrong write outside it.

- Get the worktree path with `git rev-parse --show-toplevel`. Before each write, check that the full file path starts with it.
- Run `git` only in that worktree. Push only the branch of this PR.
- Do not touch `~/.claude`, settings, skills, other repositories, other worktrees, or the main checkout.
- If a step needs a path outside the worktree, skip the step, report it, and stop. Ask no question.
