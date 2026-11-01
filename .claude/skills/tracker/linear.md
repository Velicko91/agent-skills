# Linear adapter

## Config

| Key in `~/.claude/config.local.json` | Use |
|---|---|
| `linear.workspace` | The slug in `https://linear.app/<workspace>` |
| `linear.teams` | Team routes: `[{"key": "PROJ", "repos": [...], "topics": [...]}]` |
| `linear.team` | The fallback team key, if no route matches. It can be empty. |

NEVER guess the workspace or a team. If a value is missing, ask the user, and add it to the config.

**Choose the team for a new ticket**, in this order:
1. `--team`, if given.
2. The first route whose `repos` holds the repository of the work. The repository is the last part of `git remote get-url origin`, without `.git`, or the repository that the bullets name.
3. The first route whose `topics` match the work.
4. `linear.team`, if it is not empty.
5. Otherwise, ask the user, and list the keys of the routes. STOP and WAIT.

Say which rule chose the team in the output, for example `Team: PROJ (repo acme-api)`.

## Identify

- ID: `[A-Z]+-[0-9]+`, for example `PROJ-1234`. The prefix is the team key.
- URL: `https://linear.app/<workspace>/issue/<ID>/<slug>`. The ID is the segment after `/issue/`.
- Ticket link: `https://linear.app/<workspace>/issue/<ID>`
- Ignore `gitBranchName`, because it starts with a username.

## Tools

| Operation | Tool | Notes |
|---|---|---|
| Fetch | `mcp__linear__get_issue` | `id` = the ID. Add `includeRelations: true` if a parent or a blocker matters. |
| Create | `mcp__linear__save_issue` | No `id`. `team` and `title` are required. |
| Update (state, assignee, relations) | `mcp__linear__save_issue` | With `id` |
| States of a team | `mcp__linear__list_issue_statuses` | `team` = name or ID |
| Teams | `mcp__linear__list_teams` | Gives the team UUID |
| Labels | `mcp__linear__list_issue_labels`, `mcp__linear__create_issue_label` | |
| Cycles | `mcp__linear__list_cycles` | `teamId` must be the team **UUID** from `list_teams`, not the key. `type: "current"` gives the active cycle. |
| Users, projects | `mcp__linear__list_users`, `mcp__linear__list_projects` | |
| Comment | `mcp__linear__save_comment` | `issueId` + `body` |

## Create

```json
{
  "team": "<the team from \"Choose the team\">",
  "title": "...",
  "description": "...",
  "state": "Backlog",
  "labels": ["Back-End"],
  "priority": 3,
  "cycle": "<cycle id, name, or number>",
  "parentId": "PROJ-1000",
  "project": "<name or id>",
  "milestone": "<name or id>",
  "estimate": 3,
  "assignee": "me"
}
```

- ALWAYS pass `state`. Linear puts an issue with no state in Triage. The default is `Backlog`.
- Send only the keys that apply. Linear uses its default for an absent key.
- Priority: `0` none, `1` urgent, `2` high, `3` medium, `4` low.
- Linear has no issue type. Use labels and projects instead.
- To link sibling issues, update the first one with `relatedTo: [<other IDs>]`.
- Concepts: a cycle is a sprint of one team; a project groups issues across teams; `parentId` makes a sub-issue.

## States

| Move to | How |
|---|---|
| Started (claim) | `save_issue` with `id`, `assignee: "me"`, and `state: "In Progress"`. If the team has no state with that name, run `list_issue_statuses`, and take the `started` state whose name contains "progress". Do not pass the type `started`, because a team can have several started states (for example In Progress, In Testing, In Review), and Linear can pick the wrong one. |
| Review | `list_issue_statuses` for the team. Take the first match: `In Review`, then `Ready for Review`, then any name that contains "review" (case-insensitive). Then `save_issue` with that name. If none matches, leave the state, and report it. |
| Done | `list_issue_statuses` for the team. Take the `completed` state named `Done`, else the only `completed` state. Then `save_issue` with that name. If there are several and none is `Done`, ask the user which one. |

## Rules

- Pass Markdown with real newlines, never `\n` escape sequences.
- Check `list_issue_labels` before you add a label. Create a label only if no close match exists.
- Linear links a GitHub PR to an issue when the ID is in the PR title, the branch, or the body.
