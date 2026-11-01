---
name: github-review
description: Reviews a GitHub pull request — checks out its branch in a worktree, runs /review-code on the branch, and posts each finding as an inline comment on the exact line. Use for "/github-review 123", "review PR <url>", or "review this pull request".
user-invocable: true
allowed-tools: Bash(gh *), Bash(git *), Bash(jq *), Read, Grep, Glob, Skill, mcp__notion__notion-fetch, mcp__notion__notion-search
---

# GitHub PR Review

Review a pull request with `/review-code`, and post the findings as inline comments.

## Hard rules

- Start every comment with `Claude AI:`.
- Anchor every comment to the exact line it is about. NEVER post a general or summary comment: no `gh pr comment`, no `gh pr review --comment`, no wrap-up post.
- Never submit APPROVE or REQUEST_CHANGES.
- Never change the PR branch. The review runs in a detached worktree, with `report-only`.
- Remove the worktree at the end, also after a failure.

## Arguments

| Form | Example |
|---|---|
| PR number | `/github-review 123` |
| PR URL | `/github-review https://github.com/acme/api/pull/123` |
| `owner/repo#N` | `/github-review acme/api#123` |
| `--dry-run` | Show the comments that would be posted, and post nothing |

## Workflow

### Step 1 — Read the PR

```bash
gh pr view <ref> --json number,url,title,body,author,baseRefName,headRefName,headRefOid
gh api "repos/<owner>/<repo>/pulls/<number>/comments?per_page=100" --paginate --slurp \
  | jq -c 'flatten | map(select((.body // "") | startswith("Claude AI:")) | {path, line, body})'
```

The second command lists the comments that Claude already posted, so Step 4 does not post them again. If the PR body links a Notion page, fetch it, and use its intent as context for the review.

### Step 2 — Check out the PR in a worktree

The local clone of the repo must exist. Use the current repo if `git remote get-url origin` names `<owner>/<repo>`. Otherwise use `<repos.root>/<repo>` from `~/.claude/config.local.json`, with a leading `~` expanded to the home directory. If neither exists, say so and stop.

```bash
git -C <clone> fetch origin <baseRefName>
git -C <clone> fetch origin "pull/<number>/head"
git -C <clone> worktree add --detach <clone>/.claude/worktrees/review-<number> FETCH_HEAD
git -C <clone>/.claude/worktrees/review-<number> rev-parse HEAD
```

Run the two fetches separately, in this order, because `FETCH_HEAD` points to the first ref of the last fetch. `pull/<number>/head` also works for a PR from a fork. The `rev-parse` output must equal `headRefOid`. If it does not, the PR changed during the fetch; fetch again.

### Step 3 — Review

Run `/review-code full+report-only --branch origin/<baseRefName>` with the worktree as the working directory.

Drop the findings about unused or missing imports, because linters report them.

### Step 4 — Post the findings

Make one comment for each finding with a location: `Claude AI: **[<Critical|Major|Minor|Architecture|Alternative|Comment|Best practice>]** <issue>. <concrete fix>`. Skip a finding if Step 1 shows a Claude comment on the same path and line with the same point. If no finding is left, post nothing.

With `--dry-run`, print the comments and stop at Step 5.

```bash
gh api --method POST repos/<owner>/<repo>/pulls/<number>/comments \
  -f body="Claude AI: **[Critical]** <issue>. <concrete fix>" \
  -f commit_id="<headRefOid>" \
  -f path="src/foo.py" \
  -F line=42 \
  -f side="RIGHT"
```

- For a range, add `-F start_line=<first>` and `-f start_side="RIGHT"`.
- `line` must be in the diff, on the `+` side, or the call returns 422. On a 422, anchor the finding to the nearest line that it really applies to. If there is no such line, retry once with `-f subject_type="file"`. Never drop a finding, and never put it on an unrelated line.

### Step 5 — Clean up and report

```bash
git -C <clone> worktree remove <clone>/.claude/worktrees/review-<number>
```

Report the PR URL, the number of comments posted for each category, and each comment that failed.

Then offer: "Say **retry** to fetch the PR again and run a fresh review."

## Retry

If the user says "retry", use no cached data. Fetch the PR and its comments again, and run the workflow from Step 1.
