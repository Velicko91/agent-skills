---
name: investigate-incident
description: Investigates a production incident for one service — starts from its knowledge file of past causes, gathers evidence, ranks causes, recommends a fix, and records the cause once solved. Use for "investigate INC-123", "what is causing this alert", or "has this happened before".
user-invocable: true
allowed-tools: Skill, Read, Write, Edit, Grep, Glob, Bash(dnote *), Bash(diff *), Bash(cp *), Bash(mkdir *), Bash(date *), Bash(git *), Bash(gh pr *), Bash(rm -r /tmp/investigate-incident/inc-*), mcp__incident_io__incident_show, mcp__incident_io__incident_list, mcp__incident_io__incident_update_list, mcp__incident_io__follow_up_list, mcp__incident_io__postmortem_list, mcp__incident_io__postmortem_show, mcp__incident_io__alert_show, mcp__incident_io__alert_list, mcp__incident_io__investigation_read, mcp__incident_io__skill_list, mcp__incident_io__skill_show, mcp__plugin_slack_slack__slack_read_thread, mcp__plugin_slack_slack__slack_read_channel, mcp__plugin_slack_slack__slack_search_public_and_private, CronCreate, CronList, CronDelete
model: sonnet
---

# Investigate Incident

Find the cause of an incident in one service, and the fix. Start from what past incidents taught. When the incident is solved, record the cause and the fix, so the next investigation is faster.

## Hard rules

- Run reads without asking: `/query-db`, `/get-gcloud-logs`, Slack search and read, incident.io reads, dnote, `gh`, and `git`. They change nothing.
- If you find a probable cause, validate it at once with `/query-db` and `/get-gcloud-logs`. NEVER wait for permission, because these reads change nothing.
- NEVER run a fix, post to Slack, change incident.io, or write to a database or a cluster without a yes in this conversation, because these actions affect production and other people.
- Use `/query-db` for database reads. NEVER write to a database.
- A match with a past incident is a hypothesis. Confirm each cause with evidence: a query result, a log line, or a `file:line` reference.
- NEVER update the knowledge file or the incident log before the user says that the incident is solved, or before the resolve check finds it resolved in incident.io, because an unconfirmed cause misleads the next investigation.
- Write temporary files only to the working folder of this incident. NEVER delete the folder of another incident, because another session can still use it.
- NEVER guess a channel, a database alias, or a repo path, because a wrong source gives wrong evidence. NEVER write a service value in `skill.md`, because `skill.md` is public.
- If the evidence points to a false positive, and a read at a later time can confirm it, schedule the recheck without asking. The recheck only reads, so it changes nothing.
- If you recommend a feature flag as a fix, show the name of the user who added the flag. The user can then ask that person if the flag is safe.
- Write a phase marker when each phase starts, as `~/.claude/skills/phase-markers/skill.md` says. The ID is the `⟨ph:…⟩` on the phase heading.

## Local configuration

Read `~/.claude/skills/investigate-incident/data.json` (shape in `data.example.json`). It maps each service to its sources:

| Field | Meaning |
|-------|---------|
| `aliases` | Other names for the service in alerts, Slack, and incident.io |
| `repo` | The local checkout, for the code search |
| `databases` | `/query-db` aliases, for example dev and prod |
| `logs` | The `/get-gcloud-logs` service alias |
| `slackChannels` | Alert and team channels to search |
| `incidentIo` | `services` (catalog names in incident.io) and `teams` |
| `dnoteBooks` | dnote books with runbooks for the service |
| `exec` | Shell aliases that open a shell in the service pod, one for each env, for example `{"dev": "exec-acme-dev"}` |

- If `data.json` is missing, copy `data.example.json` to `data.json` and ask for the service entry. STOP and WAIT.
- If the service has no entry, ask for its sources, add the entry, and continue.
- If a command runs inside a pod and the service has no `exec` alias for that env, ask for the alias and add it.
- The optional top-level field `resolveCheckHours` sets the hours between resolve checks. The default is `2`. Use a whole number from 1 to 23.

## Files

| File | Holds |
|---|---|
| `services/<service>.local.md` | The knowledge file of one service: Symptoms (and the causes they point to), Causes (mechanism, how to confirm, fix, incidents), Diagnostic queries (each with the cause it checks), Incident log. Shape: `services/TEMPLATE.example.md`. |
| `incident-log.local.md` | One entry for each resolved incident, for all services. The weekly report reads it. |
| `/tmp/investigate-incident/inc-<number>/` | The working folder: log exports, query results, the proposed knowledge file. Without an incident ID, use `inc-<YYYYMMDD-HHMM>` of the start time. |

The `*.local.md` files are gitignored, because they hold internal details.

## Arguments

```
/investigate-incident [<incident-id | Slack link | alert ID>] [--service <name>] [context...]
```

