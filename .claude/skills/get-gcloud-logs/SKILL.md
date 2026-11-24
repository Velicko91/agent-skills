---
name: get-gcloud-logs
description: Fetches the GKE logs of a configured service with gcloud logging read, saves them as JSON, and can extract fields to CSV with jq. Services, namespaces, and projects come from the local config. Use for "get the logs of <service>", "find errors in <service>", or "/get-gcloud-logs".
user-invocable: true
allowed-tools: Bash(gcloud *), Bash(jq *), Bash(mkdir *), Bash(echo *), Bash(date *), Write, Read, Grep, Glob
model: haiku
---

# Get GCloud Logs

Fetches GCP Kubernetes logs via `gcloud logging read`, saves as JSON, and optionally extracts fields to CSV with `jq`.

## Defaults

| Field       | Default                                      | Override                  |
|-------------|----------------------------------------------|---------------------------|
| `env`       | `dev`                                        | `--env staging\|prod`     |
| `limit`     | `200`                                        | `--limit N`               |
| `freshness` | `1h`                                         | `--freshness 2h\|24h\|7d` |
| `severity`  | none (all levels)                            | `--severity ERROR\|WARNING\|INFO` |
| `file-path` | `./<service>-<env>-<timestamp>.json`         | `--file-path /path/to/file.json` |
| `format`    | JSON                                         | always JSON               |

## Service Context — read from local config

**Read `~/.claude/config.local.json` before you build any query.** The `gcp` section
holds every project ID, namespace, and container name. This skill hardcodes none of them.

- `gcp.services[]` — each entry has `aliases`, `namespace`, `environments`, `containers` (application deployments), `jobContainers` (scheduled or batch work: CronJobs, or a worker that runs scheduled tasks), `helperContainers` (proxies, metrics, debug pods), and `envOnly` (containers that exist only in some envs).
  Match the user's service argument against `aliases`.
- `gcp.environments.<env>` — gives `project` and `cluster` for `dev`, `staging`, `prod`. A service entry can have its own `environments`, with the same shape, for a service that runs in other projects; it wins over the global one.
- `gcp.defaultService` and `gcp.defaultEnv` — used when the user names neither.

If the config is missing, copy `config.example.json` and ask the user to fill in the
`gcp` section. **NEVER guess a project ID, a namespace, or a container name** — a wrong
project returns an empty result that looks like a healthy service.

If the user names a service that matches no alias, list the available aliases from the
config and stop. Do not query a guessed namespace.

## Argument Parsing

```
/get-gcloud-logs <service> [search text] [--env dev|staging|prod] [--limit N]
                           [--freshness Nh] [--severity LEVEL] [--file-path path]
                           [--extract <description>] [--csv]
```

| Argument        | Required | Description                                                    |
|-----------------|----------|----------------------------------------------------------------|
| `<service>`     | Yes      | Service alias from context table above                         |
| `[search text]` | No       | Free-text string to search in log messages (quoted or unquoted)|
| `--env`         | No       | Environment: `dev` (default), `staging`, `prod`               |
| `--limit`       | No       | Max log entries (default: 200)                                 |
| `--freshness`   | No       | Time window: `1h` (default), `2h`, `24h`, `7d`               |
| `--severity`    | No       | Minimum severity: `ERROR`, `WARNING`, `INFO`                  |
| `--file-path`   | No       | Output JSON file path (default: `./<service>-<env>-<ts>.json`)|
| `--extract`     | No       | Natural language description of what to extract to CSV        |
| `--csv`         | No       | Also produce a `.csv` file alongside the JSON                 |

## Workflow

### Step 1 — Resolve Service Context

Match the service argument against the `aliases` of `gcp.services` in the config. Resolve:
- `$PROJECT` — the project of the env: from the service's own `environments` if it has one, else from `gcp.environments`
- `$NAMESPACE` — k8s namespace
- `$CONTAINERS` — `containers` plus `jobContainers`, joined with OR. Leave out each `envOnly` container that does not exist in this env. Never add `helperContainers`, because they hold no application logs. If the user names one container, use only that one.

If no alias matches, list the aliases from the config, and stop.

### Step 2 — Build the Filter

Construct the `gcloud logging read` filter:

