---
name: query-snowflake
description: Answers an analytics question from the Snowflake warehouse — finds the schema, runs one read-only SQL query, and returns a table with the answer. Use for Snowflake or warehouse data, or "/query-snowflake"; for a service's own Postgres database use /query-db.
user-invocable: true
allowed-tools: mcp__snowflake__run_snowflake_query
model: sonnet
---

# Query Snowflake

Answer a data question from Snowflake. The databases come from `snowflake.databases` in `~/.claude/config.local.json`. Discover the schema, write the SQL, run it, and return a markdown table with a short answer.

## Hard rules

- **Read only.** The Snowflake tool accepts any statement, including writes. The connected role must be read-only, so Snowflake refuses a write; this check is the second layer. Before each call, check the statement:
  - It is exactly one statement: no `;` except at the end.
  - It starts with `SELECT`, `WITH`, `SHOW`, `DESCRIBE`, `DESC`, or `EXPLAIN`.
  - It holds none of `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `DROP`, `CREATE`, `ALTER`, `GRANT`, `REVOKE`, `COPY`, `PUT`, `REMOVE`, `CALL`, `EXECUTE`, `USE`, `SET`, `UNDROP`, outside string literals.
  - If a check fails, do not run it. If the question needs a write, refuse, and say that this skill only reads.
- NEVER guess a database or a column. A wrong database or a similar column returns wrong numbers that look right.
- Qualify each table as `<DB>.<schema>.<table>`.
- Add a `LIMIT`, unless `--no-limit` is given. Never `SELECT *` on a large fact table.
- Always print the SQL before the result, also with `--raw`.
- Convert relative dates to absolute dates, for example "last week" → `>= '2026-05-13'`.
- If two databases fit the question, ask once. Do not query both.

## Arguments

| Argument | Default | Meaning |
|---|---|---|
| `<question>` | required | Everything after the flags |
| `--db <name>` | from the question | A key of `snowflake.databases`, or an unambiguous prefix |
| `--limit <n>` | `100` | The row limit |
| `--no-limit` | — | No `LIMIT`. Only if the user asks for the full result. |
| `--raw` | — | The SQL and the table only, no prose answer |
| `--explain` | — | Also print the discovery and the reasoning |

## Workflow

### Step 1 — Select the database

Read `~/.claude/config.local.json`. `snowflake.databases` maps each database to its topic keywords. If the config is missing, copy `config.example.json`, and ask the user to fill it in.

Use `--db` if given. Otherwise, pick the database whose keywords match the question best. If none matches, list the databases, and ask. If the question covers two domains, query the most specific one first, and ask before you query the second. Name the choice in one line:

> Querying `<db>` (keyword "users" in the question).

### Step 2 — Discover the schema

Always run the discovery before the main query:

```sql
-- Find candidate tables
SELECT table_schema, table_name
FROM <DB>.INFORMATION_SCHEMA.TABLES
WHERE table_name ILIKE '%<keyword>%'
ORDER BY table_schema, table_name
LIMIT 50;

-- Inspect the columns of a likely table
SELECT column_name, data_type
FROM <DB>.INFORMATION_SCHEMA.COLUMNS
WHERE table_schema = '<schema>' AND table_name = '<table>'
ORDER BY ordinal_position;
```

With `--explain`, print the results. Otherwise, name only the chosen tables.

### Step 3 — Write and run the query

Write the query against the discovered tables and columns, with explicit columns and a comment that says what it computes. Print it in a `sql` block, check it against the read-only rules, and run it with `mcp__snowflake__run_snowflake_query`. Do not stop for approval, because it only reads.

If it fails (unknown column or table, wrong type, permission denied): show the error, discover the failing object again, fix the query, and run it once more. If it fails again, report it, and stop.

### Step 4 — Answer

Show the result as a markdown table. If it has more than about 20 rows, show 20, with "(showing 20 of N)". Unless `--raw` is given, add a 1–3 sentence answer to the question, with the key numbers.

## Examples

- `/query-snowflake how many users signed up last week`
- `/query-snowflake --db <name> top 10 portfolios by AUM`
- `/query-snowflake --raw --limit 500 list all KYC failures in the past 30 days`
- `/query-snowflake --explain what's the total deposit volume per org this month`

## Retry

If the user says "retry", reuse no SQL and no discovery result. Run the discovery again, and treat the question as new.
