---
name: drill-me
description: Researches how a problem is solved elsewhere, then questions the user round by round until every design decision is settled, writes an alignment document, then hands it to /implement-ticket or /create-notion-tech-spec. Use for "/drill-me <topic>", "drill me on this design", or "what am I not thinking about".
user-invocable: true
allowed-tools: WebSearch, WebFetch, Read, Write, Grep, Glob, Skill
---

# Drill Me

Take a half-formed idea, find how the problem is already solved, then question the user until the design is decided, not assumed. End with an alignment document.

The value is the **grounding**: the questions come from real prior art, so they show trade-offs that the user has not considered.

## Hard rules

- NEVER write the document before the user confirms alignment at the checkpoint.
- NEVER cite a source that you did not fetch and read. If a claim comes only from a search snippet, say so, or drop it.
- Ask 3–6 questions in one message for each round. Never ask one at a time.
- Ground each question in the research. A question that you could ask without reading anything is a wasted question.
- If a real choice exists, name the options and recommend one with a reason, so the user can answer "your option B".
- If an answer contradicts an earlier decision or the prior art, say so at once, and ask which one wins. Silent inconsistency is the failure that this skill prevents.
- NEVER propose an implementation: no file lists, no function signatures, no schemas beyond what a decision needs. This skill settles decisions, not code.
- Record why each decision was made, not only what. In six months the reasoning is the part that nobody remembers.
- Stop when more questions would not change the design, because over-drilling is a failure too.
- Write a phase marker when each phase starts, as `~/.claude/skills/phase-markers/skill.md` says. The ID is the `⟨ph:…⟩` on the phase heading.

## Arguments

| Form | Example | Meaning |
|------|---------|---------|
| Topic | `event sourcing for our ledger` | The thing to drill into |
| Topic with constraints | `rate limiting, must work across 3 services` | The topic and the known constraints |
| Ticket ID in the topic | `PROJ-1234 webhook retries` | The ID goes in the file name |
| `--no-research` | — | Skip the web research, and drill from first principles |
| `--rounds <n>` | `--rounds 2` | The maximum number of rounds. Default: until convergence. |
| `--out <path>` | `--out ./design/ledger.md` | The document path |
| *(empty)* | — | Ask what to drill into, and stop |

Default document path: `./design-alignment-<ID>-<slug>.md` if the topic names a ticket ID, else `./design-alignment-<slug>.md`. The ID in the name lets `/implement-ticket` and `/create-notion-tech-spec` find the document.

Use the defaults with no confirmation.

## Workflow

### Phase 1 — Frame the problem ⟨ph:9f44fa97⟩

Restate the topic and its constraints in one or two sentences. This is a mirror, not a question: if it is wrong, the user corrects it at once, which costs less than a wrong round.

Record the goal of the drill from the words of the user. Phase 7 uses it:

| Goal | The topic says, for example |
|---|---|
| `develop` | "implement", "build", "develop", "add", "fix", "I want to code" |
| `tech-spec` | "tech spec", "spec", "design doc", "RFC", "write up" |
| `unknown` | neither, or both |

Show it in the mirror: `Goal: develop`, so the user can correct it.

### Phase 2 — Research prior art (unless `--no-research`) ⟨ph:79af451e⟩

Find with `WebSearch`, then read with `WebFetch`. Never judge a source from its snippet. Prefer, in this order:

1. Primary specifications: RFCs, standards, official protocol docs
2. Write-ups from teams that shipped it: postmortems, architecture blogs, talks with real numbers
3. Documentation of mature implementations: how they chose, and what they refused to do
4. Critiques and failure reports: "why we moved off X" is often worth more than the original design

Avoid listicles, marketing content, and tutorials that cover only the happy path.

Read 3–6 sources. From each, take the decisions that it had to make (they become the questions), the trade-offs that it names, and what goes wrong, and when. Show a digest:

```
## Prior art

**<Source title>** — <url>
<what it decided, and the trade-off it accepted>

### Where these designs disagree
- <the axis on which they really differ — this is where your decisions live>
```

