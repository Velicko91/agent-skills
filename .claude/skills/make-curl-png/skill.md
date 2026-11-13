---
name: make-curl-png
description: Runs curl requests against a local service, captures the requests and responses in a fixed-size Terminal.app window as a PNG, and attaches it to the PR after confirmation. Use for "curl screenshot", "PR verification proof", or "/make-curl-png".
user-invocable: true
allowed-tools: Bash(~/.claude/skills/make-curl-png/capture.sh *), Bash(TOKEN=* ~/.claude/skills/make-curl-png/capture.sh *), Bash(curl *), Bash(mkdir *), Bash(ls *), Bash(gh pr view *), Bash(gh pr edit *), Write, Read
model: sonnet
---

# Make Curl PNG

Run curl requests against a running service, and save a screenshot of the requests and responses as proof of testing for a PR.

## Hard rules

- NEVER run a request that changes data before the user confirms it (Step 2).
- NEVER send a request to a host other than `localhost`, `127.0.0.1`, or `[::1]` without the user's confirmation, because the screenshot proves nothing about a host the user did not choose.
- NEVER attach a screenshot to a PR without a yes in this conversation, even if a caller skill asked for it, because the whole team sees a PR description.
- ALWAYS use `capture.sh`. Do not write a new AppleScript, because the fixed window keeps every screenshot the same.
- ALWAYS show every command in full, exactly as it ran. NEVER run a filter, check, or step outside the screenshot and present its result as proof.
- Do not start or stop the service under test.
- Keep a screenshot to one or two requests. If the user gives more, propose several screenshots.
- ALWAYS put each UUID in a variable with a name that says what it is, for example `CARD_ID` or `FIELD_ID`, and use `"$CARD_ID"` in the commands. The variables show at the top of the screenshot, so a reader sees each ID once and knows what it is.
- NEVER write a token to a file. Pass it with `--secret TOKEN`, so the screenshot shows `TOKEN=<hidden>`.

## Prerequisites

- macOS with Terminal.app.
- The app that runs Claude Code has **Screen Recording** permission (System Settings → Privacy & Security → Screen & System Audio Recording). Without it, `screencapture` fails with "could not create image from window".
- The first run asks for permission to control Terminal.app. Allow it.
- The service under test runs already.
- `jq` is optional. With `jq`, a JSON response shows one top-level property per line, with colored keys.
- To attach to a PR: gh 2.103.0 or newer (`--attach`). With an older gh, the skill prints the file path.

## Arguments

```
/make-curl-png [--title "<text>"] [--name <test-case>] [--headers] [--depth 2] [--out <path>] [--pr <number|url>] [--no-attach] <curl command(s) or METHOD URL [body]>
```

| Argument | Default | Effect |
|---|---|---|
| curl commands | required | One or more full curl commands. A command can end in a short pipe, such as `\| jq '.data \| length'`. |
| `METHOD URL [body]` | — | A short form. The skill builds the curl command. |
| `--title "<text>"` | none | A header line in the screenshot, for example the ticket and the endpoint |
| `--headers` | hidden | Show the response headers. Use it only if the user asks, or the PR tests a header. |
| `--depth 2` | one level | Lay out two JSON levels, one property per line. Use it if the compared values are nested, for example `limits.daily`. |
| `--name <test-case>` | from Step 1 | The file name of the test case, for example `get-card-unknown-id-returns-404` |
| `--out <path>` | `/tmp/make-curl-png/<test-case>.png` | The full PNG path. Overrides `--name`. |
| `--pr <number\|url>` | the open PR of the current branch | The PR to attach to |
| `--no-attach` | offer to attach | Only save the PNG |

Fixed by `capture.sh`: the window is 3/4 of the main screen, top-left, with a dark theme. The title bar is cropped. The font is Menlo 12pt, reduced to 8pt if the output is too tall. The script uses its own profiles `make-curl-png` and `make-curl-png-alt`, and never changes the user's profiles. A `--secret` value appears as `<hidden>`. Every other value appears as typed.

## Nothing hidden

- Prefer one plain `curl` command for each request. The script lays out its response with one line for each top-level JSON property.
- Use a pipe only if the proof needs it, for example `curl ... | jq '.data | length'` to show a count. The screenshot shows the full command and the output of the pipe unchanged.
- Allow `curl` plus at most two pipe steps. NEVER use `;`, `&&`, `$(...)`, a redirect, or a script, because a reader cannot check them from the picture. A variable such as `"$CARD_ID"` is allowed.
- The commands run in a new Terminal shell with none of your environment variables. Only the variables of the requests file and the `--secret` values exist there.

