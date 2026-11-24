---
name: steward
description: Watches a pushed pull request until it merges or closes. It fixes failing CI, and runs /fix-pr-comments for new review comments. It polls every minute while work happens, then backs off to ten minutes when idle. Use for "/steward", "watch my PR", or after a push.
disable-model-invocation: true
allowed-tools: "*"
---

# Steward

Watch one pull request in the background. React to failing CI and to new review comments. Stop when the PR merges or closes. The user can keep working with the agent while this runs.

## Hard rules

- Act without the user only when both are true: no decision belongs to the user, and the issue is real with a clear cause and fix. If the cause is unclear, the fix is a judgement call, or the change could affect behaviour or design, send a PushNotification and wait. Do not guess.
- NEVER block the conversation. Each tick acts, re-arms the next tick, then ends the turn.
- On an idle tick with no event, end the turn with no text, so the terminal stays clean.
- Edit only files under the PR worktree. If the branch is not checked out here, do not fix. Send a PushNotification and keep watching.
- NEVER force-push. Add a new commit. Push only the PR branch.
- Fix a failing check only when its cause is in the diff of this branch. For an unrelated or infrastructure failure, send a PushNotification and keep watching.
- Give comment work to `/fix-pr-comments --unattended`. It alone judges and replies. Do not post comments from this skill.
- A design or architecture decision is the user's. `/fix-pr-comments` leaves it unchanged; steward sends a PushNotification for it.
- Run one tick job per PR. Before you arm a new job, delete the old one by its stored id.
- The cron job lives only in this session. It stops when the session ends. Tell the user this at the start.

## Arguments

| Form | Effect |
|---|---|
| `/steward` | Watch the open PR of the current branch. |
| `/steward <number \| url>` | Watch that PR. |
| `/steward stop [<number>]` | Stop watching. Default: the PR of the current branch. |
| `/steward --tick <key>` | One watch cycle. The cron job calls this. Not for a person. |

Flags: `--min <1>` base minutes, `--max <10>` cap.

## Defaults

| Field | Default | Override |
|---|---|---|
| base interval | 1 minute | `--min` |
| cap interval | 10 minutes | `--max` |

## State

Keep one file per PR at `~/.claude/steward/<key>.json`. `<key>` is `<owner>-<repo>-<number>`.

Fields: `pr`, `repo` (owner/name), `branch`, `worktree`, `interval`, `min`, `max`, `headSha`, `checksSig`, `lastCommentId`, `jobId`, `since`.

## Workflow

### Phase A — Start

Run on `/steward` or `/steward <pr>`.

1. Resolve the PR and repo:
   ```bash
   gh pr view <pr-or-blank> --json number,state,headRefName,headRefOid,url,statusCheckRollup
   gh repo view --json nameWithOwner -q .nameWithOwner
   git rev-parse --show-toplevel
   ```
   The worktree is the toplevel path. If there is no open PR, tell the user and stop.
2. If a state file for this key exists and its `jobId` is still armed, say steward already watches this PR, and stop.
3. Read the current signals, as "Signals" says: `headSha`, `checksSig`, `lastCommentId`.
4. Write the state file with `interval = min`.
5. Arm the first tick, as "Backoff" says, with the base interval.
6. Print one line: `👁  Watching <pr> every <min>m, backing off to <max>m. Stop with /steward stop <number>.` Say the job lives only in this session.

### Phase B — Tick

Run on `/steward --tick <key>`. Read the state file first.

1. Read the PR state:
   ```bash
   gh pr view <number> --json state,mergeStateStatus,headRefOid,statusCheckRollup
   ```
2. If `state` is `MERGED` or `CLOSED`:
   - Send a PushNotification: `<repo> #<number> <merged|closed>`.
   - Delete the state file. Do not arm a new job. Stop.
3. Read the current signals (Signals). An event is any of:
   - a check failed (the failed count is more than 0),
   - a check is pending or running,
   - `headSha` changed,
   - `checksSig` changed,
   - a new review comment (the new comment id is more than `lastCommentId`).
4. Act on each event:
   - **A check failed:** read the failing job with `gh run view <id> --log-failed`. Fix it yourself only when the cause is in this branch, the cause is clear, and the fix needs no decision: edit the worktree, run the affected tests with the repo's test command, commit the fix as its own commit, and push with `~/.claude/skills/safe-push/push.sh`. In every other case, for example an unrelated or infrastructure failure, an unclear cause, or a fix that changes behaviour, send a PushNotification and do nothing else.
   - **A new review comment:** run `/fix-pr-comments --unattended <number>`. After it ends, read the new `lastCommentId` across all comments, including the replies it posted, and store it, so its own replies do not start another run. If its summary lists any item that needs a user decision, send a PushNotification: `<repo> #<number>: review needs your decision`.
   - **Only pending, running, or a new commit:** take no action.
5. Store the new signals in the state file.
6. Set the next interval: if any event happened this tick, `interval = min`; otherwise `interval = min(interval * 2, max)`.
7. Arm the next tick (Backoff). Store the new `jobId`.
8. If the tick acted, print one line that names what it did. Otherwise end with no text.

### Phase C — Stop

Run on `/steward stop [<number>]`.

1. Resolve the key. Read the state file.
2. Delete the job: `CronDelete` with the stored `jobId`.
3. Remove the state file.
4. Print one line: `🛑 Stopped watching <pr>.`

## Signals

Read these from the PR, and store them in the state file:

- Head commit: the `headRefOid` field.
- Checks signature and counts:
  ```bash
  gh pr view <number> --json statusCheckRollup \
    --jq '[.statusCheckRollup[] | "\(.name):\(.status // .state):\(.conclusion // "")"] | sort | join(",")'
  ```
  Failed count: the checks whose `conclusion` or `state` matches `FAILURE|TIMED_OUT|CANCELLED|ACTION_REQUIRED|STARTUP_FAILURE|ERROR`. Pending count: those that match `QUEUED|IN_PROGRESS|PENDING|WAITING`.
- Newest review comment not from you:
  ```bash
  ME=$(gh api user --jq .login)
  gh api "repos/<repo>/pulls/<number>/comments" --paginate \
    --jq "map(select(.user.login!=\"$ME\")) | map(.id) | max // 0"
  gh api "repos/<repo>/issues/<number>/comments" --paginate \
    --jq "map(select(.user.login!=\"$ME\")) | map(.id) | max // 0"
  ```
  Use the larger of the two ids.

## Backoff

Arm the next tick as a one-shot cron job, so only one tick is pending and the interval can change:

1. Delete the old job with `CronDelete` if one is armed.
2. Compute the fire time, `<N>` minutes from now (macOS `date`):
   ```bash
   date -v+<N>M +'%M %H %d %m'
   ```
3. Call `CronCreate` with `recurring: false`, `cron` set to `<minute> <hour> <dom> <month> *`, and `prompt` set to `/steward --tick <key>`.
4. Store the returned job id in `jobId`.

The idle interval doubles each tick: 1, 2, 4, 8, then the 10 minute cap. An event resets it to the base.

## Examples

- `/steward` — watch the current branch's PR.
- `/steward 1234` — watch PR 1234.
- `/steward --max 15 https://github.com/acme/widgets/pull/1234` — watch, cap at 15 minutes.
- `/steward stop 1234` — stop watching PR 1234.

## Retry

Say **"retry"** to restart the watch. Stop the current job first (Phase C), then start again (Phase A) with fresh signals.
