# New endpoint design doc template (Phase 2)

Use this template when the change adds one or more public API endpoints (REST, MCP tool, GraphQL field) for a client. It is a mini design doc: the same limits and rules as `mini-template.md`, but the design shows the endpoint as the client sees it first, and the backend work comes later.

**Size:** 1,500-3,000 words, about 4-6 pages. **Diagrams:** 2-3. **Use cases:** 4-5. If the draft is longer, cut repeats before you publish.

Write every section below, in this order. If a section does not apply, write one sentence at its place that says why. NEVER leave a placeholder such as "TBD".

## Contents
- Header
- Table of contents
- 0. Terms
- 1. Problem
- 2. Goals & Non-Goals
- 3. Industry Peers
- 4. Background & Current Workflow
- 5. API Design
- 6. Use Cases
- 7. Alternatives Considered
- 8. Backend Work
- 9. Risks, Observability & Rollout
- 10. Open Questions
- 11. References

## Header
```
**Status:** Draft | In Review | Approved | Implemented
**Author:** [from user input, or leave blank]
**Reviewers:** [from user input, or leave blank]
**Created:** [output of `date -u +%Y-%m-%d`]
**Target:** [deadline from user input, or leave out the line]
**Ticket:** [link]
```

## Table of contents

Put a Notion table of contents block directly under the header:

```
<table-of-contents />
```

---

### 0. Terms

2-4 terms at most, sorted alphabetically. Add a term only if a reader needs it in more than one section, and the team does not already know it. No code symbols, fields, or endpoints. Use exactly these terms everywhere. If the change needs no new term, leave the section out.

| Term | Definition | Example | Not to be confused with |
|------|------------|---------|-------------------------|

---

### 1. Problem

One paragraph, 3-5 sentences: what the client cannot do today, who it hurts, and why now. Give the one number that shows the size of the problem. No solution.

---

### 2. Goals & Non-Goals

**Goals:** 3-6 numbered, verifiable outcomes, written from the client's side ("a user terminates a card with one call and reads `canceled` back").

**Non-Goals:** 0-3 bullets.

Rules for both lists:
- Name only work that belongs to this ticket. Never list work of another ticket or a change to another endpoint.
- Never list logic that already exists. Put an existing fact in Section 4.
- List a non-goal only if someone asked for it (the ticket, the user, a stakeholder) and the design does not do it. Never list a thing that nobody asked for and that stays as the current behavior.

---

### 3. Industry Peers

One comparison table and nothing else: no bullets, no summary. This design in the first column, one column for each peer, one row for each dimension that differs (endpoint, request, response, status values, repeat behavior, idempotency, scope, bulk). Link each peer's name to the docs page that the facts come from. Write "not documented" in place of a guess. Link a related ticket in a cell where a peer has a feature that another ticket covers.

| Dimension | This design | [Peer A](url) | [Peer B](url) |
|-----------|-------------|---------------|---------------|

If no peer was researched, write one sentence that says so.

---

### 4. Background & Current Workflow

3-6 bullets of facts the design builds on: how a user does this today (web app, another endpoint), the existing rules (permissions, limits, resource types), the data that sizes the change. Every existing behavior goes here, not in the goals.

Then one Mermaid `sequenceDiagram` of how a user does it today, with 3-5 participants and at most 8 messages. Mark the pain with a `Note`. Numbered steps under it.

#### 4.1 UI parity

Write this subsection when the web app already does the action, which is always the case for a public API that mirrors the web app. The endpoint copies the UI one to one, so a reviewer must see each rule side by side, and each divergence with its reason.

Start with a yellow warning callout that lists each divergence in one line, or says "No divergence from the UI." Then one table, with one row for each rule of each UI operation (for example, one operation for each toggle state):

| Rule | UI: `<GraphQL operation>` | REST | MCP | Match |
|---|---|---|---|---|
| Permission | `delete_*_cards` (`<repo>/<path>`) | Same | Same | Match |
| Step-up challenge | `virtual_card_reissued`, always | None | Approval gate, `virtual_card_reissued` | REST: **Divergence** - <reason> |

Cover the permissions, the 2FA, step-up challenge or approval (with its action and its feature flag), the refusals, the side effects (audit events, notifications, events), and the cases that the UI blocks in the frontend only. Cite the UI code as `<repo>/<path>`. Never mark a row `Match` from memory: read the resolver.

---

### 5. API Design

How the endpoint looks and feels to the client. Write this section so that a client developer could use the endpoint from it alone. No internal services, RPCs, or tables here; those go in Section 8.

#### 5.1 Endpoint at a glance

One table:

| Property | Value |
|---|---|
| Method and path | `POST /v1/cards/{card_id}/terminate` |
| Scope | `cards:terminate:write` |
| Required headers | `Idempotency-Key` |
| Sync or async | Synchronous; the result is final when the call returns |
| Reversible | No |
| MCP tool | `terminateCard`, behind approval, off until release |
| Release | Hidden behind the scope release flag |

#### 5.2 Request and response

One code block for each: the request body with every field, its type, its default, and one comment line. The response with every field. Use real-looking values, never `string` or `number`.

Then one `curl` example of the main call and its response, as a client would paste it.

#### 5.3 Errors

One table, one row for each error the client can get: status, problem code, when it happens, and what the client should do next. The "what to do next" column is the point of the table.

| Status | Code | When | Client does |
|---|---|---|---|
| 409 | `card_closed` | The card is already terminated | Nothing; read the card with `getCard` |

#### 5.4 Repeats, retries and read-back

From the client's side only: what a repeat with the same key returns, what a timeout means and how to retry it, and how to read the result back (which endpoint, which field, how soon). One short numbered example.

#### 5.5 MCP tool (if any)

The tool name, its input, what the agent sees (for example an approval link), and when it is enabled. One example of a call and its result.

#### 5.6 Docs

Where the guide text goes, and the one paragraph a client reads first. Name the docs gate if the endpoint ships hidden.

---

### 6. Use Cases

4-5 use cases from the client's side: the happy path, the main variant, one retry or timeout, and one rejection that needs explanation. Do not write a use case that only repeats one row of the error table in 5.3.

Write each with a user as the actor, never "the script" or "the client". Use one call on one resource as the example; mention a bulk need once, in the Problem.

```
#### UC-1 - <user> <does what> (happy path)

**Actor:** <the user and the permission or scope they have>
**Precondition:** <the state, with real-looking IDs>

1. The user sends ...
2. The user gets ...

**Result:** <the outcome in one line>
```

---

### 7. Alternatives Considered

2-4 alternatives about the API shape (path, verb, request, response, semantics). Leave out an alternative that is only "do what a peer does", because Section 3 already shows it.

Start with a table: the chosen design first, one column for each alternative, one row for each dimension that differs. Then 3-4 lines for each alternative:

```
#### Alt A - <name>

**How it works:** <one line>
**Cons:** <the facts that lost>
**Why rejected:** <the reason itself>
```

Smaller rejected choices go in one two-column table (Alternative, Why rejected). Backend alternatives (which RPC, where a check runs) go in Section 8, next to the work they change.

Never cite the internal reasoning as a source: no conversation, drill round, question number, alignment document, or "we decided". Cite only code, docs, tickets, or external pages that a reader can open.

---

### 8. Backend Work

What each component needs so that the endpoint in Section 5 works. Say what is needed and why, not how to code it: no file lists, no step lists.

#### 8.1 Flow

One Mermaid `sequenceDiagram` of the new request through the services, with at most 12 messages. Numbered steps under it. Add one more diagram only for a partial failure or a retry that crosses services.

#### 8.2 Work by component

One subsection for each component that changes (for example the API service, the owning service, the schema repository, the permissions service). For each one:
- **Needs:** the new RPC, event, field, check, or flag, with the contract in full when the doc adds one (every message, so no field is a guess).
- **Rules:** the order of the checks, idempotency, what is refused before any write, what an unknown outcome is. Link a repo rule (for example `AGENTS.md`) in place of restating it.
- **Owner:** the team that writes it and the team that reviews it.

#### 8.3 Data

The new table or the new fields, as a table, or one sentence that says nothing is stored.

#### 8.4 Backend alternatives

The rejected backend choices, in one two-column table (Alternative, Why rejected).

---

### 9. Risks, Observability & Rollout

Bullets only, 8-12 in all:
- **Security:** the access model and the one or two real risks, with the mitigation.
- **Observability:** the metrics and the alerts that are new. No logging rules that the repo already enforces.
- **Rollout:** the flags, the order of the merges, how the endpoint goes live, and the rollback.

---

### 10. Open Questions

| # | Question | Owner | Due |
|---|----------|-------|-----|

Only questions that block or change the work. Each has an owner team.

---

### 11. References

The other tech specs and design docs that this work depends on or changes, one bullet each: a Notion mention or link, and one line on how it connects.

- <mention of the spec> - <how it connects, for example "defines the approval gate that the MCP tool uses">

Find them in Phase 1: search Notion for specs about the same resource, the same service, and every shared mechanism the design uses (approval gate, scopes, idempotency, audit trail). Add the related tickets that are not part of this work (for example a sibling endpoint in the same project). Never list the conversation or an alignment document.

If nothing is connected, write one sentence that says so.
