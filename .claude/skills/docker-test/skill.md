---
name: docker-test
description: Starts and tests the local Docker stack of the current repo — takes a per-repo lock, makes sure the running stack is from this checkout, applies per-service rules, runs the mandatory test cases, and checks the logs. Use for "/docker-test", "test this locally", or "run the stack".
user-invocable: true
allowed-tools: Bash(~/.claude/skills/docker-test/lock.sh *), Bash(docker *), Bash(make *), Bash(cat *), Bash(git *), Bash(cp *), Bash(lsof *), Bash(curl *), Bash(python3 *), Bash(kubectl *), Read, Glob, Grep
model: sonnet
---

# Docker Test

Start the stack of this checkout, run the mandatory tests, check the logs, and report. A user or another skill can start it.

## Hard rules

- ALWAYS hold the lock (Step 3) before you check, start, stop, or test the stack. Release it at the end, also after a failure.
- NEVER release a lock that another session holds. NEVER take over a live lock without the user's order (`--takeover`, or an answer in Step 3).
- ALWAYS run Step 4 before you start anything, because a stack from another checkout answers with old code.
- ALWAYS print the test plan (Step 7) before you run a test.
- NEVER print a token, a password, or another secret. Refer to it by its variable or file name.
- NEVER port-forward from a production kubectl context.
- NEVER stop the stack at the end unless `--stop` is given, because another session may use it next.
- Prefer `make` targets to raw `docker compose`. Always start detached (`-d`).
- If the containers fail to start, report the error, release the lock, and stop.
- If another skill started this skill, report the summary only, unless there are errors.

## Local configuration

Each service has a rules file: `<skill-dir>/rules/<repo-name>.local.md`. `<repo-name>` is the last part of `git remote get-url origin`, without `.git`. The file holds the setup steps, the environment, the dev-environment port forwards, sandbox testing, how to get a token, the test data, the required headers, and the mandatory tests of that service.

- If the file exists, follow it in Steps 5 to 8.
- If it does not exist, use generic discovery. At the end, offer to create it from `rules/TEMPLATE.example.md` with what you learned.
- Put each service in its own file. NEVER add a second service to a rules file.
- NEVER copy values from a rules file into `skill.md`, because `skill.md` is public.

## Arguments

```
/docker-test [what is tested] [--service <name>] [--lines N] [--follow] [--stop] [--no-start] [--no-build] [--wait | --takeover]
```

| Argument | Default | Effect |
|---|---|---|
| `[what is tested]` | — | Selects the logs to watch and the tests to plan |
| `--service <name>` | all services | The service to watch |
| `--lines N` | `50` | The number of log lines |
| `--follow` | snapshot | Follow the logs live |
| `--stop` | keep running | Stop the stack at the end. Use it only if no other session needs the stack. |
| `--no-start` | start | Assume that the stack runs |
| `--no-build` | rebuild if the checkout is newer than the container | Never rebuild |
| `--wait` | ask | If another session holds the lock, wait up to 15 minutes |
| `--takeover` | ask | If another session holds the lock, take it over |

## Mandatory tests

Plan and run these tests, plus the "Mandatory tests" of the rules file. Skip a test only if it cannot apply, for example M3 for a service with no auth. Give the reason in the plan.

| # | Test | Pass when |
|---|------|-----------|
| M1 | Stack health | Every container of this checkout's compose project is `running`, and `healthy` if it has a health check |
| M2 | Service responds | The health or readiness endpoint (from the rules file, or the first published HTTP port) returns `2xx` |
| M3 | Auth is enforced | The endpoint under test without credentials returns `401` |
| M4 | Happy path | The endpoint under test with valid access returns the expected `2xx` status and response shape |
| M5 | Invalid input | The endpoint under test with an unknown ID or an invalid body returns the expected `4xx`, never `5xx` |
| M6 | Clean logs | The service logs have no new `ERROR`, `panic`, or stack trace from the test window |

## Workflow

### Step 1 — Discover the repo

