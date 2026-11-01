---
name: list-my-prs
description: Lists your open pull requests across all repositories, and the PRs that wait for your review, grouped by repository with their age. Use for "/list-my-prs", "what are my open PRs", or "what do I need to review".
allowed-tools: Bash(gh search prs *)
model: haiku
---

# List My PRs

List your open pull requests in every repository, and the PRs that wait for your review.

## Arguments

| Flag | Effect |
|---|---|
| *(none)* | Your open PRs, and the PRs with a review request to you by name |
| `--reviews` | Only the PRs that wait for your review |
| `--teams` | Also the review requests to your teams. These can be many. |

## Workflow

1. **Your open PRs** (skip with `--reviews`):
   ```bash
   gh search prs --author=@me --state=open --limit 100 --json number,title,repository,createdAt,url,isDraft
   ```
2. **Review requests to you by name:**
   ```bash
   gh search prs "user-review-requested:@me" --state=open --limit 100 --json number,title,repository,author,createdAt,url
   ```
   With `--teams`, use `--review-requested=@me` instead. It also counts the requests to your teams.
3. **Show** two tables, grouped by `repository.nameWithOwner`: the PR number, the title, the age in days (from `createdAt`), draft or not, and the URL. In the review table, add the author. Mark a PR that is older than 14 days.

If a list returns 100 rows, say that the limit was reached and that more can exist.

## Examples

- `/list-my-prs`
- `/list-my-prs --reviews`
- `/list-my-prs --reviews --teams`
