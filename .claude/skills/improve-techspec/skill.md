---
name: improve-techspec
description: Improves the wording, readability, and structure of a Notion tech spec while keeping all of its logic, tables, images, and code — writes a "<title>_claude" copy and adds review comments. Use for "/improve-techspec <notion-url>" or "polish this tech spec".
user-invocable: true
allowed-tools: Read, Grep, Glob, mcp__notion__notion-fetch, mcp__notion__notion-search, mcp__notion__notion-create-pages, mcp__notion__notion-update-page, mcp__notion__notion-create-comment
---

# Improve Tech Spec

Improve a tech spec in Notion for readability, wording, and structure. Keep all of its logic, meaning, and content. Write the result to a `<title>_claude` copy, and never change the original.

Requires the Notion MCP connection. If it is not active, tell the user to run `/mcp`.

## Hard rules

- Keep the meaning. Do not change a technical decision, add technical information, or remove context or nuance. When in doubt, keep the original wording.
- Do not over-condense. Keep the paragraphs that explain the "why".
- **Tables:** copy them exactly. Do not merge, split, reformat, or reorder them.
- **Images and files:** copy each reference exactly, including `notion-file-block://` references and captions, at the same place in the text.
- **Code blocks:** copy them verbatim, with their language tags.
- **Callouts and warnings:** keep them as they are, with their icons. Do not merge them into the text.
- Write to the `_claude` copy only. NEVER update the original page.

## Template

`tech-spec-template.md` in this skill directory shows the expected sections: Introduction (Problem, Context), Glossary, Scope (In/Out), Summary, System Architecture, Data Model, Interfaces, Impact & Risks, Observability, Product Metrics, Productionization (optional), Alternatives Considered. Use it only if the source has no clear structure. Do not force a document into it.

## Workflow

### Step 1 — Fetch the source

Fetch the URL with `mcp__notion__notion-fetch`. If it fails, ask the user to check the URL and the MCP connection. If the result is truncated, or lists `unknown_block_ids`, fetch those blocks too, so no content is lost.

### Step 2 — Find an existing copy

Search for `<original title>_claude` with `mcp__notion__notion-search`. If it exists, update it in Step 4. Otherwise create it.

### Step 3 — Improve

- **Clarity:** use simple words where they keep the technical precision. Split very long sentences, but do not cut the text into fragments. Prefer the active voice. Remove filler ("basically", "actually", "in order to").
- **Structure:** put the sections in a logical order, add headers to dense blocks, group related information, and make a list from a list hidden in a paragraph.
- **Section introductions:** if a header is followed directly by content, add 1–2 sentences that say what the section covers and why it matters, for example before a table.
- Note each ambiguous section, each change that could affect the meaning, and each area that needs more detail. They become comments in Step 5.

### Step 4 — Write the copy

Before the first write, read the Notion-flavored Markdown spec with `mcp__notion__notion-fetch` and the id `notion://docs/notion-flavored-markdown-spec`, because the tools reject guessed syntax.

- **Create:** `mcp__notion__notion-create-pages` with the title `<Original Title>_claude`, under the parent of the original.
- **Update:** `mcp__notion__notion-update-page` on the existing copy. If it reports child pages that would be deleted, show the list, and ask before you continue.

### Step 5 — Add comments

Add a comment with `mcp__notion__notion-create-comment` for each item noted in Step 3: ambiguous sections, changes that could affect the meaning, areas that need more detail, and suggestions for more content.

### Step 6 — Report

1. The link to the `_claude` page
2. A summary of the changes
3. The comments that you added

Say that the copy is a draft to review before sharing, and that a well-structured document gets few changes.

## Examples

**Verbose → clearer, but not too short**
```
Before: In order to be able to successfully implement this feature, we will need to first ensure that the database schema has been properly updated with all of the necessary columns and indexes.

After: Before implementing this feature, ensure the database schema is updated with the required columns and indexes.
```
"Ensure" and "required" stay, to keep the imperative tone.

**Passive → active**
```
Before: The API endpoint will be called by the frontend when the user clicks the submit button.

After: The frontend calls the API endpoint when the user clicks submit.
```

**Missing introduction → context added**
```
Before:
## Monitoring
| Metric | Description |

After:
## Monitoring
The following metrics should be tracked to ensure system health and detect issues early.

| Metric | Description |
```

**Wall of text → steps**
```
Before: The system processes incoming requests by first validating the authentication token then checking user permissions then parsing the request body then executing the business logic then formatting the response then logging the transaction.

After:
The system processes incoming requests through the following steps:
1. Validate authentication token
2. Check user permissions
3. Parse request body
4. Execute business logic
5. Format response
6. Log transaction
```

Usage: `/improve-techspec https://notion.so/<workspace>/Tech-Spec-Page-abc123`

## Retry

If the user says "retry", reuse nothing from the earlier run. Fetch the document again, and run the workflow from Step 1.
