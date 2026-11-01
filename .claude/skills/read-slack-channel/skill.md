---
name: read-slack-channel
description: Reads Slack channels and DMs, with all thread replies, and answers a question from that conversation with a cited permalink for each claim. Read-only. Use for "what was decided about X in #channel", "summarize the Slack thread on …", or "/read-slack-channel".
user-invocable: true
allowed-tools: mcp__plugin_slack_slack__slack_read_channel, mcp__plugin_slack_slack__slack_read_thread, mcp__plugin_slack_slack__slack_search_channels, mcp__plugin_slack_slack__slack_search_users, mcp__plugin_slack_slack__slack_search_public, mcp__plugin_slack_slack__slack_search_public_and_private, mcp__plugin_slack_slack__slack_read_user_profile, mcp__plugin_slack_slack__slack_list_channel_members, Read, Write, Bash(date *)
model: sonnet
---

# Read Slack Channel

Read Slack channels and DMs, with every thread reply, and answer a question from that conversation. Cite a Slack permalink for each claim, so the reader can check it. A user or another skill can start it.

## Hard rules

- NEVER post or react in Slack. This skill is read-only; the write tools are not in `allowed-tools`.
- Expand threads unless `--no-threads` is given, because most decisions happen in threads.
- Cite every claim. If a claim has no Slack source, do not make it. If the messages do not answer the question, say so.
- Show disagreement. Do not flatten competing answers into one.
- If a target is ambiguous (for example two channels with the same name), STOP and ask which one.
- Do not copy DM content into unrelated outputs without the user's explicit approval.
- If another skill started this skill, return only the Phase 5 output, with no text before or after it.

## Arguments

```
/read-slack-channel "<question>" [--in <targets>] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--no-threads] [--max-msgs N]
```

| Argument | Default | Meaning |
|---|---|---|
| `<question>` | required | The question. Everything before the first `--` flag. |
| `--in <targets>` | required | Comma-separated: `#name`, a raw ID (`C…`, `D…`, `G…`), `@user`, or a permalink (`https://<workspace>.slack.com/archives/<ID>[/p<ts>]`). If absent, use the `#channel`, `@user`, and permalinks in the question, and remove them from it. |
| `--from` | 30 days ago, 00:00 UTC | Start date, inclusive |
| `--to` | now | End date, inclusive. If `from` is after `to`, swap them, and say so in the footer. |
| `--no-threads` | expand | Skip the thread replies |
| `--max-msgs N` | `500` per target | The volume limit for the guard in Phase 2 |

Use the defaults with no confirmation.

## Workflow

### Phase 1 — Resolve the targets

1. Compute the window: `date -u -v-30d +%Y-%m-%dT00:00:00Z` for the default `from`. Convert `from` and `to` to Unix epoch seconds for `oldest` and `latest`.
2. Resolve each target to an ID:
   - Raw ID: use it as it is.
   - Permalink: take the `<ID>`. If it has `p<ts>`, keep it as a thread anchor for Phase 3.
   - `#name`: `slack_search_channels` with `keywords: ["<name>"]`, `natural_language_query: ""`, and `channel_types: "public_channel,private_channel"`. Take the exact name match.
   - `@user`: `slack_search_users` with the name as `keywords`. Use the user ID as the `channel_id` of the DM; `slack_read_channel` accepts it.
   - If a target cannot be resolved, list it, and STOP.
3. Show the result, and continue:
   ```
   Resolved targets:
     #eng-backend  → C0123ABC
     @alice        → U045XYZ (DM)
   Date window: 2026-04-20 → 2026-05-20 (30 days)
   Threads: expanded
   ```

### Phase 2 — Volume guard

Read the first page of each target: `slack_read_channel` with `oldest`, `latest`, and `limit: 100`. Estimate the number of parent messages from the pages and `next_cursor`.

If the total is above `--max-msgs`, STOP and ask:

```
⚠️  Large scan: ~<N> parent messages across <K> target(s) in the last <D> days.
    With threads expanded, this could mean several thousand messages.

    Options:
      1. Proceed as-is
      2. Narrow the date range (suggest: last 7 days)
      3. Drop a target (list them)
      4. Disable thread expansion (--no-threads)
```

WAIT, because a large scan costs many tokens and much time. Otherwise, continue.

### Phase 3 — Read the messages

For each target:

1. Read `slack_read_channel` with `oldest`, `latest`, and `limit: 100`, and follow `next_cursor` until there are no more pages, or `--max-msgs` is reached.
2. For each parent message with replies, unless `--no-threads`: `slack_read_thread` with the `channel_id` and the parent `ts` as `message_ts`.
3. For a thread anchor from a permalink, also read that thread, because it can be outside the window.
4. Resolve user IDs to names with `slack_read_user_profile`, only for the IDs in the messages, with a cache.

For each message, keep the channel ID and name, `ts` (and `thread_ts` for a reply), the user name, the text (with `<@U…>` mentions replaced by names, and links kept), and the permalink: the one in the response, else `https://<workspace>.slack.com/archives/<channel_id>/p<ts without the dot>`.

### Phase 4 — Answer

Read all the messages, and write a direct answer in prose. Mark each claim with `[N]`, and map each marker to a message in the sources list.

### Phase 5 — Output

```
## Answer

<2–6 sentences of prose answering the question, with inline [N] citations.>

### Sources

[1] #eng-backend · @alice · 2026-05-12
    "<one-line excerpt>"
    <permalink>

[2] @bob (DM) · 2026-05-14
    "<one-line excerpt>"
    <permalink>

---
Scan: <K> targets · <D> day window · <N> parent msgs · <M> thread replies · ~<T>s
```

With `--no-threads`, add that to the footer.

## Examples

- `/read-slack-channel "What did we decide about the new ledger schema?" --in #eng-backend`
- `/read-slack-channel "Summarize Alice's questions about the migration" --in @alice --from 2026-05-01`
- `/read-slack-channel "Status of the Q2 onboarding redesign" --in #design,#eng-backend --from 2026-04-01 --to 2026-05-15`
- `/read-slack-channel "What's the latest on last Thursday's incident?" --in https://<workspace>.slack.com/archives/C0123ABC`

Callers such as `/investigate-incident` and `/implement-ticket` pass a full argument string and do the further synthesis themselves.

## Retry

If the user says "retry", reuse no resolved target and no message data. Resolve the targets and read every page again.