The disagreements matter more than the consensus. A consensus is a default that you can adopt silently; a disagreement is a decision for the user.

### Phase 3 — Build the decision log ⟨ph:016ff0d2⟩

From the research and the topic, list the design dimensions, for example: scope and non-goals; data model and ownership; consistency, ordering, and failure semantics; interfaces and contracts; scale and performance targets; migration and rollout; operational burden (who runs it, who gets paged); security and access boundaries.

Give each one a status: `OPEN`, `DECIDED`, or `DEFERRED`. The log tracks convergence for the rest of the run.

### Phase 4 — Drill ⟨ph:e4ae3aa3⟩

Repeat until every dimension is `DECIDED` or `DEFERRED`, or `--rounds` is reached. In each round:

1. Ask 3–6 questions in one message. Ground each one in the research:
   > "Kafka pins ordering per partition and accepts hot-partition risk; NATS gives up global ordering for even distribution. Which failure hurts you less?"

   not:
   > "How should ordering work?"
2. Ask only about things that change the design. Do not ask what you can infer, or about names and cosmetics. One question, one decision.
3. Show the second-order effect of each choice, not only the choice.
4. If the user says "you decide", decide, give the reason, and mark it `DECIDED` with a note that it was your call.
5. After the answers, update the log, and show what closed:

```
### Round <n> — decisions

✅ <Dimension>: <what was decided> — <one-line consequence>
⏸️  <Dimension>: deferred — <what would unblock it>

Still open: <list>
```

### Phase 5 — Convergence check ⟨ph:7cce93a2⟩

Before you write, check that the design holds together:
- **Contradictions:** do two decisions conflict?
- **Gaps:** is a dimension still `OPEN` that blocks the start of the work?
- **Unstated assumptions:** did you assume something that the user never confirmed? Ask it now.
- **The disagreement axes of Phase 2:** is each one resolved?

If a check fails, run one more round.

### CHECKPOINT ⟨ph:8ab53cde⟩

Show the alignment summary, and ask: **"Aligned? Say 'write it' to save the document, or keep drilling."** STOP and WAIT.

### Phase 6 — Write the document ⟨ph:28676e4d⟩

```markdown
# <Topic> — Design Alignment

## Problem
<the framing from Phase 1, as finally agreed>

## Decisions
| # | Dimension | Decision | Why | Consequence |
|---|-----------|----------|-----|-------------|

## Explicitly out of scope
- <non-goal> — <why it was ruled out>

## Deferred
| Dimension | Why deferred | What would unblock it |
|-----------|--------------|----------------------|

## Assumptions
- <assumption that was never verified, flagged for someone to check>

## Prior art consulted
- [<title>](<url>) — <what was taken from it, or why it was rejected>

## Open risks
- <what could still go wrong given these decisions>
```

### Phase 7 — Output ⟨ph:f34fffdf⟩

```
✅ Alignment document → <path>

Decisions: <N>   Deferred: <N>   Out of scope: <N>
Sources consulted: <N>
```

Then hand off from the goal of Phase 1. Ask no question for `develop` or `tech-spec`, because the user gave the goal at the start:

| Goal | Do |
|---|---|
| `develop` | Run `/implement-ticket <ID>`. Without an ID, run `/implement-ticket implement the design in <path>`. It finds the document and still waits for plan approval. |
| `tech-spec` | Run `/create-notion-tech-spec` with the document path and the decision table as the input. |
| `unknown` | Ask: "Next: build it with `/implement-ticket`, write a tech spec with `/create-notion-tech-spec`, or stop?" STOP and WAIT. |

## Examples

- `/drill-me event sourcing for the ledger service`
- `/drill-me PROJ-1234 rate limiting across our three public APIs, must survive a region outage`
- `/drill-me --rounds 2 whether to move settlement off the monolith`
- `/drill-me --no-research how we should shard the positions table`

## Retry

If the user says "retry", discard the decision log and every answer. Research again with no cached source, and build the log again.
