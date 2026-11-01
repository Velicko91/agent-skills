# <service> - incident knowledge

What past incidents taught about this service. `/investigate-incident` reads this file first and updates it after each solved incident.

## Symptoms

| Symptom | Points to |
|---------|-----------|
| Alert "ledger balance mismatch" fires for a few accounts | C1 |
| `deadlock detected` in the worker logs | C2 |

## Causes

### C1 - Duplicate settlement event

- **Mechanism:** The settlement consumer retries after a timeout, but the first attempt already committed. The balance gets the amount twice.
- **Confirm:** Q1 returns two rows with the same `event_id`.
- **Fix:** Reverse the second entry with the admin correction endpoint. Then add the account to the reconciliation run.
- **Prevent:** Idempotency key on `event_id` (ticket PROJ-1234).
- **Incidents:** INC-101, INC-142

### C2 - Lock contention during the nightly batch

- **Mechanism:** ...
- **Confirm:** ...
- **Fix:** ...
- **Incidents:** INC-120

## Diagnostic queries

**Q1 - duplicate settlement entries (C1)**

```sql
SELECT event_id, count(*), min(created_at), max(created_at)
FROM public.ledger_entries
WHERE account_id = '<account_id>'
GROUP BY event_id
HAVING count(*) > 1;
```

**L1 - consumer retries (C1)** - log filter: `jsonPayload.msg="retrying settlement" AND jsonPayload.event_id="<event_id>"`

## Incident log

| Incident | Date | Cause | Fix | Link |
|----------|------|-------|-----|------|
| INC-101 | 2026-01-14 | C1 | Reversed 3 entries | <incident url> |
