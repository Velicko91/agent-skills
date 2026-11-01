---
name: create-skill
description: Scaffold a new Claude Code skill following all best practices — gathers requirements, designs workflow, writes skill.md, and creates the symlink. Use when creating a new slash command or skill from scratch.
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash(ls *), Bash(mkdir *), Bash(ln *), Bash(cat *), Bash(python3 *), Bash(grep *), Write, Edit
---

# Create Skill

Scaffold a new Claude Code skill from scratch, following all established conventions and best practices.

## Prerequisites

- Skills source: `$CLAUDE_CONFIG_REPO/.claude/skills/`
- Skills symlink dir: `~/.claude/skills/`
- Each skill is a directory containing a single `skill.md` file
- Symlinks make skills available globally

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

When a skill needs a private value, write the skill to **read it at runtime**, and
state what happens when it is absent:

```markdown
## Local configuration

Read `~/.claude/config.local.json` for `<keys>`. If it is missing, copy
`config.example.json` and ask the user. NEVER guess a host or an identifier.
```

### Verify before you finish — REQUIRED

After you write the skill, check it against the real private values. The local
config already holds them, so no deny-list needs maintaining:

```bash
python3 - "$SKILL_FILE" <<'PY'
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
grep -nIiE '<your-name>|<your-work-email>|/Users/<you>|/home/<you>' "$SKILL_FILE" || echo "clean"
```

**This check is a safety net, not proof.** It only catches values that are already in
the config. A private value that was never added there will pass. Read the skill
yourself as well, and ask: would this line mean anything to a stranger?

**If either check finds anything, fix it before you finish.** Move the value into the
config, replace it with a placeholder, and run the check again.

**NEVER report a skill as done while a check fails.**

## Workflow

### Phase 1 — Gather Requirements

Parse `$ARGUMENTS` for the skill name and any inline description.

Then ask ALL of the following in a **single message** (do not drip-feed questions):

1. **Purpose** — What does this skill do in one sentence? (if not in $ARGUMENTS)
2. **Trigger** — When should a user invoke it? Any keywords they'd say?
3. **Arguments** — Does it take arguments? Flags? Optional or required?
4. **Actions** — Does it READ only, or does it WRITE/CREATE/MODIFY files, call APIs, run commands?
5. **Interaction** — Is it fire-and-forget, or does it need checkpoints (stop and wait for user approval before proceeding)?
6. **Tools needed** — Which tools will it use? (Read/Grep/Glob, Bash patterns, MCP tools, Write/Edit)
7. **Similar skills** — Is there an existing skill it resembles? (for reference)

**STOP. Do NOT write the skill yet. Wait for the user's answers.**

---

### Phase 2 — Inspect Existing Skills for Context

After collecting answers, scan relevant existing skills for patterns:

```bash
ls ~/.claude/skills/
```

If the user named a similar skill, read it:
```
Read ~/.claude/skills/<similar-skill>/skill.md
```

Use what you find to match conventions (section names, flag patterns, output format, defaults tables).

---

### Phase 3 — Design the Skill

Read `authoring-rules.md` in this skill directory. Apply its rules to every line of the new skill.

Compose the skill with these building blocks (include only what applies):

#### Frontmatter (required)

```yaml
---
name: <kebab-case-name>
description: <third-person, includes what AND when, max 1024 chars>
user-invocable: true
allowed-tools: <only tools this skill actually needs>
---
```

**Description rules:**
- Third person: "Generates X" not "I generate X"
- Include **what** it does AND **when** to use it
- Include two or three trigger phrases users would naturally say
- Keep it to 300 characters or fewer — every session loads it (see `authoring-rules.md`)
- Example: "Runs database migrations and verifies schema. Use when deploying schema changes or when the user mentions migrations or schema updates."

**`model` rule:** set `model:` from the work type in the `authoring-rules.md` table — `haiku` (mechanical), `sonnet` (moderate), or omit (judgement).

**`allowed-tools` rules:**
- List only tools the skill will actually call
- Scope Bash: `Bash(git *)` not bare `Bash`
- Fire-and-forget with side effects, or started only with `/name` → add `disable-model-invocation: true` (this also removes the description from the context)
- Background knowledge (never user-called) → `user-invocable: false`
- Needs a subagent → add `context: fork` + `agent: Explore` (or `general-purpose`)
- Everything allowed → `allowed-tools: "*"` (only for full orchestration skills)

#### Argument Handling

| Pattern | When to use | Example |
|---------|-------------|---------|
| `$ARGUMENTS` | All args as one string | Free-form description |
| `$ARGUMENTS[0]`, `$0` | Positional args | `/skill file.py json` → `$0` = file.py |
| `--flag <value>` | Named overrides | `--type Bug`, `--team Investments` |
| `--flag` (boolean) | Toggle behavior | `--draft`, `--no-code`, `--dry-run` |
| None (interactive) | Skill asks questions | Docs, spec writers |