```bash
ls docker-compose*.yml docker-compose*.yaml compose*.yml 2>/dev/null
grep -E "^[a-zA-Z][a-zA-Z0-9_-]*:" Makefile 2>/dev/null | grep -iE "docker|start|stop|up|down|dev|test|run|build" | head -30
docker compose config --services 2>/dev/null
docker compose config --format json 2>/dev/null | python3 -c 'import json,sys; c=json.load(sys.stdin); [print(n, [p.get("published") for p in s.get("ports",[])]) for n,s in c["services"].items()]'
git worktree list
```

Find the compose command (a `make` target or raw `docker compose`), the services and their host ports, the shortcut targets (`make dev`, `make up`, `make test`), and whether this is a worktree. The first entry of `git worktree list` is the main checkout. Then read the rules file.

### Step 2 — Pick the log target

Use `--service` if given. Otherwise match the description against the service names. If nothing matches, use all services.

### Step 3 — Take the lock

All checkouts of a repo share the host ports, so only one session may test the stack at a time.

```bash
~/.claude/skills/docker-test/lock.sh acquire <repo-name> "<what is tested>"
```

| Result | Action |
|---|---|
| `ACQUIRED` | Continue. |
| `STALE` | The holder's session ended, and the script replaced the lock. Continue. |
| `HELD` (exit 3) | Show the holder (checkout, purpose, since). Follow `--wait` or `--takeover`, or ask: "`<checkout>` is testing "`<purpose>`" since `<since>`. **Wait** for it, or **take over** (its tests may fail midway)?" STOP and WAIT. |

- **Wait:** run `acquire` again every 30 seconds, for up to 15 minutes. If the lock is still held, ask again.
- **Take over:** run `lock.sh takeover <repo-name> "<purpose>"`. If ListAgents shows the holder's session, send it a short SendMessage that its lock was taken over.

### Step 4 — Check which stack runs

```bash
docker ps --format '{{.Names}}\t{{.Ports}}\t{{.Label "com.docker.compose.project.working_dir"}}'
lsof -nP -iTCP:<port> -sTCP:LISTEN
```

| What runs | Action |
|-----------|--------|
| This checkout's stack, built after the last change | Reuse it. Skip Step 5 unless a service is down. |
| This checkout's stack, older than the last change | Rebuild in Step 5 (`--build`), unless `--no-build`. |
| The same repo's stack from another checkout | You hold the lock, so no session tests it. Run `docker compose --project-directory <working_dir> down`, then start this stack in Step 5. |
| An unrelated project holds a needed port | List it, and ask before you stop it. STOP and WAIT. |
| Nothing runs | Start in Step 5. |

"Built after the last change" means that the container start time (`docker inspect -f '{{.State.StartedAt}}' <container>`) is later than both `git log -1 --format=%cI` and the newest modification time of the files in `git status --porcelain`.

### Step 5 — Start the stack (unless `--no-start`)

1. Apply the setup steps of the rules file, in order. Without a rules file, use these defaults:
   - In a worktree, copy `.env` from the main checkout if it is missing. If the main checkout has none, copy `.env-example`.
   - If an environment variable that the build needs is missing, STOP and name it. Never print its value.
   - If the test needs a real dependency, follow "Connect to the dev environment": confirm that the kubectl context is dev, start only the port forwards that the endpoints under test need, in the background, and set their addresses in `.env`.
   - If the user asks to test on sandbox, follow "Test on sandbox".
2. Start the stack: `make up` (or `make dev`, `make start`, `make docker-up`). If no target exists, run `docker compose up -d`, with `--build` if Step 4 said rebuild.
3. Wait until `docker compose ps` shows the containers healthy.
4. Report which containers run, and from which directory.

### Step 6 — Prepare test access

If the rules file gives a token command, test data, or required headers:

1. Run the token command. Bash calls do not share shell variables, so write the token to a file that only you can read: `umask 077; <token command> > /tmp/docker-test-<repo-name>.token`. In each request, use `$(cat /tmp/docker-test-<repo-name>.token)`.
2. Record the test data (for example test account IDs) and the headers that every request needs.
3. Give the token file path, the test data, and the headers to the caller. The next run overwrites the file.

### Step 7 — Print the test plan