## Variables

The requests file starts with one line for each variable, before the first command:

```
CARD_ID=6f1c2a3b-0000-4000-8000-000000000001
FIELD_ID=0b7e4d1c-0000-4000-8000-000000000002
curl -X DELETE "http://localhost:8080/v1/cards/$CARD_ID/fields/$FIELD_ID" -H "Authorization: Bearer $TOKEN"
```

- Write a variable line as `NAME=value` or `NAME='value'`. The name is upper case, and the value is literal, with no `$`, backtick, or `;`. `capture.sh` refuses any other line.
- Name a variable for what the ID is: `CARD_ID`, `TRANSACTION_ID`, `LINE_ID`, `OPTION_ID`. If two IDs have the same type, add what makes them different, for example `SOURCE_ACCOUNT_ID` and `TARGET_ACCOUNT_ID`.
- Put each UUID in a variable, also a UUID in a body or a query. Quote a body with `"` so the variable expands, for example `-d "{\"option_ids\":[\"$OPTION_ID\"]}"`.
- In a `jq` filter, pass the variable with `--arg`, because single quotes stop the shell from expanding it: `jq --arg id "$FIELD_ID" '[.fields[] | select(.field_id == $id)]'`.
- Pass the token in the environment of `capture.sh`, and name it with `--secret TOKEN`. The script gives it to the Terminal shell, and the screenshot shows `$ TOKEN=<hidden>` above the other variables. Use the same flag for each other secret, for example an API key.

## Prove a DELETE

A `204` from `DELETE` does not prove that the value is gone. The screenshot of a `DELETE` MUST show:

1. `GET` the resource — the value exists.
2. `DELETE` it.
3. `GET` the resource again — the value is gone.

- If the value does not exist yet, create it before the capture.
- If the `GET` response is too large, select the value with `jq`, for example `curl ... | jq --arg id "$FIELD_ID" '[.fields[] | select(.field_id == $id)]'`, which shows `[]` after the delete.
- If reads converge asynchronously and the second `GET` still shows the value, wait until it converges. Then capture the second `GET` in its own screenshot, and say why in the report.

## Workflow

### Step 1 — Build the request list

1. Parse the flags. The rest of the input is the requests.
2. Make each request one curl command on one line:
   - Join a command with `\` line continuations into one line.
   - Expand `METHOD URL [body]` to `curl -X METHOD 'URL'`. With a body, add `-H 'Content-Type: application/json' -d '<body>'`.
   - Remove `-i`, `-v`, `-o`, `-s`, `-w`, and `-D`, because they conflict with the flags of the script.
   - Replace each UUID with a variable, and add its line at the top, as "Variables" says. Use one variable for a UUID that occurs more than once.
   - Replace the token with `$TOKEN`, and keep its value only for the `--secret TOKEN` call in Step 3.
3. If a command does not start with `curl `, stop and show it to the user.
4. If a command has `;`, `&&`, `$(...)`, a redirect outside quotes, or more than two pipe steps, propose a simpler command or two commands. STOP and WAIT.
5. If a command is a `DELETE` without a `GET` before and after it, add the missing `GET`.
6. If a host is not in the allowed list, list it and ask for confirmation. STOP and WAIT.
7. Name the test case, unless `--name` or `--out` is given. The same test always writes the same file:
   - Describe what the screenshot proves: the method, the resource, the condition, and the expected result. Take it from `--title` if there is one.
   - Use only `a-z`, `0-9`, and `-`, with 60 characters or fewer.
   - Replace IDs with the word for what they are (`card_123` → `card`, a UUID → `transaction`), so a rerun with other data gets the same name.

   | Request | Test case name |
   |---------|----------------|
   | `GET /v1/cards/card_123` → 200 | `get-card-returns-200` |
   | `GET /v1/cards/unknown` → 404 | `get-card-unknown-id-returns-404` |
   | `PUT /v1/transactions/<uuid>/fields/<uuid>` without a scope | `put-transaction-field-missing-scope-returns-403` |
   | `curl .../cards \| jq '.data \| length'` | `list-cards-count` |

8. If `ls /tmp/make-curl-png/<test-case>.png` finds the file, tell the user that the new capture replaces it.

### Step 2 — Confirm requests that change data

If a request uses `POST`, `PUT`, `PATCH`, or `DELETE` (with `-X`, `--request`, or a `-d`/`--data` body), show the list and ask: "These requests change data. Run them? (yes / edit)". STOP and WAIT. If every request only reads, skip this step.

### Step 3 — Capture

1. If a command has a pipe, print it and explain each step in one line, in the order it runs:

   ```
   $ curl http://localhost:8080/v1/cards | jq '.data | length'

   1. curl http://localhost:8080/v1/cards - gets the card list
   2. jq '.data | length' - counts the items in the data array, so the screenshot shows the count
   ```

2. Write the variable lines, then the commands, to `/tmp/make-curl-png/<test-case>.requests`, one per line, exactly as they will appear. The file holds no token.
3. Run:

   ```bash
   TOKEN='<token>' ~/.claude/skills/make-curl-png/capture.sh \
     --requests /tmp/make-curl-png/<test-case>.requests \
     --out /tmp/make-curl-png/<test-case>.png \
     [--secret TOKEN] [--title "<text>"] [--headers] [--depth 2]
   ```

   Leave out `TOKEN=` and `--secret` if the requests send no token. The script keeps the token only for a moment, in a private file of its work folder, and deletes it before the first request runs.

   The script runs each command once and saves the results, so a redraw never repeats a request. It puts the user's app and window back in front, and captures from behind them, in about 3–4 seconds. If the output is too tall, it reduces the font. If the top still does not fit, it steps down from depth 2 to depth 1, then to the raw body.
4. Give each `NOTE:` line to the user, for example that the font was reduced or that the body is raw.
5. If the script prints `WARNING: output is N lines but the window shows M`, the top is cut off even in raw form. Tell the user, and offer fewer requests, or a short pipe that selects the part that the proof needs.
6. If the script fails with "could not create image", tell the user to grant Screen Recording permission and to restart the app that runs Claude Code.

### Step 4 — Report

1. Read the PNG with the Read tool, and check that it shows every request and its status line.
2. Report the status and time from the screenshot. For a piped command, write the full command:

```
📸 /tmp/make-curl-png/<test-case>.png
   file:///tmp/make-curl-png/<test-case>.png

