---
name: update-skill
description: Updates an existing Claude Code skill by reading the current SKILL.md, applying described changes, showing a diff, and iterating until the user is satisfied. Use when modifying, improving, or extending an existing slash command or skill.
user-invocable: true
allowed-tools: Read, Write, Edit, Bash(ls *), Bash(diff *), Bash(mv *), Bash(ln *), Bash(rm *), Bash(cat *), Bash(python3 *), Bash(grep *), Bash(wc *), Bash(cp *), Bash(mkdir *)
---

# Update Skill

Modify an existing Claude Code skill interactively — apply changes, show a diff, iterate until the user is happy, then write the final version.

## Prerequisites

- Skills source: `$CLAUDE_CONFIG_REPO/.claude/skills/`
- Skills symlink dir: `~/.claude/skills/`

---

## Private data — NEVER hardcode it

A skill in this repo may be published. Treat every skill file as public.

**Private data is anything specific to one organization or machine:**

| Kind | Examples |
|---|---|
| Hosts | issue tracker, wiki, Slack workspace, internal registry |
| Identifiers | project keys, team ids, board ids, custom field ids, cloud project ids |
| Topology | service names, namespaces, container names, database names, repo names |
| People | real names, emails, usernames |
| Paths | anything under a home directory with a person's name in it |

**Where each value belongs:**

| The value is… | Put it in | Referenced as |
|---|---|---|
| Org-wide, used by several skills | `~/.claude/config.local.json` | `<jira.host>`, `<linear.workspace>` |
| Specific to this one skill | `<skill-dir>/data.json` | read at runtime |
| An illustration in an example | Neither — invent one | `acme`, `alice`, `PROJ-1234` |

Both files are gitignored. A committed `*.example.json` shows the shape.

When a change introduces a private value, rewrite the skill to **read it at runtime**,
and state what happens when it is absent:

```markdown
## Local configuration

Read `~/.claude/config.local.json` for `<keys>`. If it is missing, copy
`config.example.json` and ask the user. NEVER guess a host or an identifier.
```

If the change is only to add a value the user gave you, put the value in the config
file and reference it. Never paste it into the skill.

### Verify before you save — REQUIRED

Run this on the **proposed** file, before writing it back. The local config already
holds the private values, so no deny-list needs maintaining:

```bash
python3 - /tmp/update-skill-proposed.md <<'PY'
import json, pathlib, sys
# Enum-valued keys hold generic words ("active", "high", "poetry"). Skip them,
# or the check floods with false positives and stops being read.
SKIP_KEYS = {'status','accept','onOutOfPolicy','ecosystem','minSeverity','defaultEnv',
             'note','version','owns','teamField','sprintField'}
cfg = pathlib.Path.home()/'.claude/config.local.json'
vals = set()
def walk(o, key=None):
    if isinstance(o, dict):
        for k, v in o.items():
            if k.startswith('_') or k in SKIP_KEYS: continue
            walk(v, k)
    elif isinstance(o, list):
        for v in o: walk(v, key)
    elif isinstance(o, str) and len(o) > 3 and key not in SKIP_KEYS:
        vals.add(o)
if cfg.exists():
    walk(json.loads(cfg.read_text()))
text = pathlib.Path(sys.argv[1]).read_text()
hits = sorted(v for v in vals if v in text)
print("LEAK — these config values appear in the skill:", hits) if hits else print("clean")
PY
```

Then check what the config cannot know about:

```bash
grep -nIiE '<your-name>|<your-work-email>|/Users/<you>|/home/<you>' /tmp/update-skill-proposed.md || echo "clean"
```

**This check is a safety net, not proof.** It only catches values already in the
config. A private value that was never added there will pass. Read the diff yourself
as well, and ask: would this line mean anything to a stranger?

**If either check finds anything, fix it and show the user a new diff.** Move the
value into the config, replace it with a placeholder, then re-run the check.

**NEVER write the skill file while the check fails**, even when the user says "done".
Report the leak instead, and show what you propose to replace it with.

## Arguments

```
/update-skill <skill-name> <description-of-changes>
```

| Argument | Required | Description |
|----------|----------|-------------|
| `skill-name` | Yes | Name of the existing skill to update (first word of $ARGUMENTS) |
| `description-of-changes` | Yes | Free-form description of what to change (everything after the first word) |

Parse `$ARGUMENTS` by splitting on the first whitespace: everything before = skill name, everything after = change description.

## Workflow

### Phase 1 — Validate & Read

1. Parse skill name and change description from `$ARGUMENTS`.
2. Check that the skill exists:
   ```bash
   ls $CLAUDE_CONFIG_REPO/.claude/skills/<skill-name>/SKILL.md
   ```
   If it does not exist, STOP and output:
   ```
   ❌ Skill '<skill-name>' not found.

   Available skills:
   <output of: ls ~/.claude/skills/>
   ```
   Do NOT proceed.