Print every test that you will run, with concrete values: M1–M6, the tests of the rules file (S1…), and the tests of the change (T1…).

```
🧪 Test plan - <what is being tested>

| # | Test | Request / check | Expect |
|---|------|-----------------|--------|
| M1 | Stack health | docker compose ps | api, db running + healthy |
| M3 | Auth is enforced | GET /v1/cards/card_123, no token | 401 |
| M4 | Happy path | GET /v1/cards/card_123 | 200, has id, status |
| S1 | <rules-file test> | <request> | <expected> |
| T1 | <change-specific test> | <request> | <expected> |
| -- | M2 skipped | no health endpoint in this service | - |
```

If every test only reads, continue. If a test changes data (`POST`, `PUT`, `PATCH`, `DELETE`), mark it and ask: "These tests change data. Run them? (yes / skip them)". STOP and WAIT.

### Step 8 — Run the tests

Record the time, then run the tests in order. Record the actual status and a one-line result for each. Do not stop at the first failure, so the report shows every problem.

### Step 9 — Capture the logs

```bash
docker compose logs --since <test start time> --tail=<lines> <service>   # snapshot; M6 uses this window
docker compose logs --tail=<lines>                                       # all services
docker compose logs --follow <service>                                   # --follow
```

If the output is longer than 100 lines, summarize the errors and exceptions, the startup messages, and the warnings that relate to the change.

### Step 10 — Release the lock

```bash
~/.claude/skills/docker-test/lock.sh release <repo-name>
```

Release it also when tests failed. Leave the containers running. Only with `--stop`, run `make down` (or `make stop`, `make docker-down`), else `docker compose down`.

### Step 11 — Output

```
✅ Stack running — <N> containers up (from <checkout dir>)

🔒 Lock: released (held <duration>)   ← or "taken over from <checkout>"
🔁 Replaced: <other checkout>'s stack   ← only if Step 4 stopped one
🐳 Services: <service1>, <service2>, ...
🔑 Test access: token in <file>, headers: <header names>   ← only if Step 6 ran

🧪 Tests: <passed>/<total> passed
| # | Test | Expect | Actual | Result |
|---|------|--------|--------|--------|
| M1 | Stack health | running + healthy | running + healthy | ✅ |
| T1 | <change-specific> | 200 | 500 | ❌ |

📋 Logs (<service>):
---
<log output or summary>
---

[🛑 Stack stopped]  ← only if --stop was used
```

If the logs have errors, show them first:

```
⚠️  Errors detected in <service> logs:
- <error message>
```

### Step 12 — Update the PR description

Run this step when the tests check a code change, and `gh pr view --json number,body` finds an open PR for the current branch. Ask no question. Without a PR, print the table for later. Skip the step for a log-only run (`--no-start`).

1. Choose the most important cases, at most 20 rows. Keep the happy path, each new error status, the auth and scope checks, each flag state, and the read before and after a write. Merge the passing M1, M2, and M6 rows into one line under the table. If more cases ran, write the number left out under the table.
2. Write the section. Its header is the "PR section header" of the rules file, else `## Docker tested`. Start it with two or three sentences: where the tests ran (for example the local environment with dev port forwards, or the sandbox), each temporary change made for the run (a spec flag, a local flag), and what the run did not cover.
3. Give the table these columns, one row for each case, with the real result:

   ```
   | # | Test | Request / check | Expect | Actual |
   |---|------|-----------------|--------|--------|
   | T1 | <case> | `<METHOD> <path>` | `204` | ✅ `204` |
   ```

4. Replace the existing section with that header, or a `## Manual verification` section, or add the section before the ticket link and the footer. Keep every other section as it is. Write the new body to a file, then run `gh pr edit <number> --body-file <file>`.
5. Put no token, password, or pass count in the section.

## Examples

- `/docker-test` ← full stack, mandatory tests, logs
- `/docker-test testing the authentication flow`
- `/docker-test --no-start --service api --lines 100` ← only recent logs
- `/docker-test testing GET /v1/cards --wait`
- `/docker-test --stop` ← test, then stop the stack