| # | Request | Status | Time |
|---|---------|--------|------|
| 1 | GET /cards/card_123 | 200 | 12 ms |
```

### Step 5 — Attach to the PR (unless `--no-attach`)

1. Run `gh pr edit --help`. If its output has no `--attach`, print "Drag the file into the PR description - this gh version cannot upload images (update to 2.103.0 or newer)", and stop.
2. Find the PR: `gh pr view [<pr>] --json number,url,body`. If there is no PR, print the file path, and say that `gh pr create --attach '<png>#<alt>'` attaches it when the PR is created. Stop.
3. Write the alt text from the title and the first request, for example `PROJ-1234 - GET /v1/cards/{id} returns 200`.
4. Choose the place:
   - If the body has a verification section ("Manual verification", "Testing", "How to test"), write the new body to `/tmp/make-curl-png/<test-case>.body.md`, with `![<alt>](./<test-case>.png)` under that heading. The body file must be next to the PNG, because gh resolves the path from the folder of the body file.
   - Otherwise, append the image to the end, and write no body file.
5. Ask: "Attach `<test-case>.png` to PR #`<number>` (`<under "Manual verification" | at the end>`)? (yes / no)". STOP and WAIT.
6. Attach:

   ```bash
   # Under a verification section — gh uploads the file and rewrites ./<test-case>.png to the uploaded URL
   gh pr edit <number> --body-file /tmp/make-curl-png/<test-case>.body.md \
     --attach '/tmp/make-curl-png/<test-case>.png#<alt>'

   # At the end — with no body flag, gh keeps the body and appends the image
   gh pr edit <number> --attach '/tmp/make-curl-png/<test-case>.png#<alt>'
   ```

   One command attaches up to 50 files. Pass `--attach` once for each screenshot.
7. Check that `gh pr view <number> --json body -q .body` contains an uploaded image URL and no `./<test-case>.png`. If gh exits non-zero, report which attachments failed, and the PR URL that gh printed.
8. Report the PR URL.

## Examples

- `/make-curl-png curl http://localhost:8080/v1/cards/card_123 -H 'Authorization: Bearer sandbox-token'` ← the screenshot shows `TOKEN=<hidden>`, and the command uses `$TOKEN`
- `/make-curl-png --title "PROJ-1234 - create a card" POST http://localhost:8080/v1/cards {"name":"Travel"}`
- `/make-curl-png curl http://127.0.0.1:8080/v1/cards | jq '.data | length'`
- `/make-curl-png --pr 123 --title "PROJ-1234 - get a card" curl http://localhost:8080/v1/cards/card_123`

## Retry

Say **"retry"** to capture again. Read the request list from the latest message, and run Steps 1–5 again. The new PNG replaces the old one, because the test case name stays the same.