3. Read the current skill file and any reference files that it links:
   ```
   Read $CLAUDE_CONFIG_REPO/.claude/skills/<skill-name>/SKILL.md
   ```
4. Read `~/.claude/skills/create-skill/authoring-rules.md`.

### Phase 2 — Apply Changes & Show Diff

1. Generate the full proposed new content based on the change description.
   - Apply `authoring-rules.md` to each line you add or change.
   - If the change asks to shorten, trim, or optimize the skill, run the **Trim pass and meaning check** on the whole skill.
2. Write the proposed version to a temp file:
   ```
   Write /tmp/update-skill-proposed.md
   ```
   Write each new or changed reference file to `/tmp/update-skill-proposed/<file>`.
3. Show the diff against the original:
   ```bash
   diff -u $CLAUDE_CONFIG_REPO/.claude/skills/<skill-name>/SKILL.md /tmp/update-skill-proposed.md
   ```
   For a new reference file, diff it against `/dev/null`.
   Display the diff output in a code block.
4. Show the size before and after:
   ```bash
   wc -c $CLAUDE_CONFIG_REPO/.claude/skills/<skill-name>/SKILL.md /tmp/update-skill-proposed.md
   ```
5. If the trim pass ran, list each fact that moved to a reference file, and give the name of that file.

# --- CHECKPOINT ---
After showing the diff, ask exactly:

> What should I modify? (or say **"done"** to save)

STOP and WAIT for the user's response. Do NOT write to the real skill file yet.

### Phase 3 — Iteration Loop

Repeat until the user says "done" (or a clear equivalent like "looks good", "ship it", "save it"):

1. Apply the user's requested changes to `/tmp/update-skill-proposed.md`.
2. Show the updated diff:
   ```bash
   diff -u $CLAUDE_CONFIG_REPO/.claude/skills/<skill-name>/SKILL.md /tmp/update-skill-proposed.md
   ```
3. Ask again:
   > What should I modify? (or say **"done"** to save)
4. STOP and WAIT.

### Phase 4 — Write & Handle Renames

Once the user approves:

1. Check if the frontmatter `name:` field in the proposed version differs from `<skill-name>`.

   **If the name changed** (e.g. `name: new-name`):
   - Move the source directory:
     ```bash
     mv $CLAUDE_CONFIG_REPO/.claude/skills/<old-name> $CLAUDE_CONFIG_REPO/.claude/skills/<new-name>
     ```
   - Remove the old symlink:
     ```bash
     rm ~/.claude/skills/<old-name>
     ```
   - Create new symlink:
     ```bash
     ln -s $CLAUDE_CONFIG_REPO/.claude/skills/<new-name> ~/.claude/skills/<new-name>
     ```
   - Write the final content to:
     `$CLAUDE_CONFIG_REPO/.claude/skills/<new-name>/SKILL.md`

   **If the name did not change:**
   - Write the final content to:
     `$CLAUDE_CONFIG_REPO/.claude/skills/<skill-name>/SKILL.md`

2. Copy each file from `/tmp/update-skill-proposed/` into the skill directory.

3. Clean up:
   ```bash
   rm -r /tmp/update-skill-proposed.md /tmp/update-skill-proposed
   ```

### Phase 5 — Output

Display:

```
✅ Updated: /<skill-name>

📁 Source:  $CLAUDE_CONFIG_REPO/.claude/skills/<skill-name>/SKILL.md
🔗 Symlink: ~/.claude/skills/<skill-name>
```

Then show the full final SKILL.md content so the user can review it.

## Rules

- NEVER write to the real skill file before the user says "done".
- **NEVER write the skill file while the private-data check fails** — not even on
  "done". Report the leak and propose a placeholder instead.
- **NEVER paste a private value into a skill.** Put it in `config.local.json` or the
  skill's `data.json`, and reference it.
- ALWAYS show a diff — never just describe the changes in words.
- **NEVER remove a fact when you shorten a skill.** Each command, condition, default, and NEVER/ALWAYS rule stays in `SKILL.md` or in a linked reference file.
- NEVER drip-feed questions — one message per iteration.
- If the skill does not exist, fail immediately with the error message and available skills list.
- When the name changes, update BOTH the source directory and the symlink.

## Examples

- `/update-skill create-pr add a --draft flag that creates the PR in draft mode`
- `/update-skill lint also run prettier after ruff`
- `/update-skill solve-ticket always confirm the implementation plan before writing code`
- `/update-skill review-dependabot-pr trim it and move the templates to reference files`

## Retry

Say **"retry"** to restart from scratch with the original file.

When retrying:
1. Re-read the original skill file fresh
2. Discard `/tmp/update-skill-proposed.md` and `/tmp/update-skill-proposed/` if they exist
3. Treat as a completely new execution
