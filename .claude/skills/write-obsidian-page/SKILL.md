---
name: write-obsidian-page
description: Turns inline text, a file, or a URL into an atomic Obsidian note in the PARA vault, with frontmatter, [[wiki-links]] to existing notes and new concepts, and an updated Map of Content. Use for "save this to Obsidian", "add to my second brain", or "/write-obsidian-page".
user-invocable: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(date *), Bash(mkdir *), Bash(ls *), Bash(find *), WebFetch
---

# Write Obsidian Page

Turn free-form context into one atomic Obsidian note in the user's PARA vault. Link it to existing notes, add dangling `[[wiki-links]]` for important concepts that have no note yet, and add it to a Map of Content (MOC).

## Hard rules

- One concept per note. If the source covers more, write one note and list the others under "Open Threads".
- ALWAYS show the draft and WAIT before writing, unless `--yolo` is given.
- NEVER overwrite a note silently. If `<Title>.md` exists anywhere in the vault, ask: append, rename, or cancel.
- NEVER invent facts. Expand only what the source says. If a section needs facts that the source does not have, drop it or flag it with `> [!warning]`.
- Expand bullets into sentences. Keep code blocks, numbers, names, dates, and URLs exactly as they are.
- Write links as `[[Note Title]]`, never `[[path/to/Note]]` and never `[Note](Note.md)`, because Obsidian resolves titles globally.
- Keep the frontmatter consistent: lowercase keys, ISO dates, kebab-case tags, and list values for `tags` and `aliases`.
- If the vault is missing or unreadable, ask for the path. Do not guess.

## Vault

| Field | Value |
|---|---|
| Vault root | `--vault <path>`, else `$OBSIDIAN_VAULT`, else `~/obsidian/` |
| Scheme | PARA + atomic notes |
| Top folders | `Projects/`, `Areas/`, `Resources/`, `Archive/`, `_Inbox/`, `_MOCs/` |
| File name | `<Title>.md`. Keep the spaces and the case. Remove `* " \ / < > : \| ? # ^ [ ]`, because Obsidian does not allow them in file names. |
| Link style | `[[Note Title]]` |

## Arguments

```
/write-obsidian-page <context> [--title "..."] [--bucket ...] [--tags ...]
                               [--moc "..."] [--vault <path>] [--date YYYY-MM-DD]
                               [--existing-only] [--no-danglings] [--no-moc] [--yolo]
```

`<context>` is everything before the first `--` flag.

| Field | Default | Override |
|---|---|---|
| bucket | from Phase 3 | `--bucket projects\|areas\|resources\|archive\|inbox` |
| title | the first H1, the page title, or the first important noun phrase | `--title "..."` |
| tags | 2 to 5 lowercase kebab-case tags | `--tags a,b,c` |
| date | `date -u +%Y-%m-%d` | `--date YYYY-MM-DD` |
| MOC | the matching MOC, created if absent | `--moc "<MOC Title>"`, `--no-moc` |
| links | existing notes + danglings for new concepts | `--existing-only`, `--no-danglings` |
| checkpoint | show the draft and wait | `--yolo` (only if a caller already reviewed the text) |

Use the defaults with no confirmation.

## Workflow

### Phase 1 — Locate the vault

1. Resolve the path: `ls -d "<--vault value>"`, else `ls -d "${OBSIDIAN_VAULT:-$HOME/obsidian}"`. If it does not exist, STOP and ask for the path.
2. Create each missing top folder with `mkdir -p`, with no prompt.
3. If `_MOCs/Index.md` is missing, create it:
   ```markdown
   # Index
   The root MOC. Lists the active MOCs in this vault.
   ```

### Phase 2 — Read the context

| Context | Action |
|---|---|
| An HTTP(S) URL | `WebFetch` it. Use the title and the main content, without navigation and footers, up to about 4,000 words. |
| A path that exists | `Read` it. Use the file name and the content, up to about 4,000 words. |
| Text with bullets, headings, or paragraphs | Use it as it is. |
| A short phrase | Treat it as a topic, and ask the user for more before you write. |
| Empty | STOP and ask for context. |

Record the candidate title, the candidate tags (recurring nouns, named entities, domain words), the source URL or path, and the type of content: a definition, a how-to, a decision, a meeting summary, a reference, or a log.

### Phase 3 — Classify into a PARA bucket

The first match wins, unless `--bucket` is given.

| Signals in the source | Bucket |
|---|---|
| A deadline, a deliverable, or "we're shipping X by Y" | `Projects` |
| An ongoing responsibility, role, or recurring topic (health, finances, an oncall area) | `Areas` |
| Reference material: definitions, how-tos, articles, library docs, frameworks | `Resources` |
| "archived", "old", "deprecated", or finished past work | `Archive` |
| A quick capture, a rough thought, or unsorted content | `_Inbox` |

