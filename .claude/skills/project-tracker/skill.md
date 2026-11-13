---
name: project-tracker
description: Drafts the weekly Linear status update of each open project that you lead, from its issues, milestones, and the work log, aligns each draft with you, posts it, and goes to the next project. Use for "/project-tracker", "weekly project update", or "summarize my projects".
user-invocable: true
model: sonnet
allowed-tools: mcp__linear__whoami, mcp__linear__list_projects, mcp__linear__get_project, mcp__linear__list_issues, mcp__linear__list_milestones, mcp__linear__get_status_updates, mcp__linear__save_status_update, Bash(~/.claude/skills/work-log/worklog.py *), Bash(cmux notify *), Bash(~/.claude/skills/project-tracker/setup.py), Read
---

# Project Tracker

Write one Linear status update for each open project that the user leads. Show each draft, change it until the user agrees, post it, then go to the next project.

## Hard rules

- NEVER post a status update before the user approves that draft. The approval of one project is not the approval of the next one.
- NEVER post to a project that the user does not lead.
- NEVER write a fact that the issues, the milestones, or the work log do not show. A wrong status update misleads every reader of the project.
- NEVER change an issue, a milestone, a project, or the work log. This skill writes only status updates and its own `data.json`.
- NEVER add a project to `data.json` before the user confirms it, because a project that the user leads can be one that they do not report on.
- Show one project at a time, and give the result first: the draft, then the facts behind it.

## Arguments

| Argument | Effect |
|---|---|
| *(none)* | Every project in `data.json`, in order |
| `--project <name or id>` | Only this project. It must be in `data.json`. |
| `--refresh` | Run Phase 1 only: read the projects that you lead again, update `data.json`, and stop |
| `--dry-run` | Draft and align, but post nothing |
| `setup` | Run `setup.py`, which adds or updates the weekly job in the loops daemon, and stop |

## Local configuration

Read `data.json` in this skill directory. If it is missing, copy `data.example.json` to `data.json`, set `projects` to `[]`, and run Phase 1.

| Key | Default | Use |
|---|---|---|
| `schedule.cron` | `0 10 * * 3` | When the daemon starts the run: five cron fields in local time. `setup.py` writes it into the loops job. |
| `schedule.tz` | the Mac's time zone | The time zone of `schedule.cron` |
| `lookbackDays` | `7` | The window of a project with no status update yet |
| `closeToFinish.milestonePercent` | `75` | A milestone above this percentage is close to finish |
| `closeToFinish.targetDays` | `14` | A target date in this many days is close |
| `loops.dir` | none | The folder of `loops.json`. `setup.py` stops if it is empty. |
| `loops.settingsDir` | `~/.config/cmux/loops` | Where `setup.py` writes the permissions of the session |
| `loops.model` | `sonnet` | The model of the weekly session |
| `projects` | `[]` | The projects to report on, as `{id, name}`, in order |
| `declined` | `[]` | The ids of projects that the user does not want in `projects` |

Edit `data.json` with Read and Write. Change only `projects` and `declined`.

## Setup

Run `~/.claude/skills/project-tracker/setup.py`. It writes the permissions of the session, adds the job to `loops.json`, and runs `loops.py --check`. The job runs `/project-tracker` in its own session (`session: "new"`), with `restart_after_hours: 0`, so the session does not close during a review. Run it again after you change `schedule` or `loops`.

## Workflow

### Phase 1 — Find the projects

1. Get the user id with `mcp__linear__whoami`.
2. Run `mcp__linear__list_projects` with `member: "me"` and the fields `name`, `url`, `lead`, `status`, `targetDate`. Keep each project whose `lead.id` is the user id and whose `status.type` is not `completed` or `canceled`.
3. Compare the result with `data.json`:
   - A project that is not in `projects` or `declined` is new.
   - A project in `projects` that is not in the result is closed, or has a new lead.
