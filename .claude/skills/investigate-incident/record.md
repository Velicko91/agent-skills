# Record a solved incident (Phase 6)

Start only after the user says that the incident is solved, or after the resolve check finds the incident resolved. In the second case, if the confidence of the report was below high, say so before the diff, because nobody confirmed the cause.

## Steps

1. Copy the knowledge file to `/tmp/investigate-incident/inc-<number>/<service>.proposed.md`. If there is no knowledge file yet, start from `services/TEMPLATE.example.md`.
2. Merge what this incident taught, with the merge rules below.
3. Show the diff:

   ```bash
   diff -u ~/.claude/skills/investigate-incident/services/<service>.local.md /tmp/investigate-incident/inc-<number>/<service>.proposed.md
   ```

4. Write the entry for the resolved-incident log (format below). Get the date with `date +%Y-%m-%d`. Take the impact from the assessed level and the evidence.
5. Show the log entry under the diff, and ask:

   > Save this to the `<service>` knowledge file and the incident log? (yes / edit)

   STOP and WAIT.
6. After a yes, write the file to `services/<service>.local.md`.
7. Add the entry to the end of `incident-log.local.md`. Create the file if it does not exist. If an entry for the same incident ID exists, replace it, because one incident has one entry.
8. Delete the working folder: `rm -r /tmp/investigate-incident/inc-<number>`. Do this also if the user declines the save, because the incident is solved.

If an incident affects two services, update the file of the service where the cause is, and add a one-line pointer in the other.

## Resolved-incident log

`~/.claude/skills/investigate-incident/incident-log.local.md` holds the incidents that the user resolved, for all services. The weekly report reads only this log, so every solved incident needs an entry.

```markdown
## <YYYY-MM-DD> · <INC-ID> · <service> · impact: <high | medium | low>
**Title:** <incident title>
**Issue:** <one or two sentences: what broke, and who or what it affected>
**Resolution:** <one or two sentences: what fixed it>
**Links:** <incident.io link> · <PR links, if any>
```

| Impact | When |
|--------|------|
| `high` | Customers or money affected, or the impact continued for hours |
| `medium` | A small number of customers affected, or an internal process blocked |
| `low` | No customer impact, for example an alert, a test failure, or a data check |

## Merge rules

The knowledge file must stay short, correct, and free of duplicates:

1. **Same cause:** if an entry describes the same mechanism, update it and add the incident ID. Do not add a second entry.
2. **Better facts win:** if this incident shows a better confirmation step or fix, replace the old text. Do not keep both.
3. **New cause:** add an entry only for a new mechanism, with the next ID (`C1`, `C2`, …).
4. **Symptoms:** add a symptom only if no line describes it. Point it to the cause IDs.
5. **Queries:** add a query only if no query checks the same thing. Write the cause ID it checks, with placeholders such as `<account_id>`.
6. **Incident log:** add one line for this incident.
7. **Facts only:** write what the evidence showed. Do not write the timeline, the ruled-out hypotheses, or who did what; the incident.io record keeps those.
8. **No secrets:** NEVER write a token, a password, or customer personal data. Use IDs only as placeholders in queries.
9. **Size:** keep the file under 300 lines. If it gets longer, merge similar causes, and remove fixes that the code no longer needs.
