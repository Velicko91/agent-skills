---
name: create-ticket
description: Turns the user's bullets into a well-grounded ticket in the configured tracker (Linear today) — inspects the code to state the reason, the issue, and the acceptance criteria, never the implementation. Use for "/create-ticket", "create a ticket", or "file an issue for this".
user-invocable: true
allowed-tools: mcp__linear__save_issue, mcp__linear__get_issue, mcp__linear__list_issues, mcp__linear__list_teams, mcp__linear__list_issue_labels, mcp__linear__create_issue_label, mcp__linear__list_cycles, mcp__linear__list_users, mcp__linear__list_projects, Read, Grep, Glob, Bash(git *), EnterPlanMode, ExitPlanMode
model: sonnet
---

# Create Ticket

Inspect the code behind the user's bullets, and create a ticket that states the reason, the issue, and the acceptance criteria.

## Hard rules

- NEVER write implementation details: no file lists, no function names as instructions, no test names, no migration plans, no size estimates. The implementer decides those.
- Acceptance criteria describe observable outcomes, never code changes.
- One ticket for each repository, if the work spans several.
- Split on outcomes that can be delivered alone, never on size or on implementation layers.
- Follow the rules of the tracker adapter on every call.

## Tracker

Follow "Select the tracker" in `~/.claude/skills/tracker/SKILL.md`, and read the adapter. Use its Config, Tools, and Create sections in the steps below.

## Arguments

| Flag | Effect |
|---|---|
| `--team <name\|key\|id>` | The team. Default: the team that "Choose the team" in the adapter selects. |
| `--label <name>` | Add a label. Repeatable. |
| `--priority <0-4 \| urgent \| high \| medium \| low>` | The priority. Default: none. |
| `--assignee <email \| name \| "me">` | The assignee |
| `--parent <ID>` | Make it a sub-issue |
| `--project <name\|id>` | The project |
| `--cycle [<name\|number\|id>]` | The cycle. With no value, the current cycle of the team. |
| `--milestone <name\|id>` | The project milestone |
| `--estimate <n>` | The estimate |
| `--state <name>` | The state. Default: the default state of the adapter (`Backlog` for Linear). |
| `--no-code` | Write the ticket from the bullets only |

Use the defaults with no confirmation.

## Conventions

Title prefixes, only when they fit. Most tickets have no prefix:

| Prefix | Use |
|---|---|
| `[FE]` | Frontend only (UI, components, animations) |
| `[BE]` | Backend only (APIs, services, DB queries) |
| `[FE, NTH]` | Frontend work that is nice to have |
| `[Copilot]` | Work on the Copilot AI feature |
| `[Wire out]` | Wiring or integration of existing parts |
| `[Spike]` | Investigation or research |
| `[Refactor]` | Cleanup with no change of behaviour |

Common labels, only when they clearly fit: `Bug`, `Feature`, `Front-End`, `Back-End`, `Refactor`.

## Workflow

### Step 1 — Parse the bullets

Record the intent, the explicit flags, the code references (files, functions, services), and the prefix and labels that the context suggests.

### Step 2 — Investigate the code

Unless `--no-code` is given, enter plan mode, and look at the referenced code and `git log --oneline -20`. Investigate only to ground the problem, never to design the solution:
- **Evidence** that the problem is real: the code, config, or behaviour that causes it
- **Who or what** is affected: users, services, flows
- **Repositories** in scope

Name specific code only where it makes the problem concrete, for example the endpoint that misbehaves. Exit plan mode after the investigation.

### Step 3 — Split

- **Several repositories:** one ticket for each. Add the repository to the title (`[billing-service]`), keep only its own reason and criteria, and link the siblings (adapter: Create) with a "Related: <ID>" note.
- **Several outcomes:** one sub-issue for each, with its own criteria that can be verified alone, under the original ticket.

### Step 4 — Write the ticket

**Title:** `[Optional Prefix] Clear, action-oriented title`

**Description** (Markdown, with real newlines):

```
## Reason

Why this matters and why now — the impact if it stays as it is. Who is affected.

## Issue

What is wrong or missing. Current behaviour vs. expected behaviour. Name the service or flow, but do not prescribe a fix.

## Acceptance Criteria

* <observable outcome someone else can verify>
* <another outcome>
* <edge case or failure mode that must be handled>
```

The acceptance criteria are the contract:
- Write behaviour, not code: "Expired tokens return 401 with a refresh hint", not "add a check in `validate_token()`".
- Make each criterion verifiable alone.
- Cover the failure and edge cases, not only the happy path.
- If you cannot state a criterion observably, put it in **Reason** as context.

### Step 5 — Create

1. Resolve the lookups: the current cycle for `--cycle` with no value, the label for each new `--label` (an existing close match, or create it), and the team ID if the adapter needs it.
2. Create each ticket with the Create tool and fields of the adapter. Pass the state explicitly.
3. Link the siblings of a multi-repo split.

### Step 6 — Output

For each ticket:

```
✅ Created: <ID>
🔗 <ticket link>

Title: <title>
Team: <key> (<the rule that chose it>)
Labels: <labels>
Cycle: <cycle or "—">
Priority: <name>
```

Then add a short note on the code context used, the repositories found, and any split.

## Examples

- `/create-ticket add ON_HOLD state that sells assets before moving to REQUESTING`
- `/create-ticket --label Bug login fails when token is expired`
- `/create-ticket --label Feature --parent PROJ-100 users can export portfolio as CSV`
- `/create-ticket --cycle --priority high fix memory leak in the order processor`
- `/create-ticket --no-code [FE] update button color in invoice drawer`

## Retry

If the user says "retry", reuse no team, label, or cycle lookup and no draft. Read the files and fetch the tracker data again.
