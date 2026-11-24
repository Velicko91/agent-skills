---
name: notion-document
description: Expands bullets from a localhost page or a local file into a polished Notion document — `create` publishes a new page from a type template, `update` appends a section in the page's style. Use for "/notion-document create|update" or "publish this to Notion".
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash(curl -s http://localhost*), Bash(curl -s http://127.0.0.1*), Bash(date *), mcp__notion__notion-fetch, mcp__notion__notion-search, mcp__notion__notion-create-pages, mcp__notion__notion-update-page
---

# Notion Document

Read a localhost page or a local file of bullets, expand them into prose, and publish the result to Notion: as a new page (`create`), or as a new section of an existing page (`update`).

## Hard rules

- Expand each bullet into at least one full sentence. NEVER copy bullets verbatim.
- NEVER invent facts. Expand only what the bullets say. Flag each gap with a ⚠️ callout.
- Ask all questions in one message, and only questions that change the output.
- `update` only appends. NEVER change or delete existing content, because the page belongs to other people.
- `create` uses only a parent that you verified with `notion-fetch`. NEVER create a page under a wrong parent.
- Always end with the link to the page.

## Arguments

```
/notion-document create <source> [<notion-parent-url>] [--title "..."]
/notion-document update <source> <notion-page-url> [--heading "..."]
```

| Argument | Effect |
|---|---|
| `create` / `update` | Required. Create a new page, or append to an existing page. |
| `<source>` | A page on `http://localhost` or `http://127.0.0.1`, or a local file, for example the `design-alignment-*.md` of `/drill-me` |
| `<notion-parent-url>` | `create`: the parent page. Without it, the page is private in the workspace root. |
| `<notion-page-url>` | `update`: the page to append to. Required. |
| `--title "..."` | `create`: overrides the inferred title |
| `--heading "..."` | `update`: the heading of the new section. It wins over an inferred heading. |

If the command or a required URL is missing, ask for it.

## Workflow

### Step 1 — Fetch the source

For a URL, run `curl -s <source>`; do not use `WebFetch`, because it cannot fetch `localhost`. For a file, `Read` it. Take the title (`<title>`, the first `#` or `<h1>`, the URL path, or the file name, for example `incident-postmortem-2024-03`), all list items, and the section headings that group them. From a file, also keep its tables and paragraphs. If the source returns an error or is empty, stop, and ask the user to check it.

### Step 2 — Fetch the target

- **`create` with a parent:** `notion-fetch` the parent URL, and take its page ID. If it cannot be fetched, report the error, and ask whether to publish a private page instead.
- **`update`:** `notion-fetch` the page. Take its ID, title, sections, heading depth (for example, heading_2 for top-level sections), and tone. If it cannot be fetched, stop, and ask the user to check the URL and the permissions.

### Step 3 — Infer the document type (`create` only)

The first match wins:

| Keywords in the title or bullets | Type |
|---|---|
| `postmortem`, `incident`, `outage`, `retrospective` | Postmortem |
| `runbook`, `playbook`, `oncall`, `on-call` | Runbook |
| `adr`, `architecture decision`, `decision record` | ADR |
| `rfc`, `request for comment` | RFC |
| `meeting`, `notes`, `sync`, `standup`, `1-1`, `1on1` | Meeting Notes |
| `onboarding`, `getting started`, `new hire` | Onboarding Guide |
| `brief`, `project`, `initiative`, `kickoff` | Project Brief |
| `spec`, `technical`, `design`, `eng`, `engineering` | Tech Spec |
| `readme`, `documentation`, `guide`, `how-to`, `howto` | Documentation |
| `plan`, `roadmap`, `quarter`, `q1`, `q2`, `q3`, `q4` | Planning Doc |
| *(no match)* | General Document |

### Step 4 — Ask about the gaps

STOP before you write. Ask one question for each condition that is true, all in one message, grouped by theme:

| Condition | Command | Question |
|---|---|---|
| Fewer than 5 bullets, and sparse | both | "The source page only has [N] bullets — should I proceed as-is, or is there more content I'm missing?" |
| The type matched nothing | `create` | "Is this a [best guess A] or [best guess B]?" |
| The title is missing, or a slug with no clear meaning | `create` | "What should the document title be?" |
| The audience is not clear and changes the tone (engineers or leadership) | `create` | "Who is the primary audience?" |
| Postmortem: the severity, the date, or the affected systems are missing | `create` | "What was the severity, and which systems or users were affected?" |
| ADR: the decision is not clear from the alternatives | `create` | "What is the final decision?" |
| Meeting Notes: the date or the attendees are missing | `create` | "When was the meeting, and who attended?" |
| Tech Spec, ADR, or RFC: the author or the reviewer matters and is missing | `create` | "Who is the author, and who reviews it?" |
| Two pages match the parent URL | `create` | "Which one is the parent: [A] or [B]?" |
| The heading is missing or ambiguous | `update` | "What heading should I use for this new section?" |
| The content repeats an existing section | `update` | "The page already has a '[Section]' section — append to it, or add a new one?" |
| The tone differs much from the page | `update` | "The page reads as [style] — should the new section match it?" |

Do not ask if you can infer the answer. Fix a slug title silently (`my-doc` → "My Doc"). Leave a missing non-critical field as a placeholder, for example `**Author:** —`. If there are 5 or more coherent bullets, continue, and add the ⚠️ callout if the detail is limited. WAIT for the answers.

### Step 5 — Write

- **`create`:** read `templates.md` in this skill directory, and use the template of the type.
- **`update`:** match the heading depth, the tone, and the structure of the page, so the section reads as part of it.

For both:
- Group related bullets under one heading. Do not give each bullet its own heading.
- Connect the sections, so the text reads as prose, not a list.
- Put questions and open items in an "Open Questions" section.
- Keep numbers, names, dates, proper nouns, and links exactly as written. Keep code as code blocks.
- If the source is sparse, write only what you can infer with confidence, and add the callout "⚠️ Source had limited detail — review and expand before sharing."
- Write in the present tense and the active voice, for a technical reader, with no filler ("in order to", "it is worth noting", "basically").

Write Notion-flavored Markdown. Before the first write, read its spec with `notion-fetch` and the id `notion://docs/notion-flavored-markdown-spec`, because the tools reject guessed syntax. Write a callout as `<callout icon="⚠️" color="yellow_bg">…</callout>`, and a date as `<date start="YYYY-MM-DD" />`, with the date from `date -u +%Y-%m-%d`. Do not put the page title in the content.

### Step 6 — Publish

- **`create`:** `notion-create-pages` with `properties: {"title": "<title>"}`, the `content`, and `parent: {"type": "page_id", "page_id": "<ID from Step 2>"}`. Without a parent, set `creation_mode: "draft"` instead, which makes a private page.
- **`update`:** `notion-update-page` on the page ID from Step 2, with `command: "insert_content"` and `position: {"type": "end"}`. Never use `replace_content`, because it can delete existing content.

### Step 7 — Confirm

```
✅ <Published | Appended to>: <page title>
🔗 <page URL>

Type:     <type>                          (create)
Sections: <headings added>
Parent:   <parent title or "Private">     (create)

Anything to revise?
```

## Examples

- `/notion-document create http://localhost:3000/my-doc` ← a private page
- `/notion-document create ./design-alignment-PROJ-1234-webhooks.md` ← publish a `/drill-me` document
- `/notion-document create http://localhost:3000/my-doc https://notion.so/acme/Parent-abc123 --title "Q2 Planning Brief"`
- `/notion-document update http://localhost:3000/new-section https://notion.so/acme/Spec-def456`
- `/notion-document update http://localhost:3000/notes https://notion.so/acme/Spec-def456 --heading "Rollout"`
