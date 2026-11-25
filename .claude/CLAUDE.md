# Claude Global Configuration

## Writing Style — ASD-STE100 Simplified Technical English

Write all output in Simplified Technical English (ASD-STE100).

**Words**
- Use one word for one meaning. Do not use a second word for the same thing.
- Use the simple word. Write "use" not "utilize", "start" not "initiate", "before" not "prior to".
- Do not use slang, idioms, or jargon. Do not use metaphors.
- Keep technical names and part names exactly as they are.

**Sentences**
- Keep instructions to 20 words or fewer. Keep descriptions to 25 words or fewer.
- Write one instruction in one sentence.
- Use the active voice. Write "the service sends the message", not "the message is sent".
- Use the present tense when you can.
- Do not remove articles. Write "the pump", not "pump".
- Do not put more than three nouns together.

**Structure**
- Keep paragraphs to six sentences or fewer.
- Put the condition first, then the instruction. Write "If the test fails, stop the run".
- Use a list when there is more than one step or item.
- Start each step with the verb.

**Always**
- Say what to do, not what not to do, when both are possible.
- Give a reason for a warning.
- Use the same term for the same thing in every file and every message.

## Response Format

**Length**
- Give the answer first. Add detail only if the user asks.
- Do not write a preamble, a restatement of the request, or a closing summary.
- Do not repeat file content or command output that the user can already see.
- Keep an answer to four sentences or fewer. Use a list when the answer has parts.

**Investigation results**
- If you investigate an option, an approach, or a change, write the result as pros and cons.
- Use this format:

  ```
  ### <option name>
  **Pros**
  - <point>

  **Cons**
  - <point>
  ```

- Put one fact in each point. Give the reason for each point.
- After the last option, write one line with your recommendation.

**Comparisons**
- If you compare two or more things, show the differences in a table.
- Write one row for each dimension. Write one column for each thing.
- Keep the rows that differ. Remove the rows that are the same.
- If you compare code or text, show a unified diff instead of a table.
- Show a difference in a table or a diff, not in prose.

## Commit messages

- Wrap each line of a commit message body at 72 characters, because commitlint (`body-max-line-length`) fails any body line over 100.
- Write the body with hard line breaks: one short `-m` per line, or a message file. Do not pass a paragraph as one `-m` line.
- Before a push, check the new commits: `git log --format=%b <base>..HEAD | awk 'length > 100'` must print nothing.

## cmux

- If the user asks to pause or unpause this session, run `cmux-pause <4h | until <when> | off>`. Run `cmux-pause` with no arguments for the forms of `<when>`.

## Skills Management

`$CLAUDE_CONFIG_REPO` is the checkout of this configuration repository. Set it in your
shell profile, for example:

```bash
export CLAUDE_CONFIG_REPO="$HOME/code/claude-config"
```

If the variable is not set, use the directory that holds this `CLAUDE.md`, two levels up.

**Skills source directory**: `$CLAUDE_CONFIG_REPO/.claude/skills/`
**Skills symlink directory**: `~/.claude/skills/`

### Adding New Skills

When creating a new skill:

1. **Create the skill in the source directory**:
   ```bash
   mkdir -p $CLAUDE_CONFIG_REPO/.claude/skills/{skill-name}
   # Create skill.md in that directory
   ```

2. **Create symlink in home**:
   ```bash
   ln -s $CLAUDE_CONFIG_REPO/.claude/skills/{skill-name} ~/.claude/skills/{skill-name}
   ```

### Current Skills

All skills should follow this pattern:
- Source: `$CLAUDE_CONFIG_REPO/.claude/skills/{skill-name}/skill.md`
- Symlink: `~/.claude/skills/{skill-name}` → source

### Why This Structure

- Skills are version-controlled in `$CLAUDE_CONFIG_REPO/`
- Symlinks in `~/.claude/skills/` make them available globally
- Changes to skills are tracked in git
