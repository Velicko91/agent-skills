---
name: plan
description: Builds a checkbox task plan from a ticket, an optional Notion document, and extra comments, grounded in the real code, and writes it after confirmation. Use for "/plan PROJ-1234", "/plan PROJ-1234 <notion-url> also handle the migration", or "/plan <description>".
user-invocable: true
allowed-tools: Read, Write, Grep, Glob, WebFetch, mcp__linear__get_issue, mcp__notion__notion-fetch, mcp__notion__notion-search
---

# Plan

Turn a ticket, an optional Notion document, and free comments into a **markdown list of every task to do**. The output is a task plan, not a design document: checkbox bullets only.

## Hard rules

- Write a bulleted task list, NEVER prose: no design discussion, no paragraphs of reasons.
- One bullet is one task that can be done and checked.
- NEVER write the file before the user approves the checkpoint.
- Ask all questions in one message.
- NEVER invent scope. Each task traces to the ticket, the document, or the comments. If something is not clear, ask at the checkpoint.
- Ground each task in the real code: name the files that it touches, and never assume code that does not exist.

## Tracker

Follow "Select the tracker" in `~/.claude/skills/tracker/SKILL.md`, and read the adapter. Phase 1 uses its Identify section, and Phase 2 its Fetch tool.

## Arguments

`$ARGUMENTS`, in any order:

| Form | Example | Meaning |
|------|---------|---------|
| Ticket ID or URL | `PROJ-1234` | The ticket to plan from |
| Notion URL | `https://notion.so/...` | A supporting spec or context document |
| `--out <path>` | `--out ./docs/plan.md` | The output file |
| Anything else | `also cover the backfill script` | Extra requirements |

At least one of a ticket, a Notion URL, or comments is required. If `$ARGUMENTS` is empty, ask, in one message, for a ticket, a Notion document, or a description.

The default file is `./plan-<ID>.md` with a ticket, else `./plan.md`. The ID in the name lets `/implement-ticket` find the plan. Group the tasks under `##` headings only if there are clearly distinct areas of work. Use the defaults with no confirmation.

## Workflow

### Phase 1 — Parse the arguments

Take the ticket ID (adapter: Identify), any `notion.so` URL, `--out`, and the remaining text as comments.

### Phase 2 — Gather the sources

Fetch each source that was given. Skip the others silently.

- **Ticket:** fetch it with the adapter, with relations, so sub-issues and blockers are included. Take the title, description, acceptance criteria, sub-issues, labels, and state.
- **Notion document:** `mcp__notion__notion-fetch` on the URL. Take the headings, requirements, checklists, and task lists.
- **Comments:** extra requirements that the ticket or the document may not cover.

If a source that was given cannot be fetched, report the error, and ask whether to continue with the others.

### Phase 3 — Investigate the code

With `Grep`, `Glob`, and `Read`, find:
- The entry points that the work touches: resolvers, endpoints, handlers, services named in the sources
- The models, schemas, types, and config that must change
- The existing tests of that code, and the patterns for new tests
- Related code that the work should follow (naming, structure, conventions)
- Anything that the sources assume and the repo does not have (a missing dependency, an absent migration)

### Phase 4 — List the tasks

- Make each task specific: "Add `page_number` param to positions resolver", not "improve the resolver".
- Name the real file or area of each task.
- Add each acceptance criterion, sub-issue, and Notion checklist item as a task.
- Add the comments as tasks where they add scope.
- Order the tasks for execution: setup → implementation → tests → docs and cleanup.

### CHECKPOINT

STOP. Show:

```
📋 Plan sources
- Ticket: PROJ-1234 — <title>             (or "none")
- Notion: <doc title>                     (or "none")
- Comments: <one-line paraphrase>         (or "none")
- Code investigated: <key files/areas>    (or "none")

Proposed tasks (<N>):
- [ ] <task 1>
- [ ] <task 2>

Output → <path>     (exists — will be replaced)   ← only if the file exists
```

In the same message, ask about conflicts between the sources and unclear scope. Then ask: "Write this plan, or adjust anything first?" WAIT. If the user asks for changes, update the list, show it again, and wait again.

### Phase 5 — Write the plan

```markdown
# Plan — <ticket title, or short description>

**Sources:** PROJ-1234 · <Notion doc title>        (omit parts that don't apply)

## <Section name, if grouping>
- [ ] <task>
- [ ] <task>
```

Write one imperative line for each task, and keep the source line, so the plan traces back to the ticket and the document.

### Phase 6 — Confirm

```
✅ Plan written → <path>
   <N> tasks across <M> sections

<full markdown content of the file>

Want to tweak any tasks?
```

Print the full plan, so the user sees it without opening the file.

## Examples

- `/plan PROJ-1234`
- `/plan PROJ-1234 https://www.notion.so/<workspace>/Spec-abc123 also add a Kafka consumer and backfill existing rows`
- `/plan PROJ-1234 --out ./docs/plan.md`
- `/plan add rate limiting to the GQL API, need config + middleware + tests` ← no ticket
- `/plan` ← asks for a ticket, a Notion document, or a description

## Retry

If the user says "retry", reuse no ticket data, Notion content, or draft. Fetch the sources again, and treat it as a new run.
