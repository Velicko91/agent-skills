# Prod checks — template and rules

Phase 10 of `/implement-ticket` reads this file.

## Sources

Read each source before you write a check:

- The acceptance criteria of the ticket.
- The merged diff: `gh pr diff <pr>`.
- The dev test results of Phase 9. Reuse their happy path, with prod values.

## Rules

- Write 3 to 6 checks. Each check has one action and one concrete expected result.
- Find each feature flag that the diff adds or reads. Give its name, the expected value on prod, and the scope (all, a percentage, a list of accounts). If the diff has no flag, write "No feature flag".
- Add a check for each config value, secret, or migration that the diff adds. Leave the row out if there is none.
- Give exactly one happy path. Prefer a read-only check, or an internal or test account, because the checks run on real data.
- Mark each step that writes data on prod with ⚠️ writes.
- Add one regression check for the behaviour next to the change that must not change.
- Name the log query or the dashboard to watch, and for how long.
- Give one rollback step: turn off the flag, or revert the PR.
- If you cannot find a value (a flag scope, an account, a dashboard), write `<ask: …>` in its place. NEVER guess it.

## Template

```
## Prod checks — <TICKET> <title>
PR: <url> · merged <enteredAt of merged> · dev-tested <enteredAt of dev-tested>

- [ ] 1. Deploy — the prod release contains <short merge sha>: <how to see it, for example the image tag in ArgoCD>
- [ ] 2. Feature flag — `<flag>` is `<value>` for <scope>
- [ ] 3. Config — `<name>` is set / migration `<id>` is applied
- [ ] 4. Happy path — <action> → expect <result>
- [ ] 5. Regression — <existing action> → expect <same result as before>
- [ ] 6. Watch for <30 min> — <log query or dashboard>: no new errors

Rollback: <turn off `<flag>` | revert <PR>>
```
