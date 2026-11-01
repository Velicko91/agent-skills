---
name: solve-ticket
description: Solves a ticket from the configured tracker (Linear today) end to end — claims it, runs /implement-ticket, then tests, lint, and /create-pr, and moves the ticket to review. Use for "/solve-ticket PROJ-1234" or "take this ticket from start to PR".
user-invocable: true
allowed-tools: "*"
---

# Solve Ticket

Take a ticket from claim to PR. `/implement-ticket` does all design and implementation. This skill does the lifecycle steps around it.

## Hard rules

- NEVER write code directly. All design and implementation goes through `/implement-ticket`.
- NEVER skip `/update-tests --auto --branch` or `/lint`, and NEVER run `/create-pr` before both pass.
- Do not change source code to make a test pass. If a test shows a real bug, report it to the user.
- NEVER force-push. Stage files by name, never `git add .`.
- Find the review state at runtime, because team workflows differ.
- NEVER script code changes (`sed -i`, `awk`, `perl -pi`, `python`, heredocs). Use Edit and Write only, one clear change at a time. Scripts are fine for reading code.
- Follow the Rules of the tracker adapter on every tracker call.

## Tracker

Follow "Select the tracker" in `~/.claude/skills/tracker/skill.md`, and read the adapter. Steps 1 and 6 use its Tools and States sections.

## Arguments

`$ARGUMENTS` is a ticket ID or URL (adapter: Identify), for example `PROJ-1234`.

## Workflow

### Step 1 — Claim the ticket

1. Fetch the ticket, and record its team.
2. Assign it to yourself, and move it to the started state (adapter: States).
3. Report:
   ```
   🎫 PROJ-1234 — <title>
   👤 Assigned to: you
   ▶️  State: <state>
   ```

### Step 2 — Design and implement

Run `/implement-ticket $ARGUMENTS`. It explores the code, writes the plan with 3 self-review passes, waits for approval, implements, runs the tests, and runs `/review-code` until it is clean.

Do not go to Step 3 until `/implement-ticket` is complete and the implementation is done.

### Step 3 — Tests

Run `/update-tests --auto --branch`, and follow it until the tests pass.

### Step 4 — Lint

Run `/lint`. Fix each issue, and run it again until it is clean.

### Step 5 — Create the PR

Run `/create-pr`. The PR title holds the ticket ID after the colon, for example `feat: [PROJ-1234] …`, so the tracker links the PR to the ticket.

### Step 6 — Move the ticket to review

Move the ticket to the review state (adapter: States). If no review state exists, leave the ticket in its started state, and say so in the report.

If the tracker did not link the PR to the ticket, add a comment with the PR link (adapter: Tools).

### Report

```
✅ Done — PROJ-1234

🔗 PR: <pr url>
🎫 Ticket: <state>

Summary of changes:
- <file>: <what changed>
```

## Examples

- `/solve-ticket PROJ-1234`
- `/solve-ticket https://linear.app/<workspace>/issue/PROJ-1234/add-pagination-to-positions`
