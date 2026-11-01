---
name: open-claude-session
description: Opens a new, resumed, or forked Claude Code session from the /implement-ticket work log in a cmux workspace group; a fork for the next PR of a ticket opens as a tab beside its source. Use for "open claude in <group>", "resume or fork <session> in <group>", or "/open-claude-session".
user-invocable: true
allowed-tools: Read, Bash(cmux *)
model: haiku
---

# Open Claude Session

Open a Claude Code session in a cmux workspace group. The session is new, resumed, or forked
from a work-log session. Read `rules.md` in this skill folder for where each session opens.

A user can call this skill. Another Claude session can also call it, to start a session
beside itself. The skill does not stop for approval, except when `--resume` or `--fork` has no value, or when
the group name is close to the name of a group that exists.

## Arguments

```
/open-claude-session <group> [--resume [<session>] | --fork [<session>]] [--name <title>]
                     [--agent <agent>] [--cwd <path>] [--prompt "<text>"]
```

| Argument | Required | Applies to | Meaning |
|---|---|---|---|
| `<group>` | yes | both | The name of the cmux workspace group, for example `work` |
| `--resume [<session>]` | no | resume | Resume a session from the work log. With no value, list the sessions and wait |
| `--fork [<session>]` | no | fork | Fork a session from the work log into a new session ID. With no value, list the sessions and wait |
| `--name <title>` | no | new, fork | The name of the Claude session and the title of the workspace or tab |
| `--agent <agent>` | no | new | Run the session as this agent: `claude --agent <agent>` |
| `--cwd <path>` | no | all | The folder where the session starts |
| `--prompt "<text>"` | no | new, fork | The first prompt of the new session |

Parse in this order:
1. The first word that does not start with `--` is `<group>`.
2. Read each flag and its value. For `--resume` and `--fork`, the next word is its value only if it does not start with `--`.
3. If `<group>` is missing, STOP and ask for it. Show the groups from `cmux workspace-group list`.
4. If `--resume` is used together with `--fork`, `--name`, `--agent` or `--prompt`, STOP and say that resume takes only `--cwd`.
5. If `--fork` is used together with `--agent`, STOP and say that a fork keeps the agent of its source.

## Defaults

| Field | Default | Override |
|---|---|---|
| Mode | new session | `--resume`, `--fork` |
| Folder (new) | the current folder | `--cwd <path>` |
| Folder (resume, fork) | the `sessionCwd` of the work-log entry, else the `worktree`, else the current folder | `--cwd <path>` |
| Workspace title (new) | `--name`, else `--agent`, else `claude` | `--name <title>` |
| Tab or workspace title (fork) | `--name`, else `<session>-fork` | `--name <title>` |
| Workspace title (resume) | the `session` of the work-log entry | — |
| Position in the group | at the end | — |

Use the defaults without asking.

## Work log

Resume and fork read only the work log of `/work-log`:

```
~/.claude/skills/work-log/data.json
```

Read the entries in `active`. Each entry holds `ticket`, `title`, `session`,
`worktree`, `status`, `createdAt`, and, in newer entries, `sessionId` and `sessionCwd`.
`sessionId` is the ID that `claude --resume` takes. `sessionCwd` is the folder that owns
the session. Older entries have only `session`, the name of the session.

NEVER write to the work log. Only `/work-log` writes it.

If the file does not exist, or `active` is empty, STOP and say that there is no
session to resume or fork.

## Workflow

### Step 1 — Find or create the group

```bash
cmux workspace-group list --json
```

Find the group whose `name` is `<group>`. Compare without case. Keep its `ref`.

If no group has that name, look for a similar name. Compare without case. A name is
similar if one name contains the other, for example `incident` and `incident-investigation`.

# --- CHECKPOINT ---
If one or more groups have a similar name, STOP and ask which group to use. List the
similar groups and the option to create `<group>` as a new group. Do NOT pick one
yourself, because a new group with a near-duplicate name splits the sessions.

If no group has that name or a similar name, create it:

```bash
cmux workspace-group create --name "<group>" --idempotency-key "group-<group>"
```

Keep the `workspace_group:N` ref from the output. The idempotency key prevents a
second group if two sessions create the same group at the same time.

### Step 2 — Choose the session to resume or fork

Do this step only with `--resume` or `--fork`. The steps are the same for both flags.

**If the flag has a value**, find the entries that match it. Match against
`session` and `ticket`, without case:

1. Use the exact matches. If there are none, use the entries that contain the value.
2. If one entry matches, use it. Do not ask.
3. If more than one entry matches, use the one with the latest `createdAt`. Say which one you used, and name the others.
4. If no entry matches, STOP. List the entries in `active`, and ask which one to use.

**If the flag has no value**, list the entries in `active` with the latest first:

```
📋 Sessions in the work log
  1. PROJ-1301-fix-rounding        in-progress   2026-01-14   Fix settlement rounding
  2. PROJ-1234-add-pagination      in-review     2026-01-02   Add pagination to resolver
```

# --- CHECKPOINT ---
STOP and WAIT for the user to pick a session. Do NOT pick one yourself.

### Step 3 — Build the command

Quote every value for the shell, because cmux types the command into a new terminal.
Put a value in single quotes. Write a single quote inside the value as `'\''`.

**New session:**

```
claude [-n '<name>'] [--agent '<agent>'] ['<prompt>']
```

Add each part only when its flag is set. Put the prompt last.

**Resume:**

```
claude --resume '<sessionId>'
```

**Fork:**

```
claude --resume '<sessionId>' --fork-session [-n '<name>'] ['<prompt>']
```

The fork gets a new session ID, so the source session keeps running and is not changed.

For resume and fork: if the entry has no `sessionId`, use `session`, and say that the command fails if the session was renamed.

`claude --resume` finds a session only from the folder that owns it. Start it in `sessionCwd`. If the entry has no `sessionCwd`, use `--cwd`, else the `worktree`, else the current folder. Then say that the resume can fail, and that `/work-log update --branch <B> --session-id <id>` fixes the entry.

### Step 4 — Open the workspace or the tab

Read `rules.md` in this skill folder, and pick the first rule that matches.

**New tab (rule 1):** find the workspace of the source session.

```bash
cmux workspace list --json
```

Use the workspace whose `title` equals the `session` of the entry. If none matches, use the
workspace whose `current_directory` equals the folder from Step 3. If none matches, open a
new workspace as below. Then add the tab:

```bash
cmux new-surface --workspace <workspace-ref> --working-directory '<folder>' \
  --command "<command from Step 3>"
cmux tab-action --action rename --surface <surface-ref> --title '<title>'
```

Keep the `surface:N` ref from the output of `new-surface`.

**New workspace (rules 2–4):**

```bash
cmux workspace create --group <group-ref> --group-placement end \
  --name '<title>' --cwd '<folder>' --command "<command from Step 3>"
```

Keep the `workspace:N` ref from the output.

### Step 5 — Report

```
✅ Opened in group <group>: workspace:N [surface:N]
   Rule:    <rule number from rules.md>
   Title:   <title>
   Folder:  <folder>
   Command: <command>
```

If Step 1 created the group, add `(new group)` after its name. For a resume or a fork, add the
`ticket` and the `status` of the entry.

## Rules

- ALWAYS open a new workspace, or a new tab when `rules.md` says so. NEVER type into a surface that exists, because a session may be running in it.
- NEVER search `~/.claude/projects` for sessions. Resume and fork use only the work log.
- NEVER resume a running session to continue its work in a second tab. Fork it, because two processes on one session ID write to the same transcript.
- NEVER create a second group with a name that already exists. Compare names without case.
- NEVER create a group when a group with a similar name exists, unless the user confirms it.
- If a `cmux` command fails, STOP and show its output. Do not try a different command.

## Examples

- `/open-claude-session work` — opens a plain Claude session in the group `work`
- `/open-claude-session work --name api-cleanup --cwd ~/code/acme-api` — opens a named session in a folder
- `/open-claude-session ops --agent implement-ticket --prompt "PROJ-1234"` — runs an agent with a first prompt, and creates the group `ops` if it does not exist
- `/open-claude-session work --resume PROJ-1234` — resumes the latest work-log session for that ticket
- `/open-claude-session work --resume` — lists the work-log sessions and waits for a pick
- `/open-claude-session work --fork PROJ-1234 --name PROJ-1234-pr2 --prompt "start the next PR in the stack"` — forks the session as a new tab in its workspace (rule 1)

## Retry

Say **"retry"** to run the skill again from the start.

When you retry:
1. Do NOT use cached data.
2. Read the group list, the workspace list, and the work log again.
3. Treat it as a new run.