Document argument parsing order explicitly. State which are required vs. optional.

#### Defaults Table (if applicable)

```markdown
## Defaults

| Field | Default | Override |
|-------|---------|----------|
| `field` | `value` | `--flag value` |
```

Rule: Never ask the user to confirm defaults — just use them unless overridden.

#### Workflow Structure

**For simple skills** (single pass, no user interaction):
```markdown
## Workflow

1. Step one
2. Step two
3. Step three
```

**For complex skills** (multi-phase, checkpoints):
```markdown
## Workflow

### Phase 1 — <Name>
[Actions]

# --- CHECKPOINT ---
Present findings to the user. STOP and WAIT for direction.
Do NOT proceed to Phase 2 automatically.

### Phase 2 — <Name>
[Actions — only after user approves]
```

**Checkpoint rules:**
- Any skill that WRITES code/files/records needs at least one checkpoint before doing so
- All clarifying questions go in **one message** — never drip-feed
- Explicitly write `STOP` and `WAIT` — do not imply it

#### DO / DON'T Rules (if applicable)

```markdown
## Rules

- DO X when Y
- NEVER Z (reason)
- Always prefer A over B
```

Use **CAPS** for critical rules that must not be violated.

#### Usage Examples (required, minimum 2)

```markdown
## Examples

- `/skill-name basic usage`
- `/skill-name --flag value detailed usage`
- `/skill-name --no-something alternative path`
```

#### Retry Option (for skills with state/side-effects)

```markdown
## Retry

Say **"retry"** to re-run from scratch.

When retrying:
1. Do NOT use any cached information
2. Re-read all files and fetch all data fresh
3. Treat as a completely new execution
```

---

### Phase 4 — Write the Skill

**Step 1** — Create the source directory and file:
```bash
mkdir -p $CLAUDE_CONFIG_REPO/.claude/skills/<name>
```
Then write `$CLAUDE_CONFIG_REPO/.claude/skills/<name>/skill.md`.

**Step 2** — Create the symlink (only if it doesn't exist):
```bash
ln -s $CLAUDE_CONFIG_REPO/.claude/skills/<name> ~/.claude/skills/<name>
```

**Step 3** — Verify:
```bash
ls -la ~/.claude/skills/<name>
```

**Step 4** — Write reference files, if the design has them, into the same directory. Link each one from the step in `skill.md` that uses it.

---

### Phase 5 — Output

After creation display:

```
✅ Created: /<name>

📁 Source:  $CLAUDE_CONFIG_REPO/.claude/skills/<name>/skill.md
🔗 Symlink: ~/.claude/skills/<name>

Invoke with: /<name> [arguments]
```

Then show the full skill.md content so the user can review it.

Then list three test inputs for the skill, from the **Test** section of `authoring-rules.md`.

Offer:
> Want to adjust anything? Tell me what to change, or say **"retry"** to redesign from scratch.

---

## Tier-1 Skill Checklist

Use this when reviewing a generated skill before finalising:

- [ ] Frontmatter: `name`, `description` (third-person, what + when), `allowed-tools` (scoped)
- [ ] Description is 300 characters or fewer, with two or three trigger phrases
- [ ] `model:` matches the work type, or is omitted for judgement work
- [ ] Body has only what Claude does not know; each rule appears once
- [ ] Templates, command maps, and schemas are in reference files, linked from `skill.md`
- [ ] The skill output gives the result first, from a template or an example, with no hard word limit
- [ ] Arguments documented (required vs. optional, flags explained)
- [ ] Defaults table present (if applicable)
- [ ] Workflow has numbered phases/steps
- [ ] Checkpoints present before any writes (if applicable)
- [ ] DO/DON'T rules capture critical constraints
- [ ] At least 2 usage examples
- [ ] Retry section present (if stateful)
- [ ] Body under 300 lines (hard limit 500)
- [ ] No time-sensitive info ("as of March 2026…")
- [ ] No Windows-style paths (use `/` not `\`)
- [ ] **No private data — the config-value check passes**
- [ ] Examples use invented names (`acme`, `alice`, `PROJ-1234`), never real ones

---

## Examples

- `/create-skill fix-flaky-tests — diagnoses and fixes flaky test suites`
- `/create-skill migrate-db run alembic migrations with dry-run support`
- `/create-skill oncall-handoff --no-interactive generate oncall handoff doc from incidents`
- `/create-skill weekly-report` ← skill will ask clarifying questions
