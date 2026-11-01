---
name: review-techspec
description: Reviews a Notion tech spec as an expert engineer — correctness, completeness, security, operations, dependencies — and adds each finding as a Notion comment on the exact text, without changing the document. Use for "/review-techspec <notion-url>" or "review this tech spec".
user-invocable: true
allowed-tools: Read, Grep, Glob, mcp__notion__notion-fetch, mcp__notion__notion-get-comments, mcp__notion__notion-create-comment
---

# Review Tech Spec

Review a tech spec in Notion as an expert engineer. Find issues, mistakes, gaps, and improvements, and add each one as a comment. For wording and structure, use `/improve-techspec` instead.

Requires the Notion MCP connection. If it is not active, tell the user to run `/mcp`.

## Hard rules

- NEVER change the document. Add comments only.
- Start every comment with `Claude-review: [<Category>] - `.
- Be specific: attach each comment to the exact text that it is about, and offer a solution, not only criticism.
- Review the technical substance. Do not comment on style or formatting.
- Do not suggest scope creep, and do not assume bad intent.
- Do not post a finding again that an earlier `Claude-review:` comment already makes.

## Comment categories

| Category | Use for |
|---|---|
| `[Issue]` | A problem that needs a fix |
| `[Question]` | A point that needs clarification |
| `[Suggestion]` | An improvement |
| `[Missing]` | Required information that is not there |
| `[Risk]` | A possible problem or concern |

## Workflow

### Step 1 — Fetch the document

Fetch the URL with `mcp__notion__notion-fetch`. If the result is truncated, or lists `unknown_block_ids`, fetch those blocks too. Then read the existing comments with `mcp__notion__notion-get-comments`, and note the `Claude-review:` ones.

### Step 2 — Review

Review the document through each lens:

- **Technical correctness:** are the architecture and the technology choices sound? Scalability, edge cases, failure modes?
- **Security and privacy:** authentication and authorization, data privacy, input validation, sensitive data?
- **Operational readiness:** monitoring and alerting, rollback, migration plan, performance?
- **Clarity:** is the problem clear? Could another engineer implement from it? Are the assumptions and trade-offs explicit?
- **Dependencies and integration:** are all dependencies listed? Impact on upstream and downstream services? Clear API contracts? Breaking changes?

Check the sections against `~/.claude/skills/improve-techspec/tech-spec-template.md`, with these levels:

| Level | Sections | If absent |
|---|---|---|
| Must have | Problem statement, scope (in/out), system architecture, data model (if applicable), API or interface definitions, risk assessment | `[Issue]` |
| Should have | Glossary for domain terms, sequence diagrams for complex flows, rollback or migration plan, monitoring, alternatives considered | `[Missing]` |
| Nice to have | Performance benchmarks, cost estimates, timeline, testing strategy | `[Suggestion]`, only if it would help |

### Step 3 — Add the comments

For each finding, call `mcp__notion__notion-create-comment` with `page_id` and `markdown`:

- Attach it to the text that it is about with `selection_with_ellipsis`: about 10 characters from each end of a unique snippet, joined by `...`, for example `"The checkout...PaymentService"`. If no snippet matches, retry with another snippet. Use a page-level comment (`page_id` only) only for a finding about the whole document, for example a missing section.
- Write inline text only: bold, italic, code, and links. A comment shows lists, headings, and code blocks as plain text.

Examples:

```
Claude-review: [Issue] - The synchronous call to PaymentService during checkout is a single point of failure. Consider async processing with a queue.
Claude-review: [Question] - What happens if the external pricing API is unavailable? Is there a fallback or a cached price?
Claude-review: [Suggestion] - Add a circuit breaker for the third-party inventory service, to prevent cascade failures.
Claude-review: [Missing] - No data retention policy. How long is user activity data stored? This affects GDPR compliance.
Claude-review: [Risk] - The schema has no index on the frequently queried user_id and created_at. This can be slow at scale.
```

### Step 4 — Report

1. The number of comments added, and how many earlier findings were skipped
2. The count for each category
3. The 3 most critical items
4. The overall assessment: Ready, Needs Work, or Major Revision

Then offer: "Say **retry** for a fresh review after changes."

## Retry

If the user says "retry", reuse no earlier result. Fetch the document and its comments again, and run the workflow from Step 1. Existing `Claude-review:` comments are not posted again.

Usage: `/review-techspec https://notion.so/<workspace>/Tech-Spec-Page-abc123`
