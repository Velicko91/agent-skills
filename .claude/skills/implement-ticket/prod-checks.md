# Prod checks — template and rules

Phase 10 of `/implement-ticket` reads this file.

Prod checks cover the release and the deployment only. The dev tests of Phase 9 already prove the behaviour, so NEVER repeat a functional test on prod: no happy path, no regression call. A call on prod can change customer data.

## Sources

Read each source before you write a check:

- The merged diff: `gh pr diff <pr>`. Find each feature flag, config value, secret, and migration that it adds or reads.
- The service file of `/test-on-dev`: `~/.claude/skills/test-on-dev/services/<service>.local.md`. It holds "Prod release" and "Prod logs".
- The dev test results of Phase 9. Name each `blocked` test, because it is not proven on dev.

## Rules

- Write 3 to 5 checks. Each check has one action and one concrete expected result.
- Give the release check: how to see that prod runs a release with the merge commit.
- Find each feature flag that the diff adds or reads. Give its name, the value it must have on prod, and the scope (all, a percentage, a list of accounts). Say whether the user must turn it on, because the watch never changes a flag. If the diff has no flag, write "No feature flag".
- Add a check for each config value, secret, or migration that the diff adds. Leave the row out if there is none.
- Name the log queries to watch: the error lines of the changed code paths, and the general error rate of the service.
- Give one rollback step: turn off the flag, or revert the PR.
- If you cannot find a value (a release check, a flag scope, a log alias), write `<ask: …>` in its place. NEVER guess it.

## Release watch

Phase 10 starts the watch with CronCreate after it shows the checklist.

1. Get the release check from "Prod release" of the service file. It is one read-only command that prints `released` when prod runs a release that contains the merge commit, and `not yet` otherwise. Examples: compare the prod image tag in ArgoCD with the release tag that holds the commit (`git tag --contains <sha>`), or read the prod deployment image with `kubectl get deploy`.
2. Get the prod log alias from "Prod logs" of the service file, for `/get-gcloud-logs`.
3. If either is missing, ask the user for it. After the run, offer to add it to the service file.
4. Schedule a recurring job every 30 minutes, on a minute that is not 0 or 30. Write its prompt so it stands alone, because it runs without this conversation:
   - Run the release check. If it prints `not yet`, reply with one line and do nothing else.
   - If it prints `released`, delete this job with CronDelete. Record the release time.
   - Read the prod logs of the service with `/get-gcloud-logs <alias>` from the release time to now, with the error lines of the checklist. Compare the count of errors with the same length of time before the release.
   - Schedule one more read 30 minutes later with a one-shot CronCreate, with the same queries.
   - After the second read, report with PushNotification: released at `<time>`, the error counts before and after, each new error line, and each flag the user must set.
5. NEVER change a flag, restart a service, or call a prod endpoint from the watch.

## Template

```
## Prod checks — <TICKET> <title>
PR: <url> · merged <enteredAt of merged> · dev-tested <enteredAt of dev-tested>

- [ ] 1. Release — prod runs a release that contains <short merge sha>: <release check>
- [ ] 2. Feature flag — `<flag>` is `<value>` for <scope>; <turn it on after the release | already on> (or "No feature flag")
- [ ] 3. Config — `<name>` is set / migration `<id>` is applied
- [ ] 4. Logs — 30 min after the release, <log queries>: no new errors, error rate as before the release

Release watch: job <id>, every 30 min, next run <time>
Rollback: <turn off `<flag>` | revert <PR>>
```