```
resource.type="k8s_container"
AND resource.labels.namespace_name="<namespace>"
AND (resource.labels.container_name="<container1>" OR resource.labels.container_name="<container2>")
[AND (textPayload:"<search>" OR jsonPayload.message:"<search>")]
[AND severity>="<SEVERITY>"]
```

For single container, omit the OR grouping.

### Step 3 — Determine Output File Path

- If `--file-path` is given: use it
- Otherwise: generate `./<service>-<env>-<timestamp>.json`
  - Timestamp format: `YYYYMMDD-HHmmss` (run `date +%Y%m%d-%H%M%S`)

### Step 4 — Fetch Logs

Run:
```bash
gcloud logging read '<filter>' \
  --project=<project> \
  --limit=<limit> \
  --freshness=<freshness> \
  --format=json > <file-path>
```

Report how many entries were fetched:
```bash
jq 'length' <file-path>
```

### Step 5 — Extract to CSV (if `--extract` or `--csv`)

If the user asked to extract specific fields, translate the natural-language description into a `jq` expression.

**Common extraction patterns:**

Extract a top-level field + flatten all jsonPayload fields as key=value into one column:
```bash
jq -r '.[] | [
  .jsonPayload.<field1>,
  .jsonPayload.<field2>,
  (.jsonPayload | to_entries | map("\(.key)=\(.value|tostring)") | join("|"))
] | @csv' <file>.json > <file>.csv
```

Extract specific fields only:
```bash
jq -r '["field1","field2","timestamp"], (.[] | [
  .jsonPayload.field1,
  .jsonPayload.field2,
  .timestamp
]) | @csv' <file>.json > <file>.csv
```

CSV file path: same as JSON but with `.csv` extension.

Show the first 3 rows of the CSV after creation.

### Step 6 — Output

```
✅ Fetched <N> log entries

📋 Service:   <alias> → <namespace>/<container>
🌍 Project:   <project> (<env>)
⏱  Freshness: <freshness>
🔍 Filter:    <filter string>

💾 JSON saved: <file-path>
📊 CSV saved:  <csv-path>   (if applicable)
```

## Rules

- ALWAYS save logs to a file — never just print raw JSON to the terminal
- ALWAYS use `--format=json` for gcloud (never default text format)
- When extracting to CSV, add a header row as the first line
- When multiple containers match an alias, include ALL of them with OR in the filter
- Wrap the whole filter in single quotes, so the shell does not expand `$` or other special characters; inside it, `$` needs no escape (see the example below). If the search text contains a single quote, write it as `'\''`.
- NEVER modify or delete the output file after writing it

## Examples

```bash
# Fetch ERROR logs from a service (last 1h, default env)
/get-gcloud-logs <service> --severity ERROR

# Search for a specific message
/get-gcloud-logs <service> "balance difference"

# Fetch staging worker logs, last 24h
/get-gcloud-logs <service-worker> --env staging --freshness 24h --limit 500

# Save to a specific path
/get-gcloud-logs <service> --file-path ~/Desktop/errors.json --severity ERROR

# Fetch and extract a field + flatten extra data to CSV
/get-gcloud-logs <service> "some log message" --extract "extract business_gid and flatten extra data" --csv

# Another service, last 2h
/get-gcloud-logs <service> --freshness 2h --severity WARNING
```

## Extraction Example (end-to-end)

**User asks:**
> get log "Speed up delayed settling: Account balance difference is greater than 1$" extract business_gid and flat out extra data into .csv

**Filter built:**
```
resource.type="k8s_container"
AND resource.labels.namespace_name="<namespace from config>"
AND resource.labels.container_name="<container from config>"
AND (textPayload:"Speed up delayed settling: Account balance difference is greater than 1$"
     OR jsonPayload.message:"Speed up delayed settling: Account balance difference is greater than 1$")
```

**jq extraction:**
```bash
jq -r '["business_gid","timestamp","extra_data"], (.[] | [
  .jsonPayload.business_gid,
  .timestamp,
  (.jsonPayload | to_entries | map("\(.key)=\(.value|tostring)") | join("|"))
]) | @csv' service-dev-20260328-120000.json > service-dev-20260328-120000.csv
```