| Argument | Default |
|---|---|
| `<incident-id>` | An incident.io ID such as `INC-1234`, a Slack message link, or an alert ID |
| `--service <name>` | From the incident's affected service, the alert source, or the `aliases` |
| `[context...]` | Pasted errors, logs, or a description. Required if no ID is given. |

The investigation reads the dev database first, and prod only if the evidence is in prod. It searches past incidents of the last 12 months, unless the user asks for more.

## Workflow

### Phase 1 — Identify the incident and the service ⟨ph:982a01ba⟩

1. Parse the input: an incident ID, a Slack link, an alert ID, and any pasted context.
2. Find the service from `--service`, the incident's affected service, the alert source, or the `aliases`. If two services match, or none, ask. STOP and WAIT.
3. Set the scope to the symptom of the incident title and its first alert. If incident.io grouped another alert in by key (`alert_show` gives `joined_by: key`) and its symptom is different, list it as "Other attached alerts" and do not investigate it. A grouping key, such as priority and source, does not show a shared cause. Investigate it only if the user asks.
4. Create the working folder: `mkdir -p /tmp/investigate-incident/inc-<number>`.

### Phase 2 — Read what is already known ⟨ph:9cfcbcb4⟩

Read `services/<service>.local.md` before any other source, because a known cause is the fastest lead. If it does not exist, note that this is the first incident of the service. Compare the symptoms with the Symptoms section, and write down each matching cause as a hypothesis.

### Phase 3 — Gather evidence (in parallel) ⟨ph:6adcecf2⟩

Before the first incident.io call, load the `incident-io:incidents` skill. If it is not available, call `mcp__incident_io__skill_list` and read the matching skill with `skill_show`.

| Source | What to get |
|--------|-------------|
| incident.io | The incident, its timeline (`incident_update_list`), its alerts, its follow-ups, and the AI investigation, if one exists |
| Slack | The thread from the link, and messages about the symptom in `slackChannels` during the incident window |
| Past incidents | `incident_list` and `postmortem_list` for the same service and similar symptoms. Read the postmortem of each match. |
| Slack history | `slack_search_public_and_private` for the error text and the symptom, before this incident. Read each matching thread to see how it was resolved. |
| dnote | `dnote find "<keyword>" -b <book>` in each of the service's `dnoteBooks`, with 3–5 keywords from the title and the error. If the service has no `dnoteBooks`, run `dnote find "<keyword>"` across all books. Read each matching note in full. |
| Logs | `/get-gcloud-logs` for the `logs` alias, in the incident window, filtered on the error. Pass `--file-path /tmp/investigate-incident/inc-<number>/<logs>-<env>-<timestamp>.json`. |
| Code | Grep the `repo` for the error text, the endpoint, the table, or the job name |
| Pull requests | In the `repo`, `gh pr list --state merged` and `--state open`, with `--search` on the changed files, the error text, or the incident ID |

For each matching past incident, record the ID, the date, the cause, and what fixed it.

### Phase 4 — Investigate ⟨ph:a9db19ef⟩

Run Phases 3 and 4 to the end, then show the report.

1. List two to five hypotheses, ranked by evidence. Put a matching cause from the knowledge file first.
2. For each one, find the evidence that confirms it or rules it out. Use the "Diagnostic queries" of the knowledge file first, with `/query-db`. Fetch logs around the failure with `/get-gcloud-logs`, and read the code there. Search Slack for the same symptom. If a hypothesis needs more data, run more reads.
3. If a hypothesis becomes the probable cause, validate it before the report:
   - Run `/query-db` to find the affected rows, and how many.
   - Run `/get-gcloud-logs` to find the failing requests or errors in the incident window.
   - If the result does not confirm the cause, lower its rank and validate the next hypothesis.
4. Stop a hypothesis when the evidence rules it out, and write one line on why.
5. Convert relative times to absolute times, from the incident start time in incident.io.
6. If the cause is a defect, find the merged PR that added it: `git log -S "<code>"` or `git blame` on the failing lines, then `gh pr list --search <sha> --state merged`.
7. Find an open PR that fixes the cause: search open PRs on the failing files and the incident ID.
8. For each PR from step 6 or 7, record the link and the author with `gh pr view <n> --json url,author,mergedAt`.
9. If a feature flag can fix the cause, find the commit that added it: `git log -S "<FLAG_NAME>" --reverse --format='%h %an %ad' | head -1`. Find its PR with `gh pr list --search <sha> --state merged`. Record the PR link and the author.
10. Assess the level from the evidence, with the severity names of incident.io: the users or accounts affected, the money at risk, and whether the impact continues.
11. Focus the fix on the current incident: stop the impact and repair the data. Write the long-term fix as one line.
12. If the most likely cause is a false positive that time can confirm, schedule one recheck. Examples: a job that has not run yet, a consumer that lags, a retry that is still pending.
    - Set the time to when the confirming read can show the result, from the evidence, for example the next job run plus 10 minutes.
    - Call `CronCreate` with `recurring: false` and this prompt: `Recheck <INC-ID> (<service>): run <the reads>. False positive if <expected result>.`
    - Record the job ID and the time from the `CronCreate` result. Put them in the report.
