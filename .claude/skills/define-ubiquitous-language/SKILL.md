---
name: define-ubiquitous-language
description: Mines a repository for its domain vocabulary, flags concepts with several names, and writes a short ubiquitous-lng.md glossary at the repo root. Use when onboarding, when naming feels inconsistent, or for "/define-ubiquitous-language" or "build a glossary for this repo".
user-invocable: true
allowed-tools: Read, Grep, Glob, Write, Edit, Bash(git *), Bash(ls *), Bash(find *)
---

# Define Ubiquitous Language

Find the words that this repository uses for its domain, settle one word for each concept, and write them down simply, so tickets, reviews, and conversations mean the same thing.

Ubiquitous language is **business vocabulary**, not implementation vocabulary. If a term makes sense only to someone who reads the code, it does not belong here.

## Hard rules

- NEVER overwrite an existing glossary. Read it, merge into it, and keep its wording unless it is wrong.
- NEVER write the file before the user approves the checkpoint.
- NEVER rename anything in the code. This skill documents and recommends; a rename is separate work.
- Keep each definition to 1–2 sentences in business language, with no implementation detail: no types, no table schemas, no function signatures.
- One entry for each concept, not for each spelling.
- Drop a term that you cannot justify to a non-developer, because a long glossary gets ignored.
- For each collision, cite `file:line` for every variant, and recommend a winner with a reason.
- Edit `CLAUDE.md` only after explicit confirmation, because it is a tracked, shared file.

## Arguments

| Form | Example | Meaning |
|------|---------|---------|
| *(empty)* | — | The current repo |
| Scope hint | `focus on the settlement flow` | Mine only one area |
| `--out <path>` | `--out docs/glossary.md` | Write there instead of `ubiquitous-lng.md` at the repo root |
| `--update` | — | Merge into the existing file. This is also what happens with no flag when the file exists. |
| `--no-claude-md` | — | Do not offer the `CLAUDE.md` pointer |

The glossary holds 15–40 terms: the domain terms that matter, not every noun. Use the defaults with no confirmation.

## Workflow

### Phase 1 — Locate the domain

Run `git rev-parse --show-toplevel`. Read `README.md` and `CLAUDE.md`, because they usually state the purpose of the service in business terms, which is the register of the glossary. If the glossary file exists, read it now; it is the starting point.

### Phase 2 — Mine the vocabulary

Collect candidate terms, in this order of signal quality:

1. **Persistence** — table names, column names, migrations. What the business stores is what the business is about.
2. **Contracts** — proto messages and fields, GraphQL types, OpenAPI schemas, event and topic names. Other teams already use these words with you.
3. **Domain types** — model, entity, and value-object names, and enum members. State machines are rich: `PENDING`, `SETTLED`, `ON_HOLD` are domain terms.
4. **Module and package names** — the directory structure often shows the domain split.
5. **Function and method names** — the verbs: `settle`, `reconcile`, `pledge`.

Search with the `Grep` tool, for example the pattern `^\s*(class|type|enum) ` or `@dataclass` in `*.py` and `*.go`. `Grep` skips the paths in `.gitignore`, such as `node_modules` and `.venv`.

Drop:
- Framework and pattern words: `Handler`, `Service`, `Manager`, `Repository`, `Factory`, `Controller`, `DTO`, `Mixin`, `Base`, `Impl`
- Generic technical nouns: `Config`, `Client`, `Request`, `Response`, `Payload`
- Any word that a developer of another product would also have

Keep a term only if someone who does not write code would say it.

### Phase 3 — Find the collisions

This is the most valuable output:
- **Synonyms** — one concept, several names: `Account` in the DB, `Portfolio` in the API, `Wallet` in the frontend.
- **Homonyms** — one word, several meanings: `Position` as a held asset vs. an index in a list. These cause real bugs.
- **Drift from the business** — the code says `Transaction`, and everyone in Slack and the tracker says `Transfer`. The business word usually wins.
- **Leaked implementation** — a domain concept named after its storage or transport (`KafkaEvent`, `RedisSession`), where a plain domain word exists.

### CHECKPOINT

STOP. Show the proposal:

```
## Proposed ubiquitous language — <repo>

<N> terms, from <where they were mined>

### Terms
- **<Term>** — <one-line definition>

### Collisions to settle          (omit if none)
⚠️  <Concept> is called 3 things:
    `Account`    — db/models.py:34, migrations/003.sql:12
    `Portfolio`  — api/schema.graphql:88
    `Wallet`     — web/src/types.ts:19
    → Recommend **Account** — it is the word in the DB and in the tickets.

### Dropped as non-domain
<short list, so the user can object if something was cut wrongly>

Writing to: <path>            (or: merging into existing <path>)
```

In the same message, ask about each term that you could not define from the code, because a wrong definition is worse than a missing one. Then ask: "Write this glossary, or adjust the terms first?" WAIT.

### Phase 4 — Write the glossary

```markdown
# Ubiquitous Language

The shared vocabulary for this repository. Use these words in code, tickets, PRs,
and conversation. If a term here does not match how you talk about the domain,
change the term — do not keep two.

## Terms

### <Term>
<One or two plain sentences. What it is in business terms, not how it is stored.>
**Also seen as:** `<rejected synonym>` (deprecated — use <Term>)
**Where:** `path/to/model.py`

## Deliberately distinct

Terms that sound alike but are not:
- **<A>** vs **<B>** — <the distinction, in one line>

## Not domain terms
Words that appear often but carry no domain meaning here: `Handler`, `Client`, …
```

`Where:` is a pointer, not a specification. Sort the entries alphabetically in each section, so the file stays easy to diff as it grows.

### Phase 5 — Make it get used

Unless `--no-claude-md`, offer to add this pointer to the repo's `CLAUDE.md` (create the file if it does not exist), and WAIT for the yes:

```markdown
## Domain vocabulary
This repo has a ubiquitous language defined in `ubiquitous-lng.md`. Read it before
discussing or naming anything in the domain, and use those terms in code, commits,
and tickets.
```

A glossary that no session loads is a glossary that no one uses.

### Phase 6 — Output

```
✅ Ubiquitous language → <path>

Terms: <N>        Collisions flagged: <N>
CLAUDE.md: pointer added | skipped
```

Restate the collisions: they are follow-up work, and writing the file renames nothing. If a rename is worth planning, suggest `/create-ticket`.

## Examples

- `/define-ubiquitous-language`
- `/define-ubiquitous-language focus on the settlement and reconciliation flow`
- `/define-ubiquitous-language --out docs/glossary.md --no-claude-md`

## Retry

If the user says "retry", discard the mined terms and every proposed definition. Read the existing glossary again, and mine the code again.
