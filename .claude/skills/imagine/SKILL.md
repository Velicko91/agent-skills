---
name: imagine
description: Generates an image through OpenRouter and saves the PNG — writes a strong prompt first (asking what it needs) when the request is vague or is a diagram of code. Use for "/imagine <description>", "make an image of …", or "draw a diagram of this code".
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash(~/.claude/skills/imagine/imagine.py *)
---

# Imagine

Generate an image through the OpenRouter Image API, and save it as a PNG. If the request is not a finished prompt, write the prompt first with `prompt-guide.md`.

## Hard rules

- ALWAYS generate with `imagine.py`, and pass the prompt on **stdin** with a quoted heredoc. NEVER put the prompt into a command line or into code, because quotes and backslashes in it would break the command or run as code.
- NEVER print `OPENROUTER_API_KEY`.
- Put only what the image needs in a prompt. Do not paste code, secrets, or customer data into it, because the prompt leaves the machine.
- If you ask questions, ask them all in one message.

## Arguments

```
/imagine <description or prompt> [--size 1024x1024|1536x1024|1024x1536] [--quality low|medium|high] [--model <id>] [save to <path.png>]
```

| Argument | Default | Meaning |
|---|---|---|
| description | required | A finished prompt, or what the image should show |
| `--size` | `1024x1024` | Square, landscape (`1536x1024`), or portrait (`1024x1536`) |
| `--quality` | `medium` | `high` for complex or text-heavy diagrams. Used by `openai/*` models only. |
| `--model` | `google/gemini-3.1-flash-image` | An OpenRouter image model, for example `openai/gpt-image-1`. List them with `curl -s https://openrouter.ai/api/v1/images/models`. |
| `save to <path.png>` | `~/Downloads/<slug>-<time>.png` | The output file |

## Workflow

### Step 1 — Decide whether to write the prompt

- **A finished prompt** (it names the style, the subject, the layout, and the constraints): go to Step 3.
- **A vague request, or "a diagram of this code":** go to Step 2.

### Step 2 — Write the prompt

1. Read `prompt-guide.md` in this skill directory.
2. For a diagram of code, read the code with Grep, Glob, and Read, and take the components and their relations. Put names in the prompt, never code.
3. If the guide's questions (goal, audience, style, detail, colors, format) are not answered by the request, ask them in one message. STOP and WAIT. If most are answered, continue.
4. Write the prompt with the structure and rules of the guide, and choose `--size` and `--quality`.
5. Show the prompt and the settings, and ask: "Generate it, or adjust the prompt?" STOP and WAIT. If the user asked for options, show 2–3 variants with short labels.

### Step 3 — Generate

```bash
~/.claude/skills/imagine/imagine.py --size <size> --quality <quality> [--model <id>] [--out <path.png>] <<'PROMPT'
<the prompt, exactly as written>
PROMPT
```

### Step 4 — Report

Report the saved path, the cost, and the revised prompt if the script prints one. If the script prints an error:

| Error | Action |
|---|---|
| `OPENROUTER_API_KEY is not set` | Tell the user to set it in the shell profile. |
| `402` or "no credits" | Tell the user that the account or, for `openai/*`, the OpenAI key linked to OpenRouter has no credit. Offer the default Google model. |
| `400` about the size | Retry with another `--size`, or another model. |

## Examples

- `/imagine flat vector icon of a blue database cylinder labeled "db", white background, no watermark`
- `/imagine a diagram of how the order service publishes events` ← writes the prompt first
- `/imagine --size 1536x1024 --quality high --model openai/gpt-image-1 <finished prompt>`
- `/imagine a cat reading a newspaper save to ~/Desktop/cat.png`
