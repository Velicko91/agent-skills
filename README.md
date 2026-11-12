# agent-skills

Skills and subagents for [Claude Code](https://claude.com/claude-code). They cover the full development loop: ticket, plan, code, test, review, pull request, and incident work.

## Setup

1. Clone the repository.

   ```bash
   git clone git@github.com:Velicko91/agent-skills.git ~/code/agent-skills
   export CLAUDE_CONFIG_REPO="$HOME/code/agent-skills"
   ```

2. Link each skill and the agents into `~/.claude`.

   ```bash
   mkdir -p ~/.claude/skills
   for s in "$CLAUDE_CONFIG_REPO"/.claude/skills/*/; do ln -sfn "${s%/}" ~/.claude/skills/; done
   ln -sfn "$CLAUDE_CONFIG_REPO/.claude/agents" ~/.claude/agents
   ln -sfn "$CLAUDE_CONFIG_REPO/.claude/CLAUDE.md" ~/.claude/CLAUDE.md   # optional: global writing rules
   ```

3. Copy the templates and fill in your values.

   ```bash
   cp .claude/config.example.json .claude/config.local.json
   cp .claude/settings.example.json .claude/settings.json
   ```

## Configuration

The skills never hardcode organization names, hosts, or IDs. They read them from local files that git ignores:

| File | Holds | Template |
|---|---|---|
| `.claude/config.local.json` | Tracker, repositories, GCP projects | `.claude/config.example.json` |
| `.claude/skills/review-dependabot-pr/config.local.json` | Repo policy, internal GitHub orgs and package hosts | `.claude/skills/review-dependabot-pr/config.example.json` |
| `.claude/settings.json` | Claude Code permissions and hooks | `.claude/settings.example.json` |
| `skills/<skill>/data.json` | Per-skill state and service lists | `data.example.json` in the skill |
| `skills/<skill>/**/*.local.md` | Per-service rules and test data | `TEMPLATE.example.md` in the skill |

Keep passwords in the macOS Keychain or in your secret manager, never in these files.

## Skills

### Tickets and planning

| Skill | What it does |
|---|---|
| `create-ticket` | Turns bullets into a ticket in the tracker, with the reason, the issue, and the acceptance criteria. |
| `plan` | Builds a checkbox task plan from a ticket, an optional Notion document, and the real code. |
| `drill-me` | Researches a problem, then asks design questions round by round, and writes an alignment document. |
| `create-worktree` | Creates a git worktree with a named branch for a ticket or a free-text task. |
| `tracker` | Issue-tracker adapters (Linear today) that the ticket skills read. |

### Implementation

| Skill | What it does |
|---|---|
| `implement-ticket` | Explores the code, writes a reviewed plan, waits for approval, implements, tests, and follows the ticket to production. |
| `solve-ticket` | Claims a ticket, runs `implement-ticket`, tests, lints, opens the PR, and moves the ticket to review. |
| `dev-loop` | Runs ticket, worktree, implementation, then review, test, and fix until both pass, then opens a PR. |
| `update-tests` | Fixes failing Python tests and writes the missing tests for a change. |
| `lint` | Runs the formatter and the linter, and fixes what they report. |
| `work-log` | Keeps the log of open work: branches, PRs, and sessions. |
| `open-claude-session` | Opens a new, resumed, or forked Claude Code session from the work log in a cmux workspace. |

### Testing

| Skill | What it does |
|---|---|
| `docker-test` | Starts and tests the local Docker stack with per-service rules and mandatory test cases. |
| `test-on-dev` | Tests a service on the dev environment through MCP, REST, GraphQL, or gRPC, and reports evidence. |
| `make-curl-png` | Captures curl requests and responses as a PNG and attaches it to the PR. |
| `verify-stamp` | Records a hash of the working tree after a test run, so later steps skip a repeat run. |

### Pull requests and review

| Skill | What it does |
|---|---|
| `create-pr` | Reviews the diff, runs lint and tests, opens a draft PR, and requests the Copilot review. |
| `review-code` | Reviews staged changes or a branch, applies small fixes, and reports what needs a decision. |
| `github-review` | Reviews a PR in a worktree and posts each finding as an inline comment. |
| `fix-pr-comments` | Checks each unresolved review comment, fixes the real ones, and replies to all. |
| `sweep-pr-comments` | Finds new review comments on open PRs, fixes the simple ones, and escalates the hard ones. Built for cron. |
| `post-pr-comment` | Posts one comment on a PR. |
| `list-my-prs` | Lists your open PRs and the PRs that wait for your review. |
| `safe-push` | Pushes a branch only after it pulls new commits and finds no conflict with the base branch. |

### Dependencies

| Skill | What it does |
|---|---|
| `review-dependabot-pr` | Reviews one dependabot PR in depth, repairs it so it can merge, and posts one comment. |
| `approve-and-merge-chore-prs` | Approves and queues the dependabot PRs after one confirmation. |

### Data and operations

| Skill | What it does |
|---|---|
| `query-db` | Runs one read-only SQL query on a configured Postgres database and returns a table. |
| `query-snowflake` | Runs one read-only SQL query on Snowflake and returns a table. |
| `get-gcloud-logs` | Fetches GKE logs for a configured service and can extract fields to CSV. |
| `investigate-incident` | Investigates an incident from a file of past causes, ranks causes, and records the solved cause. |
| `read-slack-channel` | Reads Slack channels and threads, and answers a question with a permalink for each claim. |

### Documentation

| Skill | What it does |
|---|---|
| `docs` | Writes technical documentation for a part of the codebase through interactive exploration. |
| `diagram` | Draws one Mermaid diagram from code or a description, and saves it as Markdown. |
| `document-flow` | Traces a flow across services and writes an Obsidian page with Mermaid sequence diagrams. |
| `define-ubiquitous-language` | Finds the domain vocabulary of a repository and writes a glossary. |
| `create-notion-tech-spec` | Turns bullets into a tech spec and publishes it as a private Notion page. |
| `review-techspec` | Reviews a Notion tech spec and adds each finding as a comment on the exact text. |
| `improve-techspec` | Improves the wording and structure of a Notion tech spec in a copy. |
| `notion-document` | Expands bullets from a local page or file into a Notion document. |
| `write-obsidian-page` | Turns text, a file, or a URL into an atomic Obsidian note with links. |
| `dnote` | Searches, adds, edits, and removes notes in the dnote notebook. |

### Media

| Skill | What it does |
|---|---|
| `imagine` | Generates an image through OpenRouter and saves the PNG. |
| `slidev` | Creates and runs developer slide decks with Slidev. |

### Skill authoring

| Skill | What it does |
|---|---|
| `create-skill` | Scaffolds a new skill and creates its symlink. |
| `update-skill` | Changes an existing skill, shows a diff, and iterates. |
| `create-agent` | Scaffolds a subagent with least-privilege tools and a model. |
| `phase-markers` | The phase marker rule that skills follow, so a token tracker can count tokens per phase. |

## Agents

| Agent | What it does |
|---|---|
| `implement-ticket` | Implements a ticket in its own worktree as a background session. |
| `pr-author` | Writes the PR title and description, pushes the branch, and opens the PR. |
| `pr-comment-courier` | Fetches unresolved PR comments and posts replies that the caller wrote. |
| `review-pr` | Reviews a PR and posts inline comments. |
| `impact-scout` | Finds the callers of a symbol, field, or endpoint that a breaking change affects. |
| `review-dependabot-pr` | Reviews a dependabot PR and opens a draft PR with guard tests if it finds a risk. |
| `dependabot-sweep` | Sends each open dependabot PR to `review-dependabot-pr` and reports a table of verdicts. |

## License

[MIT](LICENSE)
