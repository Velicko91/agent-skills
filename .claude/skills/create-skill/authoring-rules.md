# Skill authoring rules — token budget and wording

`/create-skill` and `/update-skill` both use these rules. Apply every rule to each line you write.

## Contents
- Description
- Body
- Reference files
- Model choice
- Output of the skill
- Trim pass and meaning check
- Test

## Description

Every session loads the description of every skill, so each byte costs tokens on each request.

- Write what the skill does and when to use it, in the third person.
- Keep the description to 300 characters or fewer. Use 500 only if selection needs more.
- Give two or three trigger phrases. Do not list each variant of a phrase.
- If the user only starts the skill with `/name`, set `disable-model-invocation: true`. Claude Code then removes the description from the context.

## Body

Claude reads the body each time the skill runs.

- Write only what Claude does not know. Do not explain git, gh, semver, markdown, or standard libraries.
- Write each rule once. Put the hard rules (NEVER, ALWAYS) in one short block near the top.
- Do not add comments to commands that explain themselves, for example `git branch --show-current`.
- Give one default way to do a task. Add an alternative only for a real special case.
- Use one term for one thing in the whole skill.
- Keep the body under 300 lines. The hard limit is 500.

## Reference files

Claude reads a reference file only when a step tells it to.

- Move templates, command maps, config schemas, and long examples to reference files.
- Link each reference file from the step that uses it: "Read `templates.md` for the comment text."
- Link reference files only from `SKILL.md`. Claude can read only part of a file that a second file links to.
- If a reference file is longer than 100 lines, start it with a table of contents.
- If a step is deterministic, write a script. Only the script output uses tokens.
- If two skills share text, put it in one file and link it from both.

## Model choice

Set `model:` in the frontmatter from the type of work:

| Work | `model:` |
|---|---|
| Mechanical: run commands, fetch, post, format | `haiku` |
| Moderate: queries, summaries, tickets, test updates | `sonnet` |
| Judgement: design, review, investigation, specs | omit (the session model) |

- If you set `haiku`, write explicit steps. Haiku needs more detail than Opus.
- If a skill produces large tool output, set `context: fork`. The output then stays out of the main conversation.

## Output of the skill

Output tokens cost about five times as much as input tokens.

- Tell the skill to give the result first, with no preamble and no closing summary.
- Give an output template or an example. An example works better than a list of rules.
- Write what to do ("write one table"), not what not to do ("no long text").
- Do not set hard word limits. Anthropic measured a 3% quality loss in coding from hard word limits.

## Trim pass and meaning check

Use this pass to make an existing skill shorter.

1. Apply the rules in this file to each section.
2. Make a list of the facts in the original: each command, flag, condition, default, NEVER rule, ALWAYS rule, and checkpoint.
3. Find each fact in the new `SKILL.md` or in a linked reference file.
4. If a fact is missing, put it back.
5. Show the size before and after:

   ```bash
   wc -c <original> <proposed>
   ```

## Test

1. Write three test inputs before you change the skill.
2. Run the skill and save the outputs.
3. Change the skill, then run the same inputs again.
4. Compare the commands, the decisions, and the output format.
5. Test with each model that the `model:` field names.