4. If there is a new or a closed project, ask once, in one message: "Add <new projects>? Remove <closed projects>?" STOP and WAIT. Add each confirmed project to `projects`, and add each refused one to `declined`. Remove each closed project that the user confirms.
5. With `--refresh`, show the list in `data.json`, and stop.

### Phase 2 — Collect the facts of one project

Do this for the next project in `projects`, or for `--project` only.

1. Get the last update: `mcp__linear__get_status_updates` with `type: "project"`, `project: <id>`, `orderBy: "createdAt"`, `limit: 1`. The window starts at its `createdAt`. If there is none, the window starts `lookbackDays` days ago.
2. Get the issues that changed in the window: `mcp__linear__list_issues` with `project: <id>`, `updatedAt: <window start>`, `limit: 250`, and the fields `title`, `status`, `statusType`, `assignee`, `completedAt`, `projectMilestone`, `url`.
3. Get the open issues: `mcp__linear__list_issues` with `project: <id>`, `state: "started"`, and the same fields.
4. Get the milestones with `mcp__linear__list_milestones`, and the target date with `mcp__linear__get_project`.
5. For each issue that was finished in the window, read its work log entry: `~/.claude/skills/work-log/worklog.py list --key <issue key>`. Use it to tell `merged` from `in production`. If there is no entry, say only what the issue status says.
6. If the project status is `backlog`, and no issue changed in the window, skip the project. Add it to the skipped list, and go to the next project.

### Phase 3 — Draft the update

Read `update-template.md` in this skill directory, and write the body in that form.

Sort the facts into three groups:

| Group | Issues |
|---|---|
| Done | Finished in the window: `statusType` is `completed` |
| Close to finish | In review or merged, a milestone above `closeToFinish.milestonePercent`, or all open work of a milestone in review |
| Next | All other open issues |

Propose the health, and give the reason in one sentence:

| Health | When |
|---|---|
| `offTrack` | The target date is in the past, and the project is not finished |
| `atRisk` | There is a blocker, or the target date is in `closeToFinish.targetDays` days and more than half of the issues are open |
| `onTrack` | All other cases |

Show the project like this:

````
## <n>/<total> — <project name>   Health: <onTrack | atRisk | offTrack> — <reason>

<the draft body>

**Facts** (since <window start>)
| Group | Issue | Status | Assignee |
|---|---|---|---|
| Done | <title> | <status> | <name> |
| Close to finish | <title> | <status> | <name> |
| Target date | <date> · <n> of <n> issues open |
````

After the first draft of the run, notify the user, because the daemon opens the session when nobody watches it:

```bash
cmux notify --workspace "$CMUX_WORKSPACE_ID" --title "project-tracker" --body "<project name>: the draft is ready"
```

If `CMUX_WORKSPACE_ID` is empty, run it with no `--workspace`.

# --- CHECKPOINT ---
Ask: "Post it, tell me what to change, `skip`, or `stop`?" STOP and WAIT.

- **A change:** apply it, show the draft again, and ask again.
- **`skip`:** post nothing, add the project to the skipped list, and go to Phase 2 for the next project.
- **`stop`:** go to Phase 5.

### Phase 4 — Post

1. Post with `mcp__linear__save_status_update`: `type: "project"`, `project: <id>`, `body: <the approved draft>`, `health: <the approved health>`. With `--dry-run`, post nothing, and say "dry run: not posted".
2. Show the url of the update.
3. Go to Phase 2 for the next project.

### Phase 5 — Report

```
## Project updates — <date>

| Project | Health | Result |
|---|---|---|
| <name> | onTrack | Posted: <url> |
| <name> | — | Skipped: backlog, no change since <date> |
```

## Examples

- `/project-tracker`
- `/project-tracker --project "Acme API: Webhook retries"`
- `/project-tracker --dry-run`
- `/project-tracker --refresh`
- `/project-tracker setup`

## Retry

If the user says "retry", use no fact from earlier in the session. Read `data.json`, the status updates, the issues, and the work log again, and start at Phase 1.
