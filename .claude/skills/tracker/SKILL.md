---
name: tracker
description: Issue-tracker adapters (tool names, ID patterns, states) that create-ticket, implement-ticket, and solve-ticket read. Used by other skills.
user-invocable: false
disable-model-invocation: true
---

# Tracker

The ticket skills work with any tracker that has an adapter file here. They are not slash commands.

## Select the tracker

1. Read `tracker` in `~/.claude/config.local.json`, for example `"tracker": "linear"`.
2. If `tracker` is absent, use the only tracker that has config (`linear.workspace` or `jira.host`). If both or neither have config, ask the user. STOP and WAIT.
3. Read `<tracker>.md` in this directory. If it does not exist, say that the tracker has no adapter, and stop.

## Adapters

| Tracker | File | Status |
|---|---|---|
| Linear | `linear.md` | In use |
| Jira | `jira.md` | Not written. Write it with the same sections as `linear.md` when it is needed. |

## Sections of an adapter

Each adapter has the same sections, so a ticket skill can use any of them:

- **Config** — the keys in `config.local.json`
- **Identify** — the ID pattern, the URL forms, and the ticket link
- **Tools** — the MCP tool for each operation
- **Create** — the required fields, the defaults, and the field names
- **States** — how to move a ticket to "started", to "review", and to "done"
- **Rules** — tracker rules that each call must follow
