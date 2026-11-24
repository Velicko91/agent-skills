---
name: dnote
description: Searches, views, adds, edits, or removes notes and books in the dnote command-line notebook. Use for "/dnote", "find my note about …", "save this to dnote", or "what's in my <book> notes".
allowed-tools: Bash(dnote *), Read, Grep, Glob
model: haiku
---

# dnote

Dnote is a command-line notebook of books and notes. Run the `dnote` commands below.

## Hard rules

- NEVER remove a note or a book before the user confirms it in this conversation, because a removal cannot be undone. Show the note (or the notes of the book) first. Then run `dnote remove … -y`.
- Never open an editor: use `-c`, or stdin for new notes. `dnote add <book>` or `dnote edit <id>` with no content waits for an editor and hangs.
- Do not guess a book name. Get the list with `dnote view --name-only`.

## IDs

- `dnote view <book>` lists the notes of a book with their **global IDs**. Use a global ID for `edit` and `remove`.
- `dnote view <book> <index>` reads one note by its **index in the book**, starting at 0. Use the index only to read.

## Commands

| Task | Command |
|---|---|
| List the books | `dnote view --name-only` |
| List the notes of a book | `dnote view <book>` |
| Read one note | `dnote view <book> <index> --content-only` |
| Search all books | `dnote find "<keywords>"` |
| Search one book | `dnote find "<keywords>" -b <book>` |
| Add a one-line note | `dnote add <book> -c "<content>"` |
| Add a note with several lines, or with quotes | `dnote add <book> << 'EOF'` … `EOF` (the quoted `'EOF'` keeps the content as it is) |
| Change a note | `dnote edit <id> -c "<new content>"` |
| Move a note to another book | `dnote edit <id> -b <other book>` |
| Rename a book | `dnote edit <book> -n <new name>` |
| Remove a note or a book (after confirmation) | `dnote remove <id or book> -y` |

`dnote add` creates the book if it does not exist.

## Workflow

- **Search:** run `dnote find`, and show each match with its book and its global ID.
- **View:** list the notes with `dnote view <book>`, then read the one you need.
- **Add:** use `-c` for one line, and the heredoc for anything longer. Say which book holds the note.
- **Edit:** find the global ID with `dnote view <book>`, show the current content, then run `dnote edit <id> -c "…"`.
- **Remove:** show what will go, ask, and WAIT. Then run `dnote remove … -y`.

## Examples

- `/dnote find kafka consumer lag`
- `/dnote add git -c "git switch -c creates and switches to a branch"`
- `/dnote what's in my kubectl notes`
- `/dnote remove the old alembic note about downgrades` ← asks before it removes
