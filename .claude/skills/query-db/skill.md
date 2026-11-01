---
name: query-db
description: Answers a data question with one read-only SQL query to a service's Postgres database from the config — handles the Keychain password and port forward, finds the schema, returns a table. Refuses writes. Use for "check in the db" or "/query-db"; for warehouse analytics use /query-snowflake.
user-invocable: true
allowed-tools: Bash(~/.claude/skills/query-db/query.py *), Read
model: sonnet
---

# Query DB

Answer a data question with one read-only SQL query. The databases come from `data.json` in this skill directory, and the passwords from the macOS Keychain.

## Hard rules

- NEVER run a statement that writes, also if the database user can write. Refuse, and give the reason: this skill only reads.
- ALWAYS run SQL through `query.py`, never with `psql` or another client, because the script holds the read-only guard. NEVER change the script or the session settings to get past the guard.
- NEVER print, log, or ask for a password in the conversation. It stays in the Keychain.
- NEVER guess a database, host, context, table, or column, because a wrong value queries the wrong data, and a similar column gives a wrong answer.
- If two databases match the question, ask once. Do not query both.

## Read-only mode

The database user can have write permission, so the skill blocks writes itself:
1. Write one `SELECT`, `WITH`, `EXPLAIN`, `SHOW`, `TABLE`, or `VALUES` statement.
2. The script refuses any other statement before it connects, and any statement with a write keyword (`INSERT`, `UPDATE`, `DELETE`, `INTO`, `COPY`, …) or a function with side effects (`pg_terminate_backend`, `nextval`, `dblink`, …).
3. The script starts each session with `default_transaction_read_only=on`, so the server also refuses a write.

## Local configuration

Read `~/.claude/skills/query-db/data.json`. If it is missing, copy `data.example.json` to `data.json`, and ask the user to fill it in, with `config.md` in this skill directory as the reference. STOP and WAIT.

## Arguments

```
/query-db [--db <alias>] [--limit N] [--show-sql] <question>
```

| Argument | Default | Meaning |
|---|---|---|
| `<question>` | required | Everything after the flags |
| `--db <alias>` | from the question | The alias, or an unambiguous prefix of it |
| `--limit N` | `defaults.limit`, or `100` | The row limit |
| `--show-sql` | hidden | Show the SQL with the answer. Also show it if the user asks. |

The skill runs the query at once, with no approval, because it only reads.

## Workflow

### Step 1 — Select the database

Run `~/.claude/skills/query-db/query.py list`. Use `--db` if given. Otherwise, pick the entry whose `keywords`, `tables`, or alias match the question. If two match, or none, show the list, and ask. STOP and WAIT.

Name the selection in one line, for example: "Querying `acme-ledger-dev` (keyword "transactions")."

### Step 2 — Connect

Run `~/.claude/skills/query-db/query.py check <alias>`. It reuses an open local port (and prints its process) or starts the port forward, reads the Keychain password unless the entry is `passwordless`, connects, and checks that the session is read-only.

| Error | Action |
|-------|--------|
| `no Keychain password` | Give the user the command in "Store a password" in `config.md`. STOP and WAIT. |
| `kubectl context ... not found` | Tell the user to log in to the cluster. STOP and WAIT. |
| A `cloud-sql-proxy` auth error in the log | Tell the user to run `! gcloud auth application-default login`. STOP and WAIT. |
| `port forward did not start` | Read `/tmp/query-db/<alias>.log`, and report the cause. |
| A `psql` connection error | Report it, and check `host`, `port`, `user`, and `sslmode` in `data.json`. |

### Step 3 — Discover the schema

Start from `tables` and `notes` in `data.json`. If they do not name every column that the query needs, look them up:

```bash
~/.claude/skills/query-db/query.py run <alias> <<'SQL'
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND table_name ILIKE '%<keyword>%'
ORDER BY 1, 2
LIMIT 50
SQL
```

```bash
~/.claude/skills/query-db/query.py run <alias> <<'SQL'
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = '<schema>' AND table_name = '<table>'
ORDER BY ordinal_position
SQL
```

### Step 4 — Write and run the query

1. Write one read-only statement.
2. Qualify each table: `<schema>.<table>`.
3. Select only the columns you need. Do not use `SELECT *` on a large table, because it is slow and hides the answer.
4. Add `LIMIT <N>` if the query returns rows. An aggregate needs none.
5. Change relative dates to absolute dates, for example "last week" → `>= '2026-10-19'`.
6. Run it:
   ```bash
   ~/.claude/skills/query-db/query.py run <alias> --limit <N> <<'SQL'
   <query>
   SQL
   ```

The script prints CSV. If it prints `NOTE: <M> rows, showing <N>`, say that the result has more rows.

If the query fails:
1. If the guard refused it, write it again as one read-only statement.
2. If the server returned an error (an unknown column, a wrong type), run Step 3 again on that table, fix the query, and run it once more.
3. If it fails again, report the error, and stop.

### Step 5 — Answer

1. Give the answer first, in one to three sentences, with the key numbers.
2. Show the result as a markdown table. If it has more than 20 rows, show 20, and write "(showing 20 of N)".
3. Show the SQL in a `sql` block only with `--show-sql`, or if the user asks.

### Step 6 — Stop the port forward

When the question has an answer and no next query is expected, run `~/.claude/skills/query-db/query.py stop <alias>`. It stops only a forward that `query.py` started.

## Examples

- `/query-db how many transactions did account 42 have last month`
- `/query-db --db acme-cards-local is card card_123 frozen`
- `/query-db --show-sql --limit 20 the 20 newest accounts with status frozen`
- `/query-db delete the test accounts` ← refused, because the skill only reads

## Retry

If the user says "retry", reuse no SQL and no schema discovery. Read `data.json` again, and treat the question as new.