### Phase 4 — Find links

1. List the important noun phrases of the source. Use your judgement, not a regex.
2. `Glob` `<vault>/**/*.md`. Match each phrase against the note names, case-insensitive and without punctuation. Also `Grep` for `^aliases:` and match the aliases.
3. Sort the phrases:
   - A match → `[[Existing Note]]`.
   - An important, reusable concept with no note → `[[Dangling Concept]]`, unless `--no-danglings` or `--existing-only`.
   - A one-off mention → plain text.
4. Keep about 12 links or fewer. Pick the strongest ones.
5. Check that no note named `<Title>.md` exists. If one exists, ask: append, rename, or cancel.

### Phase 5 — Write the draft

```markdown
---
title: <Title>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
tags: [<tag1>, <tag2>, ...]
source: <URL or file path or "inline">
bucket: <Projects|Areas|Resources|Archive|_Inbox>
aliases: []
---

# <Title>

> [!summary] TL;DR
> <One or two sentences: what is this note about?>

## Context
<2–4 sentences: why this matters, where it came from, what triggered the capture.>

## Notes
<The substance, in prose. Put [[wiki-links]] inline where they fit.>

## Related
- [[Existing Note A]]
- [[Dangling Concept C]]  <!-- new stub, fill out later -->

## Open Threads
- <Questions or follow-ups that the source raised and did not answer. Omit the section if there are none.>

## Source
<URL or file path, or "inline (typed by user on <date>)">
```

- "Related" holds only the links that did not fit inline.
- Write no filler ("in conclusion", "basically", "it is worth noting").
- Keep code and quotes as fenced blocks or blockquotes. Do not paraphrase them.

### Phase 6 — Choose the MOC

1. Use `--moc` if it is given.
2. Otherwise, take the strongest topic of the note (for example "Obsidian Workflow" or "Oncall Process"), and look for `_MOCs/<Topic>.md`.
3. If none exists and `--no-moc` is not given, plan a new MOC.

The entry, under `## Notes` of the MOC: `- [[<Title>]] — <8–14 word description>`

A new MOC:

```markdown
---
title: <Topic> MOC
created: <YYYY-MM-DD>
tags: [moc, <topic-tag>]
---

# <Topic> MOC

A map of notes related to <topic>.

## Notes
- [[<Title>]] — <description>
```

A new MOC also gets a one-line entry in `_MOCs/Index.md`.

### CHECKPOINT

Unless `--yolo` is given, show the plan, then STOP and WAIT:

```
📍 Vault:    <vault path>
📂 Bucket:   <bucket>  →  <target folder>
📄 File:     <Title>.md
🗂  MOC:      <MOC title>   (new)  |  (existing)  |  (skipped, --no-moc)

🏷  Tags:     [tag1, tag2, ...]
🔗 Links:
   existing  → [[Note A]], [[Note B]]
   dangling  → [[Concept C]], [[Concept D]]

— DRAFT ——————————————————————————————————————
<the full markdown of the note>
———————————————————————————————————————————

Write the note + update MOC?  (yes / edit / cancel)
```

On "edit", apply the changes and show the plan again. On "cancel", stop and write nothing.

### Phase 7 — Write

1. `mkdir -p` the bucket folder, and `Write` `<vault>/<bucket>/<Title>.md`.
2. For a new MOC, `Write` `<vault>/_MOCs/<Topic>.md`, and `Edit` `_MOCs/Index.md` to add it. For an existing MOC, `Edit` it to add the entry under `## Notes`.
3. Do not create files for dangling links. Obsidian shows them as unresolved links, which is the purpose.

### Phase 8 — Confirm

```
✅ Wrote: <vault>/<bucket>/<Title>.md
🗂  MOC updated: <vault>/_MOCs/<Topic>.md
🔗 Links: <N existing> + <M dangling>
🏷  Tags: [...]
```

## Examples

- `/write-obsidian-page https://help.obsidian.md/Linking+notes/Internal+links` ← a Resource note
- `/write-obsidian-page "Talked with Sam about moving to direct ETF buys for tax-loss harvesting. Decided to wait until Q3." --bucket areas --tags investing,tax-loss-harvesting`
- `/write-obsidian-page ~/Downloads/article.md --title "Zettelkasten First Principles"`
- `/write-obsidian-page "Try the Dataview plugin to surface stale Inbox notes." --bucket inbox --no-moc`

A caller skill passes its formatted text as `<context>`, with `--bucket` and `--tags`. It passes `--yolo` only if it already reviewed the text.

## Retry

If the user says "retry", reuse no classification, link scan, or draft. Fetch the URL or read the file again, scan the vault again, and run the workflow from Phase 1.
