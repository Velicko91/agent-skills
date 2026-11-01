---
name: test-on-dev
description: Tests one service on the dev environment, against given acceptance criteria or with exploratory tests, through MCP, REST, GraphQL, or gRPC, and reports pass or fail with evidence. Use for "/test-on-dev <service>", "test this on dev", or "verify on dev".
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Skill, Bash(curl *), Bash(grpcurl *), Bash(jq *), Bash(python3 *), Bash(git *), Bash(gh pr diff*), Bash(kubectl *), Bash(gcloud auth print-identity-token*), Bash(mkdir *), Bash(chmod *), Bash(cp *), Bash(diff *), Bash(date *), Bash(rm /tmp/test-on-dev/*), mcp__linear__get_issue
---

# Test on Dev

Test one service on the dev environment. Plan the tests, wait for a yes, run them, and report each result with the call and the response.

## Hard rules

- ALWAYS send calls only to a host in the "Dev hosts" list of the service file. If a URL or a kubectl context is not on that list, STOP and say which one, because a call to staging or prod can change real data.
- ALWAYS show the test plan and WAIT for a yes before the first call, because a test can change data on dev.
- NEVER print a token, a password, or another secret. Refer to it by its variable or file name.
- Keep a token only in the token file of the run (Step 3). Delete that file at the end of the run, also after a failure.
- If a token, a test account, or a value is missing and the service file gives no command to get it, ask the user for it. STOP and WAIT. NEVER guess it.
- NEVER copy a value from a service file into `skill.md`, because `skill.md` is public.
- Write a phase marker when each phase starts, as `~/.claude/skills/phase-markers/skill.md` says. The ID is the `⟨ph:…⟩` on the phase heading.

## Service files

Each service has a file: `<skill-dir>/services/<service>.local.md`. It holds the dev hosts, the endpoints for each protocol, how to get a token, the test data, the mandatory tests, the main flows, and the known problems. The shape is in `services/TEMPLATE.example.md`. The `*.local.md` files are gitignored.

- If the file does not exist, copy `services/TEMPLATE.example.md` to it. Ask the user for the dev hosts and the endpoints. STOP and WAIT.
- Put each service in its own file. NEVER add a second service to a file.

## Arguments

```
/test-on-dev <service> [<criteria | file | ticket-id>] [--random] [--via mcp|rest|gql|grpc] [--evidence]
```

| Argument | Required | Meaning |
|---|---|---|
| `<service>` | yes | The name of the service file, without `.local.md` |
| `<criteria>` | no | The acceptance criteria as text, a file path, or a ticket ID such as `PROJ-1234` |
| `--random` | no | Exploratory tests. Also used when no criteria are given |
| `--via <protocol>` | no | Run every test through this protocol |
| `--evidence` | no | After the run, make a PNG of the calls with `/make-curl-png` |

## Workflow

### Step 1 — Read the service and the criteria ⟨ph:f71cb202⟩

1. Read `services/<service>.local.md`.
2. Read the criteria:
   - A ticket ID: follow "Select the tracker" in `~/.claude/skills/tracker/skill.md`. Read the acceptance criteria with the Fetch tool of the adapter.
   - A file path: read the file.
   - Text: use it as it is.
3. If there are no criteria, or `--random` is given, design exploratory tests:
   - If the current folder is a checkout of the service, read the change. If the branch has a PR, use `gh pr diff`, because after a merge `git diff` against the default branch is empty. Otherwise use `git diff origin/HEAD...HEAD`. Test what the diff changes, and the edge cases of it: empty input, a missing field, a wrong type, no permission, a repeated call.
   - Otherwise, test the "Main flows" of the service file.

### Step 2 — Write the test plan ⟨ph:30daf65d⟩

Read `protocols.md` for the call pattern of each protocol.

For each criterion or exploratory test, write one test with concrete values. Choose the protocol from the service file, or use `--via`. Add the "Mandatory tests" of the service file.

```
## Test plan - <service> on dev

| # | Test | Protocol | Call | Expect | Writes |
|---|------|----------|------|--------|--------|
| M1 | Health | REST | GET <dev-host>/health | 200 | no |
| T1 | <criterion 1> | GQL | mutation createThing(...) | thing returned, status ACTIVE | yes |
| T2 | <edge case> | gRPC | acme.v1.Things/Get {id: "missing"} | NOT_FOUND | no |

Needs: <tokens, accounts, or port forwards, and where each comes from>
```

Mark each test that creates, changes, or deletes data as `Writes: yes`.

# --- CHECKPOINT ---
Show the plan. STOP and WAIT for a yes. If the user changes the plan, show it again.

### Step 3 — Prepare access ⟨ph:aad0f0bb⟩

1. Make the run folder: `mkdir -p /tmp/test-on-dev/<service>-<YYYYMMDD-HHMM>`.
2. For each token, run the command from "Test access" of the service file. Write the token to `<run folder>/.token-<name>`, then `chmod 600` it.
3. If there is no command, or it fails, ask the user for the token. STOP and WAIT. Write the answer to the token file in the same way.
4. Start the port forwards that "Dev hosts" names, in the background. Check the kubectl context first.

### Step 4 — Run the tests ⟨ph:92b0edeb⟩

1. Run the tests in the order of the plan. Read each token from its file in the command, for example `-H "Authorization: Bearer $(cat <run folder>/.token-api)"`.
2. Save each response to `<run folder>/<test #>.json`.
3. Compare each response with "Expect". A test passes only if each expected part is true.
4. If a test fails, read the dev logs of the call with `/get-gcloud-logs` for the `logs` alias of the service file, from 1 minute before the call. Pass `--file-path <run folder>/logs-<test #>.json`.
5. If a test fails because of a known problem in the service file, mark it `blocked`, not `fail`, and name the problem.

### Step 5 — Report ⟨ph:fe460019⟩

Give the result first:

```
## <service> on dev - <passed>/<total> passed

| # | Test | Result | Evidence |
|---|------|--------|----------|
| T1 | <criterion> | ✅ pass | 200, status ACTIVE |
| T2 | <edge case> | ❌ fail | expected NOT_FOUND, got INTERNAL - log: "<error line>" |
| T3 | <test> | ⏸ blocked | <known problem> |

Data created on dev: <IDs, so the user can clean them up, or "none">
Responses: <run folder>
```

Then:
1. Delete each token file: `rm /tmp/test-on-dev/<run>/.token-*`.
2. Stop the port forwards that this run started.
3. If `--evidence` is given, run `/make-curl-png` with the calls of the tests. Use the token variable, never the token.
4. If the run taught something new, for example a token command, a host, a test account, or a known problem, show it as a diff of the service file, and ask: "Add this to `services/<service>.local.md`?" STOP and WAIT. Write the file only after a yes.

## Examples

- `/test-on-dev acme-ledger PROJ-1234` — tests the acceptance criteria of the ticket
- `/test-on-dev acme-ledger "a refund over the balance returns 422"` — tests one criterion
- `/test-on-dev acme-ledger --random` — exploratory tests of the branch diff, or of the main flows
- `/test-on-dev acme-ledger PROJ-1234 --via grpc --evidence` — gRPC only, with a PNG for the PR

## Retry

If the user says "retry", reuse no response and no token. Read the service file and the criteria again, and start from Step 1.
