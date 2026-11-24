---
name: create-agent
description: Scaffolds a Claude Code subagent in .claude/agents/ — gathers requirements, picks least-privilege tools and a model, writes the system prompt, and saves the .md file after approval. Use for "/create-agent <name>", "create a subagent that …", or "make me an agent for X".
user-invocable: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(ls *), Bash(mkdir *), Bash(ln *), Bash(test *)
---

# Create Agent

Scaffold a Claude Code **subagent**: a separate Claude instance with its own context, tools, model, and system prompt, started with the `Agent` tool. This is the counterpart of `/create-skill`.

## Hard rules

- NEVER write the file before the user approves the checkpoint.
- ALWAYS ask whether delegation is proactive. Never assume it, because a proactive agent with side effects starts on its own.
- NEVER set `permissionMode: bypassPermissions` unless the user explicitly asks for it, because it disables all permission checks.
- Grant the fewest tools that the job needs. Omitting `tools` inherits every tool, so do that only on purpose.
- If the job needs user interaction, it must be a skill. Redirect to `/create-skill`.
- One agent, one responsibility. If the description needs "and", consider two agents.
- NEVER overwrite an existing agent silently. Show its content, and ask.
- Ask all questions in one message. If you are undecided between two designs, show the options, and let the user pick.

## Paths

- Source: `$CLAUDE_CONFIG_REPO/.claude/agents/<name>.md`. With `--project`: `.claude/agents/<name>.md` of the current repo.
- `~/.claude/agents` is a symlink to the whole source directory, so writing the file is enough. Do not create a symlink for each file.
- An agent is one `.md` file, never a directory.

## Arguments

| Form | Example | Meaning |
|---|---|---|
| Name + purpose | `code-reviewer reviews code for security issues` | Name and purpose |
| Name only | `db-migrator` | Ask for the rest |
| Free text | `an agent that hunts flaky tests` | Infer a name, and confirm it |
| *(empty)* | — | Ask for everything |
| `--project` | `--project code-reviewer` | Write to the current repo |

## Agent or skill — decide first

Build an **agent** if the work is self-contained, produces verbose output that should stay out of the main context, needs enforced tool limits, or can run in parallel.

Build a **skill** if the work needs back-and-forth with the user, shares context across phases, or must stop for approval. **A subagent cannot ask the user anything**: `AskUserQuestion`, `EndConversation`, `ScheduleWakeup`, `Workflow`, `TaskOutput`, and the plan-mode tools are not available to it.

## Workflow

### Phase 1 — Requirements

Parse `$ARGUMENTS`. Then ask, in one message, only what you cannot infer:

1. **Job** — the one specific task
2. **Trigger** — when to delegate to it, and what the user is doing then
3. **Delegation** — proactive, or only when named? Always ask.
4. **Tools** — read-only research, or edits, commands, MCP tools?
5. **Output** — a report, a findings list, or a structured result?

If the user gave enough detail, go to the checkpoint.

### Phase 2 — Check for collisions

Run `ls ~/.claude/agents/` (and `ls .claude/agents/` with `--project`). The `name` must be unique. If it collides, show the existing agent, and ask: a new name, or overwrite?

### Phase 3 — Design

**Frontmatter.** Start minimal:

```yaml
---
name: <lowercase-and-hyphens-only>
description: <what it does + when to delegate>
tools: <comma-separated, least privilege>
model: <from the table below>
---
```

**Model.** A subagent runs on its own `model:`, so choose it from the work (the same table as `~/.claude/skills/create-skill/authoring-rules.md`):

| Work | `model` |
|---|---|
| Mechanical: run commands, fetch, post, format | `haiku` |
| Moderate: queries, summaries, test updates | `sonnet` |
| Judgement: design, review, investigation | `inherit` |

If you choose `haiku`, write explicit steps, because Haiku needs more detail than Opus.

Add another field only when the job needs it, and give the reason at the checkpoint:

| Field | Values | Add when |
|---|---|---|
| `disallowedTools` | comma-separated; `mcp__*` denies all MCP | A denylist is simpler than an allowlist |
| `effort` | `low` `medium` `high` `xhigh` `max` | The job is trivially mechanical or very hard |
| `maxTurns` | integer | A runaway needs a hard limit |
| `isolation` | `worktree` | It edits files and can run in parallel with others |
| `color` | `red` `blue` `green` `yellow` `purple` `orange` `pink` `cyan` | The user wants a visual marker |
| `background` | boolean | It must always, or never, run in the background |
| `skills` | comma-separated | It must preload specific skills |
| `memory` | `user` `project` `local` | It needs persistent memory |
| `permissionMode` | `default` `acceptEdits` `plan` `auto` `dontAsk` | It needs a non-default permission mode |

**Field rules:**
- `name`: lowercase letters and hyphens only.
- `tools`: a comma-separated **string**, not a YAML list. Bash cannot be scoped: write `Bash`, not `Bash(git *)`. To limit Bash, use `disallowedTools` or a hook. MCP: `mcp__<server>` or `mcp__<server>__*`. To let it start other agents: `Agent(worker, researcher)`; leave out `Agent` to deny it.
- `model`: `inherit`, `sonnet`, `opus`, `haiku`, `fable`, or a full model ID.

**Description.** Claude reads it to decide whether to delegate, and every session loads it. Make it specific, with the trigger words, in 300 characters or fewer.
- Proactive: include "Use proactively" or "Use immediately after …", for example: `Expert code review specialist. Proactively reviews code for quality, security, and maintainability. Use immediately after writing or modifying code.`
- Explicit only: state the trigger with no proactive wording, for example: `Runs database migrations and verifies schema. Use when the user explicitly asks to migrate.`

**Body.** The body is the whole system prompt of the agent. It does not get the Claude Code system prompt, so write everything that it needs here, in about 10–40 lines:

```markdown
You are a <role>, specializing in <domain>.

When invoked:
1. <first concrete step>
2. <second step>
3. <third step>

<Checklist, criteria, or domain reference as bullets>

Report your findings as:
- **Critical** — <definition>
- **Warnings** — <definition>
- **Suggestions** — <definition>

For each finding include the file:line and a concrete fix.
```

- Start with `You are a <role>`.
- Give a numbered workflow, not general guidance.
- State the output format exactly, because the final message of the agent is its return value.
- Write the domain criteria as bullets.
- Do not tell it to ask the user anything, and do not repeat general Claude Code behaviour.

### CHECKPOINT

STOP. Show the full draft:

```
📄 Agent: <name>
📁 Path: $CLAUDE_CONFIG_REPO/.claude/agents/<name>.md
🔔 Delegation: proactive | explicit-only
🔧 Tools: <list>  (least privilege: <one-line reason>)
🧠 Model: <model>  (<work type>)
<each other non-default field + why>

<full file content, frontmatter + body>
```

Ask: "Write this agent, or adjust anything first?" WAIT.

### Phase 4 — Write

1. Write the file to the path of the checkpoint.
2. If `~/.claude/agents` is missing, create the directory symlink once: `ln -s $CLAUDE_CONFIG_REPO/.claude/agents ~/.claude/agents`.
3. Check with `ls -la ~/.claude/agents/<name>.md`.

### Phase 5 — Output

```
✅ Created agent: <name>

📁 Source:  $CLAUDE_CONFIG_REPO/.claude/agents/<name>.md
🔗 Global:  ~/.claude/agents/ (directory symlink)
🔔 Delegation: <proactive | explicit-only>

Invoke with: "use the <name> agent to ..."
<if proactive: "Claude will also delegate to it automatically when <trigger>.">
```

Then offer: "Tell me what to change, or say **retry** to redesign from scratch."

## Examples

- `/create-agent code-reviewer reviews changed code for bugs and security issues`
- `/create-agent flaky-test-hunter finds and diagnoses flaky tests, read-only`
- `/create-agent migration-writer --project`
- `/create-agent` ← asks for everything

## Retry

If the user says "retry", reuse no frontmatter, body, or tool choice. Check for collisions again, ask the delegation question again, and treat it as a new run.
