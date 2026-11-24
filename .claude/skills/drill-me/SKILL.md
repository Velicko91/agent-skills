---
name: drill-me
model: opus
description: Researches how a problem is solved in existing repos or on the web, ranks the design questions, asks the most important ones round by round until every design decision is settled, writes an alignment document, then hands it to /implement-ticket or /create-notion-tech-spec. Use for "/drill-me <topic>", "drill me on this design", or "what am I not thinking about".
user-invocable: true
allowed-tools: Bash, WebSearch, WebFetch, Read, Write, Grep, Glob, Skill
---

# Drill Me

Take a half-formed idea, find how the problem is already solved, then question the user until the design is decided, not assumed. End with an alignment document.

The value is the **grounding**: the questions come from real prior art, so they show trade-offs that the user has not considered.

## Hard rules

- NEVER write the document before the user confirms alignment at the checkpoint.
- NEVER cite a source that you did not fetch and read. If a claim comes only from a search snippet, say so, or drop it.
- Ask `perRound` questions in one message for each round. Never ask one at a time.
- Ground each question in the research. A question that you could ask without reading anything is a wasted question.
- If a real choice exists, name the options and give each one the percentage that shows how much you would pick it. The percentages add up to 100. Recommend the highest one with a reason, so the user can answer "your option B".
- ALWAYS list the options from the highest percentage to the lowest, so option A is always the recommendation.
- If the top option of a question has more than `autoPickPercent`, pick it with no question, and mark it `AUTO`. ALWAYS list each `AUTO` pick with its percentage, so the user can reopen it.
- ALWAYS show each option in the option format of Phase 4: how it works, how it looks in code, and the consequence. The user must see the exact result of a pick before the pick, because a consequence found during implementation causes a late disagreement.
- If the work changes code that exists, ALWAYS make at least one option of each question follow a pattern that the code already uses, and cite it as `<repo>/<path>:<line>`. If no code has a pattern for the question, write `No existing pattern`, and give the files that you searched.
- NEVER start the research before the user picks the research topics, because the user knows which repos and pages matter.
- If an answer contradicts an earlier decision or the prior art, say so at once, and ask which one wins. Silent inconsistency is the failure that this skill prevents.
- NEVER write an implementation plan: no file lists, no step lists, no full functions. The code in an option is a sketch that shows only how the option differs. This skill settles decisions, not code.
- Record why each decision was made, not only what. In six months the reasoning is the part that nobody remembers.
- Stop when more questions would not change the design, because over-drilling is a failure too.
- Write a phase marker when each phase starts, as `~/.claude/skills/phase-markers/SKILL.md` says. The ID is the `⟨ph:…⟩` on the phase heading.

## Arguments

| Form | Example | Meaning |
|------|---------|---------|
| Topic | `event sourcing for our ledger` | The thing to drill into |
| Topic with constraints | `rate limiting, must work across 3 services` | The topic and the known constraints |
| Ticket ID in the topic | `PROJ-1234 webhook retries` | The ID goes in the file name |
| `--no-research` | — | Skip the research, and drill from first principles |
| `--rounds <n>` | `--rounds 2` | The maximum number of rounds. Default: until convergence. |
| `--out <path>` | `--out ./design/ledger.md` | The document path |
| *(empty)* | — | Ask what to drill into, and stop |

Default document path: `./design-alignment-<ID>-<slug>.md` if the topic names a ticket ID, else `./design-alignment-<slug>.md`. The ID in the name lets `/implement-ticket` and `/create-notion-tech-spec` find the document.

Use the defaults with no confirmation.

## Local configuration

Read `data.json` in this skill directory. If it is missing, copy `data.example.json` to `data.json`, and use it.

