---
name: docs
description: Writes technical documentation for a part of the codebase through interactive exploration — overview, chosen deep-dives, then one polished document in the repo. Use for "/docs", "document the <system>", or "write an onboarding guide for <area>".
allowed-tools: Read, Grep, Glob, Write, Bash(git diff *, git log *, git show *), Bash(date *), AskUserQuestion
user-invocable: true
---

# Technical Documentation Skill

Generate high-quality technical documentation through interactive codebase exploration. Follows FAANG-standard documentation practices (Google developer docs style, AWS well-architected patterns, Meta engineering blog conventions).

## Workflow

### Phase 1: Theme Discovery

**Start by asking the user what they want to document.**

Use `AskUserQuestion` to ask:

```
What area/theme would you like me to document?

Examples:
- A system or subsystem (e.g., "state machine", "payment processing")
- An API or interface (e.g., "gRPC endpoints", "GraphQL mutations")
- A workflow or process (e.g., "transaction lifecycle", "deployment pipeline")
- Architecture overview (e.g., "database schema", "service topology")
- An onboarding guide (e.g., "new developer setup", "how to add a new transaction type")
```

### Phase 2: Automated Overview

Once the theme is known, **explore the codebase autonomously** to build an initial understanding:

1. **Identify relevant files and modules:**
   - Use `Glob` to find files matching the theme
   - Use `Grep` to find references, imports, and usage patterns
   - Use `Read` to understand key files

2. **Map the structure:**
   - Entry points and public interfaces
   - Internal components and their relationships
   - Data flow and dependencies
   - Configuration and environment requirements

3. **Present a structured overview** to the user:

```markdown
## Overview: [Theme]

### Scope
[What this covers]

### Key Components
- **[Component A]** — [one-line description] (`path/to/file.py`)
- **[Component B]** — [one-line description] (`path/to/file.py`)

### Architecture Summary
[2-3 sentences on how components interact]

### Areas I Can Deep-Dive Into
1. [Area 1] — [what this would cover]
2. [Area 2] — [what this would cover]
3. [Area 3] — [what this would cover]
4. [Area 4] — [what this would cover]
```

Then ask: **"Which areas should I focus on? Pick numbers, or tell me something specific you want explored."**

### Phase 3: Interactive Exploration

For each area the user selects:

1. **Deep-dive into the code** — read implementations, trace call chains, understand data structures
2. **Present findings concisely** — use bullet points, code snippets, and diagrams where helpful
3. **Ask follow-up questions** — "Want me to go deeper on X?" or "Should I also cover Y?"

**Keep exploring until the user says to consolidate.** Track all findings internally.

### Phase 4: Consolidation

When the user asks to consolidate (e.g., "write it up", "create the doc", "consolidate"), produce the final document.

#### Document Structure (FAANG Standard)

Follow this template, adapting sections to the content:

```markdown
# [Title]

> [One-line description of what this document covers]

## Overview

[2-3 paragraph executive summary. What is this system/feature, why does it exist,
and what problem does it solve. A senior engineer should understand the scope
after reading this section alone.]

## Architecture

[High-level architecture description. How components fit together.
Include a text-based diagram if the system has multiple interacting parts.]

### Components

#### [Component Name]

**Purpose:** [What it does]
**Location:** `path/to/module/`

[Description of the component, its responsibilities, and key design decisions.]

**Key interfaces:**

| Method/Endpoint | Description | Input | Output |
|----------------|-------------|-------|--------|
| `method_name()` | What it does | Params | Return |

### Data Flow

[Step-by-step description of how data moves through the system.
Use numbered steps for sequential flows.]

1. **[Step name]** — [Description] (`file.py:function`)
2. **[Step name]** — [Description] (`file.py:function`)

## Key Concepts

### [Concept 1]

[Explanation of domain-specific concepts a reader needs to understand.]

### [Concept 2]

[Explanation.]

## Usage

### [Common Use Case 1]

[Step-by-step guide with code examples.]

```python
# Example code
```

### [Common Use Case 2]

[Step-by-step guide.]

## Configuration

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `PARAM_NAME` | What it controls | `value` | Yes/No |

## Error Handling

[How errors are handled, common failure modes, and recovery strategies.]

| Error | Cause | Resolution |
|-------|-------|------------|
| `ErrorType` | When this happens | How to fix |

## Observability

[Logging, metrics, alerts, and monitoring relevant to this system.]

## Dependencies

[External services, libraries, or systems this depends on.]

| Dependency | Purpose | Criticality |
|------------|---------|-------------|
| Service X | What it provides | High/Medium/Low |

## Related Documentation

- [Link to related doc 1]
- [Link to related doc 2]

---

*Last updated: [output of `date -u +%Y-%m-%d`]*
*Generated with [Claude Code](https://claude.com/claude-code)*
```

#### Writing Standards

Follow these FAANG documentation principles:

1. **Audience-first** — State the intended audience at the top. Write for that level.
2. **Progressive disclosure** — Overview first, then details. Reader can stop at any section and have a complete understanding at that depth.
3. **Concrete over abstract** — Use real code examples from the codebase, not pseudocode. Reference actual file paths.
4. **Scannable** — Use tables for structured data, bullet points for lists, bold for key terms. Avoid walls of text.
5. **Self-contained** — The document should make sense without requiring other docs. Define terms inline or in a "Key Concepts" section.
6. **Accurate** — Every code reference, file path, and technical claim must be verified against the actual codebase. Do NOT hallucinate paths or APIs.
7. **Opinionated** — Document the recommended way, not every possible way. Call out anti-patterns.
8. **Maintainable** — Avoid over-specifying things that change often. Reference patterns over specific line numbers.

#### Output

- Ask where to save the file, and suggest `docs/<theme>.md`. If the file exists, say so, and ask before you replace it.
- Write it with the `Write` tool.
- Print a summary of what was documented: the sections, and the files that it references.

## Usage Examples

- `/docs` — Start interactive documentation session
- User says "document the state machine" → explores states/, transitions, produces architecture doc
- User says "write an onboarding guide for new devs" → explores setup, key patterns, produces guide
- User says "document the gRPC API" → explores proto files, service implementations, produces API reference

## Principles

- **Never fabricate** — Only document what exists in the code. If something is unclear, say so.
- **Stay interactive** — Don't dump a massive document without checkpoints. Explore incrementally.
- **Respect scope** — Document what was asked. Don't document the entire codebase when asked about one module.
- **Code as source of truth** — When docs and code disagree, trust the code and note the discrepancy.
