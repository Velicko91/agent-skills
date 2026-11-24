---
name: phase-markers
description: The phase marker rule that skills follow, so a token tracker can count tokens per skill phase. Used by other skills.
user-invocable: false
disable-model-invocation: true
---

# Phase markers

A skill that links this file has an ID on each phase heading, for example `### Phase 7 — Tests ⟨ph:5b8e44f1⟩`. A local token tracker reads the markers from the transcript, and counts tokens per phase.

## When a phase starts

Start your first message of the phase with one line:

```
‹phase: <number> <heading name> · <id>›
```

Example: `‹phase: 7 Tests · 5b8e44f1›`.

- Take the number, the name, and the ID from the heading. A heading with no number, for example `CHECKPOINT`, takes the number of the phase before it.
- Write the line also when the turn has only a tool call: put it as text before the call.
- Write it each time the phase starts, also when you go back to an earlier phase or repeat a phase for each step.
- Write only the line. Do not explain it.

## When the run ends

When the skill finishes and nothing waits for the user, end the last message with one line, with the ID of the last phase:

```
‹phase: end · <id>›
```

## When you change a skill

- Never change an ID. A renamed or moved phase keeps its ID, so the tracker sees it as the same phase.
- A new phase gets a new random ID of 8 lowercase hex characters: `python3 -c 'import secrets; print(secrets.token_hex(4))'`.
- Check that each ID is unique in the skill.