| Key | Default | Use |
|---|---|---|
| `poolSize` | `45` | The number of design questions that Phase 3 finds |
| `askTop` | `20` | The number of the most important questions that Phase 4 asks the user |
| `perRound` | `4` | The number of questions in one message |
| `autoPickPercent` | `95` | If the top option of a question has more than this percentage, pick it with no question |
| `peers` | `{}` | A map from a repo name to the industry peers (comparable products) to research for that repo, each with the url of its API docs, for example `{"public-api": {"Peer Product": "https://docs.example.com/reference/get-resource"}}` |
| `uiParity` | `{}` | A map from a repo name to the UI path that the repo must copy one to one, for example `{"public-api": "the web app's GraphQL operation (the API gateway to the owning service resolver)"}`. See "UI parity" below. |

If a key is missing, use its default.

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

Choose the research mode from the topic:

| Mode | The topic | Source |
|---|---|---|
| `repos` | names a ticket ID, or changes code that already exists | The repos of the organization that owns the current repo |
| `web` | is new, and no repo of the organization solves it yet | Web pages |

#### Step 1 — Propose the research topics

List 5–10 research topics. Give each topic the place to look, the reason, and the percentage that shows how much you would pick it:

```
## Research topics — mode: repos

| # | Topic | Where to look | Why | Pick |
|---|---|---|---|---|
| 1 | PostgreSQL service container in CI | `.github/workflows/*.yml` in the org | Shows the CI pattern that already works | 90% |
| 2 | pytest database fixtures | `conftest.py` in the org | Shows how the tests get a clean database | 80% |
| 3 | How other projects do it (web) | Web pages | Only if no repo solves it | 20% |
```

In `repos` mode, add the web as the last topic, because a repo search can find nothing.

If `peers` has a key for the name of the current repo, add one topic for each peer: "How <peer> does it", with its docs url as the place to look. Start the research at that url, and follow its links to the pages of the topic. Give each one 80% or more, because a peer that shipped it shows the contract that the customers already know. Research these topics with Step 2b. If a peer has no public docs for the topic, say so, and do not guess its design.

If `uiParity` has a key for the name of the current repo, add the topic "How the UI does it" at 100%, first in the list. The user cannot unpick it. See "UI parity" below.

#### UI parity

The repos in `uiParity` copy the UI. The UI behavior is the default for every decision, and a divergence is a decision with its own reason. A design that drifts from the UI gives a customer two answers to the same action.

1. **Trace the UI path.** Find each GraphQL operation that the web app sends for the action, for example one mutation for each toggle state. Follow each one through the API gateway to the resolver in the owning service, and read the resolver on the default branch of the remote.
2. **Record each rule of each operation,** with `<repo>/<path>:<line>`:
   - the permissions, and the permission map they come from
   - the 2FA, step-up challenge or approval, with its action, its details and its feature flag, and what happens when the flag is off
   - the validation and the refusals, with their order
   - the side effects: audit events, notifications, Kafka or Pub/Sub events
   - the cases that the UI blocks in the frontend only
3. **Make the UI behavior option A** of each question that it touches, marked `UI parity`. An option that diverges says `Divergence:` and what the user of the API sees differently.
4. **Ask each divergence as a question.** Never pick a divergence as `AUTO` or as your call, because the user decides each one.

# --- CHECKPOINT ---
STOP and WAIT for the user to pick the topics. Research only the topics that the user picks.

#### Step 2a — Research the repos (`repos` mode)

Get the organization from the current repo, then search its code for each topic:

```bash
gh repo view --json owner -q .owner.login
gh search code '<term>' --owner <org> --limit 30 --json repository,path
```

Prefer a repo that is checked out next to the current repo, because you can read it with no network. Read the files that the search finds, for example the CI workflows, the `conftest.py` files, and the test settings. Never judge a repo from the search hit.

Read 3–6 repos. From each, take the decisions that it had to make, the trade-offs, and the parts that differ from the other repos. Show the digest of Step 2b, with `<repo>/<path>` in place of the url.

Read the code that the work changes, in the current repo, too. Record each pattern that it already uses for the topic, with `<repo>/<path>:<line>`, for example how it retries, validates, maps errors, or tests. Phase 4 builds the existing-code option of each question from this list.

#### Step 2b — Research the web (`web` mode, or a picked web topic)

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

Then write `poolSize` design questions that cover the dimensions. For each question, record:

- The dimension.
- The options, each with its percentage, highest first.
- The questions whose answer can change its percentages (`Depends on`).

If the topic has fewer questions that change the design, write fewer, and say how many. A filler question wastes a round.

Give each question a status: `OPEN`, `DECIDED`, `AUTO`, or `DEFERRED`. The log tracks convergence for the rest of the run.

### Phase 3b — Rank the questions ⟨ph:fb06ce66⟩

Sort the questions from the most important to the least important. Use these keys, in this order:

1. The cost to reverse: a decision that changes a contract, a schema, or stored data costs the most to change later.
2. The reach: the number of other questions that depend on it.
3. The doubt: a lower top percentage means that the answer of the user adds more.

Then give each question its plan:

| Plan | The question |
|---|---|
| `AUTO` | Its top option has more than `autoPickPercent`. Pick it now. |
| `ASK` | One of the first `askTop` questions in rank order that are not `AUTO` |
| `LATER` | All other questions. Phase 4 decides them after the `ASK` answers. |

Show the ranked list, one line for each question:

```
## Questions — 45 found · 20 to ask · 7 auto · 18 later

| Rank | Q | Dimension | Question | Top option | % | Depends on | Plan |
|---|---|---|---|---|---|---|---|
| 1 | Q7 | data model | Who owns the retry state? | Outbox table | 60% | — | ASK |
| 2 | Q3 | contracts | Does the webhook payload carry the attempt number? | Yes | 55% | Q7 | ASK |
| 22 | Q12 | operations | Who gets paged when retries stop? | The owning team | 80% | Q7 | LATER |
| 31 | Q19 | security | Sign the webhook payload? | HMAC, as the other webhooks do | 97% | — | AUTO |
```

# --- CHECKPOINT ---
Ask: "Change the order, move a question to `ASK`, reopen an `AUTO` pick, or say **go**." STOP and WAIT.

### Phase 4 — Drill ⟨ph:e4ae3aa3⟩

Ask the `ASK` questions in rank order, until all of them are answered or `--rounds` is reached. In each round:

1. Ask the next `perRound` `ASK` questions in one message. Ground each one in the research:
   > "Kafka pins ordering per partition and accepts hot-partition risk; NATS gives up global ordering for even distribution. Which failure hurts you less?"

   not:
   > "How should ordering work?"
2. Ask only about things that change the design. Do not ask what you can infer, or about names and cosmetics. One question, one decision.
3. Write each option in the option format below.
4. If the user says "you decide", decide, give the reason, and mark it `DECIDED` with a note that it was your call.
5. After the answers, calculate the percentages of each open question again, from the answers so far. Then:
   - Pick each question whose top option now has more than `autoPickPercent`, and mark it `AUTO`.
   - Drop a question that an answer made obsolete, and say why.
   - If an answer raises a new question that is more important than the next `ASK` question, add it to `ASK`, and say so.
6. Update the log, and show what closed:

```
### Round <n> — decisions

✅ Q7 <Dimension>: <what was decided> — <one-line consequence>
🤖 Q19 <Dimension>: auto-picked <option> (97%) — <the answer that made it clear>
⏸️  Q12 <Dimension>: deferred — <what would unblock it>

Still to ask: <n> · Later: <n>
```

When every `ASK` question is answered, calculate the percentages of the `LATER` questions again. Pick each one that has more than `autoPickPercent` as `AUTO`. Decide each other one with its top option, and mark it `DECIDED` with a note that it was your call.

#### Option format

Write each question and its options like this example:

````
### Q2 — Where does a failed webhook wait for its retry? (failure semantics)

The ledger writes the payment and then calls the webhook. `acme-billing` keeps an outbox table, and `acme-notify` uses a retry topic.

**A — Outbox table, as `acme-billing/app/outbox.py:42` does** · existing pattern · 70%
- How it works: the payment row and the retry row commit in one transaction. A worker reads the retry rows every 5 s. If the service crashes after the commit, the worker still sends the webhook after the restart.
- In code (sketch):
  ```python
  with uow:
      uow.payments.add(payment)
      uow.outbox.add(WebhookDue(payment_id=payment.id, attempt=1))
  ```
- Consequence: a new table and a migration. A retry can wait up to 5 s. The tests use the database fixture that exists, and need no Kafka.

**B — Kafka retry topic, as `acme-notify/consumer.py:88` does** · 30%
- How it works: the handler publishes `WebhookDue` after the commit. If the service crashes between the commit and the publish, the webhook is lost.
- In code (sketch):
  ```python
  uow.commit()
  producer.send("webhook-retry", WebhookDue(payment_id=payment.id, attempt=1))
  ```
- Consequence: no migration, but a new topic and its ACLs. The tests need a Kafka container.

Recommend: A, because B loses a webhook on a crash, and A follows the pattern of this codebase.
````

Each option has these parts:

| Part | Content |
|---|---|
| Title | The option, and the code that it follows: `as <repo>/<path>:<line> does`. Add `existing pattern` if that code is in the repo that the work changes. |
| How it works | One concrete scenario with real values, and the failure case, if there is one. |
| In code | A sketch of 3–15 lines, in the language of the repo, with the names that the code uses. Show only the lines that differ between the options. |
| Consequence | What the pick changes later: a migration, a contract, a test setup, the behavior that a client sees, or the code that must change with it. |

If the topic has no code (`web` mode, or `--no-research`), write the sketch as the call or the config that a user of the design writes.

### Phase 5 — Convergence check ⟨ph:7cce93a2⟩

Before you write, check that the design holds together:
- **Contradictions:** do two decisions conflict?
- **Gaps:** is a question still `OPEN` that blocks the start of the work?
- **Unstated assumptions:** did you assume something that the user never confirmed? Ask it now.
- **The disagreement axes of Phase 2:** is each one resolved?
- **Combined code:** do the sketches of the picked options work together? Write them as one sketch, and look for a conflict, for example two picks that each own the same transaction.
- **UI parity** (if `uiParity` has the repo): write the parity table of Phase 6. Each row is `Match`, or a `Divergence` that the user picked, with its reason. A row with no decision is a gap: ask it.

If a check fails, run one more round.

### CHECKPOINT ⟨ph:8ab53cde⟩

Show the alignment summary, with the combined sketch of the picked options. List each `AUTO` pick and each of your calls, with its percentage, so the user can reopen it. Then ask: **"Aligned? Say 'write it' to save the document, or keep drilling."** STOP and WAIT.

### Phase 6 — Write the document ⟨ph:28676e4d⟩

````markdown
# <Topic> — Design Alignment

## Problem
<the framing from Phase 1, as finally agreed>

## Decisions
| # | Dimension | Decision | How | Follows | Why | Consequence |
|---|-----------|----------|-----|---------|-----|-------------|
<!-- How: asked, auto (<percent>), or my call (<percent>). Follows: <repo>/<path>:<line>, or "new" -->

## Decision details
### <#> — <Dimension>
- **Picked:** <option>. How it works: <the scenario of the option>
- **Sketch:**
  ```<language>
  <the sketch of the picked option>
  ```
- **Rejected:** <option> — <why>

The implementation follows these sketches. A change to a sketch is a new decision, so ask the user first.

## UI parity
<!-- Only if uiParity has the repo. One row for each rule of each UI operation. -->
| Rule | UI (<GraphQL operation>, <repo>/<path>:<line>) | <each entry point, for example REST and MCP> | Match or divergence | Why |
|------|-----|-----|-----|-----|

## Combined sketch
```<language>
<the sketches of the picked options together>
```

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
````

### Phase 7 — Output ⟨ph:f34fffdf⟩

```
✅ Alignment document → <path>

Decisions: <N> (asked <N>, auto <N>, my call <N>)   Deferred: <N>   Out of scope: <N>
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

If the user says "retry", discard the decision log, the ranked questions, and every answer. Research again with no cached source, and build the log again.
