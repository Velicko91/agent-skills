---
name: create-worktree
description: Creates a git worktree with a properly named branch for a ticket of the configured tracker (Linear today) or a free-text task, copies the files in .worktreeinclude, and prints how to start the session. Use for "create worktree for PROJ-1234" or "/create-worktree <ticket | description>".
user-invocable: true
allowed-tools: "*"
---

# Create Worktree

Create an isolated git worktree with a properly named branch, for a ticket or a free-text task, and set it up for implementation.

## Hard rules

- NEVER create the worktree before the user confirms the plan.
- Ask all questions in one message.
- NEVER use `git worktree add -B`, because it resets a branch that exists, and its commits can be lost.
- NEVER edit `.gitignore` without asking, because it is a tracked, shared file.
- NEVER guess an issue tracker host.

## Tracker

Follow "Select the tracker" in `~/.claude/skills/tracker/SKILL.md`, and read the adapter. Its Identify section gives the ID and URL patterns and the ticket link; its Tools section gives the fetch tool. If `~/.claude/config.local.json` is missing, copy `config.example.json`, and ask the user to fill it in.

## Arguments

| Form | Example | Behaviour |
|------|---------|-----------|
| Ticket URL | `https://linear.app/<workspace>/issue/PROJ-1234` | Fetch the ticket, and name the branch from its title |
| Ticket ID | `PROJ-1234` | Fetch the ticket, and name the branch from its title |
| Free-text description | `"add caching to auth middleware"` | Name the branch from the description |
| ID + extra context | `PROJ-1234 focus on the gRPC part only` | Fetch the ticket. The extra text is a constraint for the implementation. |

## Workflow

### Phase 1 — Parse the arguments

- A URL or an ID that matches the adapter (Identify) → `has_ticket = true`. The text after it is `extra_context`.
- Anything else → a free-text description, `has_ticket = false`.

### Phase 2 — Name the branch

**With a ticket:** fetch it with the adapter, and take the title, the description, and the labels.

**Branch format:** `<type>/<ID>-<slug>`, or `<type>/<slug>` with no ticket.
- `type`: `fix` if a label is `Bug` or `Incident`, `refactor` if a label is `Refactor`, else `feat`.
- `slug`: the title (or the first ~5 words of the description), lowercase, with hyphens for other characters, at most 40 characters, without title prefixes such as `[FE]`, `[BE]`, `[Spike]`.

Examples:
- `PROJ-1234` + `"Improved logging on GQL schema"` → `feat/PROJ-1234-improved-logging-gql-schema`
- `PROJ-5678` + `"Add gRPC for withdrawals"` → `feat/PROJ-5678-add-grpc-for-withdrawals`
- `"fix the price calculation returning zero"` → `feat/fix-the-price-calculation-returning` (or `fix/…` if the user says it is a bug)

The worktree ID (its folder name) is the ticket ID, or the slug with no ticket.

**Relevant areas:** look in the current repo with Grep, Glob, and Read for the areas that the work touches. Do not draft an implementation plan: the new session in the worktree does not see this context, so `/implement-ticket` plans there.

### CHECKPOINT — Present the plan

```
## Worktree Plan

**Ticket:** PROJ-1234 — <title>           (or "Description: <text>")
**Branch:** feat/PROJ-1234-short-slug
**Worktree path:** .claude/worktrees/PROJ-1234

### What needs to be done
<summary from the ticket or the description>

### Relevant areas of the codebase
- `path/to/file.py` — reason

### Questions / Unknowns          (omit if none)
- <question>
```

Ask: "Shall I create the worktree, or do you want to adjust anything?" STOP and WAIT.

### Phase 3 — Create the worktree

1. Get the repo root: `git rev-parse --show-toplevel`.
2. Make sure that `origin/HEAD` is set: `git remote set-head origin -a 2>/dev/null || true`.
3. Check that `.claude/worktrees/` is ignored: `git check-ignore -q <repo-root>/.claude/worktrees/x`. If it is not, ask to add `.claude/worktrees/` to `.gitignore`, and WAIT.
4. Create the worktree from `origin/HEAD`, unless the user named another base:
   ```bash
   git worktree add -b <branch> <repo-root>/.claude/worktrees/<worktree-id> origin/HEAD
   ```
   If the branch exists already, stop, and ask: use the existing branch (`git worktree add <repo-root>/.claude/worktrees/<worktree-id> <branch>`), or pick a new name.
5. If `<repo-root>/.worktreeinclude` exists, copy the ignored files that its patterns match:
   ```bash
   while IFS= read -r pattern; do
     [[ -z "$pattern" || "$pattern" == \#* ]] && continue
     git -C <repo-root> ls-files --others --ignored --exclude="$pattern" -z |
       while IFS= read -r -d '' f; do
         mkdir -p "$(dirname "<worktree-path>/$f")"
         cp "<repo-root>/$f" "<worktree-path>/$f"
       done
   done < "<repo-root>/.worktreeinclude"
   ```
   If the file does not exist, skip this step, and say in the output that env files can be missing.
6. Check with `git worktree list`.

### Phase 4 — Output

```
✅ Worktree ready

🌿 Branch:   feat/PROJ-1234-short-slug
📁 Path:     <repo-root>/.claude/worktrees/PROJ-1234
🎫 Ticket:   <ticket link>   (if any)

To start your session:

  cd <repo-root>/.claude/worktrees/PROJ-1234 && claude

Once inside the session, run:

  /implement-ticket PROJ-1234                 (with a ticket)
  /implement-ticket "<description>"           (with no ticket)
```

Add the `extra_context` to the `/implement-ticket` command, if there is one.

## Examples

- `/create-worktree PROJ-1234`
- `/create-worktree https://linear.app/<workspace>/issue/PROJ-1234`
- `/create-worktree PROJ-1234 focus on the Kafka handler only, skip gRPC`
- `/create-worktree add rate limiting to the GraphQL API`

## Retry

If the user says "retry", reuse no ticket data and no branch name. Fetch the ticket again, and name the branch again.
