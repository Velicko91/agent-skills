# Mini design doc template (Phase 2)

Use this template for one incremental change: a new endpoint, a new RPC, a new field, or a change to one flow. Use `template.md` for a new service, a new bounded context, or a change across many services.

**Size:** 1,500-3,000 words, about 4-6 pages. **Diagrams:** 2-3. **Use cases:** 4-5. If the draft is longer, cut before you publish: a mini doc that grows past 3,000 words is a full spec, or it repeats itself.

Write every section below, in this order. If a section does not apply, write one sentence at its place that says why. NEVER leave a placeholder such as "TBD".

## Contents
- Header
- Table of contents
- 0. Terms
- 1. Problem
- 2. Goals & Non-Goals
- 3. Industry Peers
- 4. Background & Current Workflow
- 5. Design
- 6. Use Cases
- 7. Alternatives Considered
- 8. Risks, Observability & Rollout
- 9. Open Questions

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

2-4 terms at most, sorted alphabetically. Add a term only if a reader needs it in more than one section, and the team does not already know it. No code symbols, fields, or endpoints. Use exactly these terms everywhere.

| Term | Definition | Example | Not to be confused with |
|------|------------|---------|-------------------------|

If the change needs no new term, leave the section out.

---

### 1. Problem

One paragraph, 3-5 sentences: what is missing, who it hurts, and why now. Give the one number that shows the size of the problem. No solution.

---

### 2. Goals & Non-Goals

**Goals:** 3-6 numbered, verifiable outcomes of this ticket.

**Non-Goals:** 0-3 bullets.

Rules for both lists:
- Name only work that belongs to this ticket. Never list work of another ticket or a change to another endpoint.
- Never list logic that already exists. Put an existing fact in Section 4.
- List a non-goal only if someone asked for it (the ticket, the user, a stakeholder) and the design does not do it. Never list a thing that nobody asked for and that stays as the current behavior.

---

### 3. Industry Peers

One comparison table and nothing else: no bullets, no summary. This design in the first column, one column for each peer, one row for each dimension that differs. Link each peer's name to the docs page that the facts come from. Write "not documented" in place of a guess. Link a related ticket in a cell where a peer has a feature that another ticket covers.

| Dimension | This design | [Peer A](url) | [Peer B](url) |
|-----------|-------------|---------------|---------------|

If no peer was researched, write one sentence that says so.

---

### 4. Background & Current Workflow

3-6 bullets of facts the design builds on: the existing code, the existing rules (permissions, limits, card types), the data that sizes the change. Every existing behavior goes here, not in the goals.

Then one Mermaid `sequenceDiagram` of the current workflow, with 4-6 participants and at most 10 messages. Mark the pain with a `Note`. Under the diagram, numbered steps that match `autonumber`.

---

### 5. Design

#### 5.1 Overview

One or two paragraphs that a senior engineer can stop after. Then one Mermaid `sequenceDiagram` of the new workflow, with the same participants as Section 4, and a `rect` block or `Note` on what is new. Numbered steps under it.

#### 5.2 Contract

The exact interface, in code blocks:
- The endpoint: method, path, scopes, headers, request, response, and every error with its condition, one line each.
- The internal RPC or event, if the change adds one: every message in full, so a reader can see each field without guessing. Never point to a message that the doc does not show.
- A small table of the possible results when a response has branches (for example success, replay, refusal).

#### 5.3 Logic

The non-obvious rules, as a numbered list in the order the code runs them: idempotency, the order of the checks, what is refused before any write, what an unknown outcome is. Link to a repo rule (for example `AGENTS.md`) in place of restating it; state only what this change adds.

#### 5.4 Data

The new table or the new fields, as a table, or one sentence that says nothing is stored.

---

### 6. Use Cases

4-5 use cases: the happy path, the main variant, one failure of each external dependency, and one rejection that needs explanation. Do not write a use case that only repeats one line of the error list in 5.2.

Write each with a user as the actor, never "the script" or "the client". Use one call on one resource as the example; mention a bulk need once, in the Problem.

```
#### UC-1 - <user> <does what> (happy path)

**Actor:** <the user and the permission or scope they have>
**Precondition:** <the state, with real-looking IDs>

1. The user sends ...
2. ...

**Result:** <the outcome in one line>
```

Add a diagram to one use case only if its flow differs from Section 5.1, for example a retry or a partial failure.

---

### 7. Alternatives Considered

2-4 alternatives. Leave out an alternative that is only "do what a peer does", because Section 3 already shows it.

Start with a table: the chosen design first, one column for each alternative, one row for each dimension that differs. Then 3-4 lines for each alternative:

```
#### Alt A - <name>

**How it works:** <one line>
**Cons:** <the facts that lost>
**Why rejected:** <the reason itself>
```

Smaller rejected choices go in one two-column table (Alternative, Why rejected).

Never cite the internal reasoning as a source: no conversation, drill round, question number, alignment document, or "we decided". Cite only code, docs, tickets, or external pages that a reader can open.

---

### 8. Risks, Observability & Rollout

Bullets only, 8-12 in all:
- **Security:** the access model and the one or two real risks, with the mitigation.
- **Observability:** the metrics and the alerts that are new. No logging rules that the repo already enforces.
- **Rollout:** the flags, the order of the merges, how the change goes live, and the rollback.

---

### 9. Open Questions

| # | Question | Owner | Due |
|---|----------|-------|-----|

Only questions that block or change the work. Each has an owner team.

---

No Appendix. A work breakdown belongs in the tickets, and a deep detail that a reviewer does not need belongs in a link.
