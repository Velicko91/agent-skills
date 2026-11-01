# Document templates (`create`)

Use the template of the type from Step 3. Leave out a section only if the source has nothing for it.

## Contents
- Postmortem
- Runbook
- ADR
- Meeting Notes
- Tech Spec / Design Doc
- Onboarding Guide
- Project Brief
- Planning Doc
- Documentation / README / How-To
- General Document

### Postmortem

```
# <Incident Name> — Postmortem

**Date:** <from bullets or today>
**Severity:** <P0/P1/P2 if mentioned>
**Author:** <if mentioned>
**Status:** Draft

## Summary
<2–3 sentences: what happened, impact, resolution>

## Timeline
<Ordered list of events with timestamps if available>

## Root Cause
<Explain the underlying cause, not just the trigger>

## Impact
<Who/what was affected, for how long, measurable impact>

## Contributing Factors
<List of conditions that made the incident possible or worse>

## What Went Well
<Honest positives — detection speed, communication, etc.>

## What Went Wrong
<Honest negatives — gaps in monitoring, process failures, etc.>

## Action Items
| Action | Owner | Due |
|--------|-------|-----|
| ...    | ...   | ... |
```

---

### Runbook

```
# <System/Process Name> — Runbook

**Last Updated:** <date>
**On-call:** <team or rotation if mentioned>

## Overview
<What does this runbook cover? When should you use it?>

## Prerequisites
<Access, tools, or context needed before starting>

## Procedures

### <Procedure Name>
**When:** <trigger or condition>
**Steps:**
1. ...
2. ...

**Expected outcome:** ...
**If this fails:** ...

## Alerts & Thresholds
<Key signals and what they mean>

## Escalation
<Who to contact and how if procedures don't resolve the issue>
```

---

### ADR

```
# ADR-<N>: <Decision Title>

**Date:** <date>
**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-<N>
**Deciders:** <names if mentioned>

## Context
<What is the situation that necessitates this decision?>

## Decision
<What was decided, stated clearly in one paragraph>

## Rationale
<Why this option over the alternatives>

## Alternatives Considered
- **<Option A>** — <why rejected>
- **<Option B>** — <why rejected>

## Consequences
**Positive:** ...
**Negative:** ...
**Risks:** ...
```

---

### Meeting Notes

```
# <Meeting Name> — <Date>

**Attendees:** <names if available>
**Facilitator:** <if mentioned>

## Agenda
<Topics covered, inferred from bullets>

## Discussion

### <Topic 1>
<Expand bullets into prose summary of what was discussed>

### <Topic 2>
...

## Decisions Made
- ...

## Action Items
| Action | Owner | Due |
|--------|-------|-----|
| ...    | ...   | ... |

## Open Questions
- ...
```

---

### Tech Spec / Design Doc

```
# <Feature/System Name> — Design

**Status:** Draft
**Author:** <if mentioned>
**Created:** <date>

## Problem
<What problem does this solve and why now?>

## Goals
- ...

## Non-Goals
- ...

## Design
<High-level approach in 2–4 paragraphs>

## Detailed Design
### <Component or Flow>
<Step-by-step or subsection breakdown>

## Alternatives Considered
- **<Option>** — <why rejected>

## Open Questions
| # | Question | Owner |
|---|----------|-------|
```

---

### Onboarding Guide

```
# <Role/Team> Onboarding Guide

## Welcome
<Context-setting paragraph: what the team does, what the new person will be doing>

## Before Day 1
<Access requests, prereqs, tools to install>

## Week 1

### Day 1
<First-day setup, introductions, immediate tasks>

### Rest of Week 1
<Getting oriented, first small tasks>

## Key Systems & Resources
<Links, repos, dashboards, internal docs>

## Who to Talk To
<Contacts for common questions>

## Common Gotchas
<Pitfalls, non-obvious things, things that trip people up>
```

---

### Project Brief

```
# <Project Name> — Brief

**Status:** Draft
**Owner:** <if mentioned>
**Timeline:** <if mentioned>

## Problem
<What are we solving and why?>

## Objective
<Measurable outcome(s) we're targeting>

## Scope
**In scope:** ...
**Out of scope:** ...

## Approach
<High-level plan or proposed solution>

## Success Metrics
<How will we know this worked?>

## Risks & Dependencies
- ...

## Open Questions
- ...
```

---

### Planning Doc

```
# <Quarter/Period> Planning — <Team/Area>

**Period:** <Q1 2025 / etc.>
**Owner:** <if mentioned>

## Goals
<Top-level outcomes for the period>

## Initiatives

### <Initiative Name>
**Why:** <motivation>
**What:** <scope>
**Success looks like:** <outcome>
**Owner:** <if mentioned>
**Timeline:** <if mentioned>

## Risks
- ...

## Dependencies
- ...
```

---

### Documentation / README / How-To

```
# <Topic> — Guide

## Overview
<What is this? Who is it for?>

## Prerequisites
<What the reader needs before starting>

## <Main Sections>
<Expand each bullet cluster into a section with prose>

## Examples
<If bullets contain examples or commands, format them clearly>

## Troubleshooting
<Common issues if mentioned in bullets>

## Related
<Links or references if present>
```

---

### General Document

```
# <Title>

## Overview
<Context paragraph>

## <Section per bullet cluster>
<Expanded prose>

## Summary
<Closing paragraph or action items if applicable>
```

