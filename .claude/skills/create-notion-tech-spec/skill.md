---
name: create-notion-tech-spec
description: Turns the user's bullets into a FAANG-style tech spec — terms table, Mermaid workflows, worked use cases, rejected alternatives — after one round of questions, and publishes it as a private Notion page. Use for "write a tech spec" or "/create-notion-tech-spec".
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash(date *), mcp__notion__notion-create-pages
---

# Create Notion Tech Spec

Turn rough bullets into a tech spec for engineers, and publish it as a private Notion page.

Requires an active Notion MCP connection. If it is not active, tell the user to run `/mcp`.

## Principles

- Every sentence must earn its place. The readers are engineers, so skip the basics.
- Give the reason for each decision.
- Define the few concepts the design rests on in a Terms table at the top, and nothing else.
- Give each workflow, use case, and alternative a concrete, numbered walk-through.
- Record the alternatives from the conversation, with the reason that each one lost.
- Ask before you assume. Missing context makes a bad spec.

## Phase 1 — Intake and questions

### Step 1 — Parse the input

From everything the user gave, record:
- **What** is built, **why** it is needed, and **who** it affects
- The rough scope: what is in and what is out
- The terms a reader must know to follow the spec
- The use cases: each actor and the outcome it wants

### Step 2 — Find the rejected alternatives

Search the conversation and the files the user referenced for options that were discussed and not picked:
1. Earlier messages that compared approaches
2. Design or alignment documents the user pointed to, for example `design-alignment-*.md`, Notion pages, or ticket comments
3. Phrases such as "we could also", "instead of", "we considered", "rejected", "too complex", "decided against"

For each option, record its name, one line on how it works, the reason it lost (in the user's words if possible), and the source.

### Step 3 — Find the gaps

Must know before writing:
- The problem, in 1–2 sentences
- Measurable success
- What is out of scope
- The services and systems involved
- The scale: users, QPS, data volume
- Hard constraints: deadline, tech stack, team size

Should know, if it applies:
- The reviewer or approver
- Security or privacy concerns
- Existing APIs or data models that change
- The migration or rollout strategy
- The alternatives from Step 2, and any others the user weighed
- Terms that are ambiguous or mean different things to different teams
- The current workflow, step by step, with its actors

### Step 4 — Ask

STOP. Do not write the document yet.

Send one message with all questions, grouped by theme. Explain a question only if its reason is not clear. Example:

```
Before I write the spec, I need a few clarifications:

**Scope**
- What's the explicit non-goal here — are we ruling out X?

**Scale & Constraints**
- Rough expected traffic? (even a ballpark: hundreds/day vs millions/day)

**Technical**
- Is there an existing service this extends, or is this greenfield?

**Alternatives**
- From our discussion I found: (1) polling the vendor, (2) a nightly batch. Rejected because [reason]. Correct? Any others?

**Terms**
- Does "account" mean the customer account or the ledger account here?

**Ownership**
- Who reviews and approves this? (for the header)
```

WAIT for the answers. If a critical gap stays open, ask one focused follow-up. Then go to Phase 2.

## Phase 2 — Write the document

1. Read `template.md` and `diagrams.md` in this skill directory.
2. Write every section of the template, in its order.
3. Write in the present tense, as if the design is settled: "the service validates", not "the service will validate".
4. Give the conclusion first, then the reason.
5. Back each abstract statement with a concrete example: values, IDs, timings.
6. Name the subject instead of "it", "this", or "they" when the reference is not clear.
7. Use exactly the term from the Terms table everywhere. Never add a synonym.
8. Keep paragraphs to 4 sentences or fewer.
9. Write no filler ("basically", "in order to", "it is worth noting that") and no section introductions ("In this section, we will discuss…").

## Phase 3 — Publish

Create the page with `mcp__notion__notion-create-pages`:
- Title: `<Feature Name> — Tech Spec`
- Parent: none, so the page is private in the workspace root
- Content: the full document from Phase 2

Then reply with:
1. The link to the page
2. A short summary: the sections included, the diagrams, the number of terms and use cases, the alternatives and their sources, and each skipped section with the reason
3. "Anything you'd like me to revise before you share it for review? Describe what to adjust and say "retry" to regenerate."

## Examples

- `/create-notion-tech-spec` ← then paste the bullets
- `/create-notion-tech-spec I want to build a rate limiting service for our public API...`

## Retry

If the user says "retry", use no earlier generated content. Read the original input and all answers again, and run Phase 2 again with the new direction.
