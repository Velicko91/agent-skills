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
- Never cite the internal reasoning as a source: no conversation, drill round, question number, alignment document, or "we decided". The readers did not see it. State the reason itself. Cite only sources a reader can open: code (`<repo>/<path>`), internal docs, tickets, and external pages.

## Phase 1 — Intake and questions

### Step 1 — Parse the input

From everything the user gave, record:
- **What** is built, **why** it is needed, and **who** it affects
- The rough scope: what is in and what is out
- The terms a reader must know to follow the spec
- The use cases: each actor and the outcome it wants
- The industry peers: how each comparable product solves the problem, with the docs URL (from an alignment document, or from research in the conversation)
- The UI parity, for a public API endpoint that mirrors the web app (and any repo in the `uiParity` config of drill-me): each GraphQL operation that the web app sends for the same action, each of its rules (permissions, 2FA or step-up, refusals, side effects) with `<repo>/<path>`, and each divergence with its reason. Take it from the alignment document, or trace the resolver on the default branch of the remote. The endpoint template shows it in 4.1. Ask the user about each divergence that has no reason.
- The connected tech specs: search Notion for specs about the same resource, the same services, and each shared mechanism the design uses, and record each with its URL and how it connects. The endpoint template lists them in References.

### Step 2 — Find the rejected alternatives

Search the conversation and the files the user referenced for options that were discussed and not picked:
1. Earlier messages that compared approaches
2. Design or alignment documents the user pointed to, for example `design-alignment-*.md`, Notion pages, or ticket comments
3. Phrases such as "we could also", "instead of", "we considered", "rejected", "too complex", "decided against"

For each option, record its name, one line on how it works, the reason it lost (in the user's words if possible), and the source. The source is for your own check only: never write it in the document (see Principles).

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

1. Pick the template, and name the pick in one line before you write:

   | The change | Template |
   |---|---|
   | One or more new public endpoints (REST, MCP tool, GraphQL field) | `endpoint-template.md` (1,500-3,000 words) |
   | One other incremental change: a new RPC, field, or a change to one flow | `mini-template.md` (1,500-3,000 words) |
   | A new service, a new bounded context, or a change across many services | `template.md` |

   If the user names a template, use it.
2. Read the picked template and `diagrams.md` in this skill directory.
3. Write every section of the template, in its order. Before you publish, count the words; if a mini doc is over 3,000, cut repeats first.
4. Write in the present tense, as if the design is settled: "the service validates", not "the service will validate".
5. Give the conclusion first, then the reason.
6. Back each abstract statement with a concrete example: values, IDs, timings.
7. Name the subject instead of "it", "this", or "they" when the reference is not clear.
8. Use exactly the term from the Terms table everywhere. Never add a synonym.
9. Keep paragraphs to 4 sentences or fewer.
10. Write no filler ("basically", "in order to", "it is worth noting that") and no section introductions ("In this section, we will discuss…").

## Phase 3 — Publish

Create the page with `mcp__notion__notion-create-pages`:
- Title: `<Feature Name> — Tech Spec`
- Parent: none, so the page is private in the workspace root
- Content: the full document from Phase 2

Then reply with:
1. The link to the page
2. A short summary: the template used and the word count, the sections included, the diagrams, the number of terms and use cases, the alternatives, and each skipped section with the reason
3. "Anything you'd like me to revise before you share it for review? Describe what to adjust and say "retry" to regenerate."

## Examples

- `/create-notion-tech-spec` ← then paste the bullets
- `/create-notion-tech-spec I want to build a rate limiting service for our public API...`

## Retry

If the user says "retry", use no earlier generated content. Read the original input and all answers again, and run Phase 2 again with the new direction.