13. If the incident has an incident.io ID and its status is not closed, schedule the resolve check (see "Resolve check"). Put the job ID in the report.

### CHECKPOINT ⟨ph:ed3f0b04⟩

```
## <INC-ID> - <title> (<service>)

**Status:** <status> · **Severity:** <severity in incident.io> · **Started:** <absolute time>

**Assessed level:** <severity> - <impact: users or accounts affected, money at risk, still ongoing or not>

### Most likely cause
<one or two sentences> - confidence: high | medium | low
Evidence:
- <query result, log line, or code reference>

### Ruled out
- <hypothesis> - <why>

### Seen before
| Incident | Date | Cause | Fix |
|----------|------|-------|-----|

### Related PRs
| PR | Role | Owner | State |
|----|------|-------|-------|
| <link> | Caused the defect / Fixes the defect / Added the flag | <author name> | merged <absolute time> / open |

### Recommended fix (current incident)
1. <step, command, or code that stops the impact or repairs the data>
   In a pod: run `<exec alias of the env>` first, then `<command>`
   For a flag: `<FLAG_NAME>` - added by <author name> in <PR link>

**Long-term:** <one line, or "none">

**Resolve check:** every <N>h while idle (job <id>)

### Scheduled recheck
<absolute time> - <what it reads> - false positive if <expected result> (job <id>)

### Open questions
- <what is still unknown, and how to find it>
```

Remove "Related PRs" if no PR caused the defect, fixes it, or added a recommended flag. Remove "Scheduled recheck" if you scheduled none. Remove "Resolve check" if you scheduled none. STOP and WAIT for the user's decision.

### Phase 5 — Continue until the incident is solved ⟨ph:1fccee31⟩

- If the user gives new context, go back to Phase 3 or 4 with it.
- If the user approves a fix, give the exact steps or code. Put the `exec` alias of the env before each command that runs inside a pod. The user or the service's tools run the change, because `/query-db` only reads. If the fix corrects data and a dnote runbook of the service holds a `fix()` function, write the correction in the same pattern, with the incident ID and a comment that says what it does and when it is safe to run.
- Write each fix script with no empty lines, also between imports and between blocks, because an empty line ends a function in an interactive shell such as `flask shell`.
- Continue until the user says that the incident is solved, for example "solved", "fixed", "resolved", or "update the doc", or until the resolve check finds the incident resolved.

### Recheck

When a scheduled recheck fires, run only its reads, then report one line: `confirmed false positive`, `real issue`, or `not clear yet`.

- For `real issue`, go back to Phase 4 with the new evidence.
- For `not clear yet`, schedule one more recheck. After three rechecks, STOP and ask the user.
- Rechecks live only in this session. If the user ends the session, tell them that the pending recheck stops too.
- If the incident is solved, cancel each pending recheck with `CronDelete`.

### Resolve check

While the session is idle, check if the incident is resolved in incident.io.

- Call `CronCreate` with `recurring: true`, the cron `7 */<resolveCheckHours> * * *`, and this prompt: `Resolve check <INC-ID> (<service>): read the incident with incident_show. Report one line: resolved, still open, or stopped.`
- Read `resolveCheckHours` from `data.json`. If it is missing, use `2`.
- When the check fires, call `incident_show` and report one line:
  - `resolved`: the status is closed or resolved. Mark the incident as solved in this session. Cancel the resolve check and each pending recheck with `CronDelete`. Tell the user the incident is resolved, then go to Phase 6.
  - `still open`: do nothing else.
  - `stopped`: the status is declined, canceled, or merged. Cancel the resolve check, and tell the user.
- If the user changes the interval, delete the job with `CronDelete` and create it again with the new value.
- The resolve check lives only in this session, like a recheck.

### Phase 6 — Record the solved incident ⟨ph:032acfdd⟩

Read `record.md` in this skill directory, and follow it. It updates the knowledge file and the incident log, after a yes.

## Examples

- `/investigate-incident INC-1234` — reads the incident, finds the service, starts from its knowledge file
- `/investigate-incident --service acme-ledger https://acme.slack.com/archives/C0123/p1700000000` — an alert in a Slack thread
- `/investigate-incident --service acme-ledger balances are negative for some accounts since 09:00` — from a description
- `solved - update the doc` — records the cause and the fix

## Retry

If the user says "retry", reuse no hypothesis or evidence. Read the knowledge file again, fetch every source again, and treat the incident as new.
