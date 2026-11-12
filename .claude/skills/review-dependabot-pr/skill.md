---
name: review-dependabot-pr
description: Reviews one dependabot PR in depth — changelog, real call sites, lockfile extras gating, org policy — then repairs that PR so it can merge, and posts one comment. Runs unattended. Use for "/review-dependabot-pr <url>" or "review this dependabot PR".
user-invocable: true
allowed-tools: Bash(gh *), Bash(git *), Bash(go *), Bash(poetry *), Bash(uv *), Bash(pytest *), Bash(make *), Bash(ruff *), Bash(mypy *), Bash(pnpm *), Bash(npm *), Bash(diff *), Bash(jq *), Bash(awk *), Bash(grep *), Bash(sort *), Bash(comm *), Bash(wc *), Bash(head *), Bash(tail *), Bash(find *), Bash(ls *), Bash(cat *), Read, Grep, Glob, Edit, Write, WebFetch
---

# Review Dependabot PR

Review one dependency-update PR, then repair that PR so a human can merge it. This is the deep counterpart of `/approve-and-merge-chore-prs`.

## Hard rules

- NEVER approve and NEVER merge a PR. A human, or `/approve-and-merge-chore-prs`, does that.
- NEVER ask the user a question. Decide, act, and report.
- Repair the existing PR. Open a second PR only in the fallback of Phase 8.
- NEVER work in the main checkout. Use a worktree, and remove it when you finish.
- Take every version from the resolver, never from memory or from the PR title. NEVER hand-edit a version.
- NEVER claim a breaking change without a call site. Cite `file:line` for every risk.
- NEVER claim an install effect or a blast radius that you have not proven. A library lockfile does not reach the consumers of that library.
- NEVER weaken a policy check, drop a flag, or silence a test to make something pass.
- NEVER script a code change (`sed -i`, `awk`, `perl -pi`, `python`, heredocs). Use Edit and Write only, one clear change at a time, with no bulk find-and-replace. Scripts are fine for reading code.
- Count before you describe. NEVER truncate a list with `head` and then describe its size.
- If a later finding shows that an earlier claim was wrong, say so in the output, and record it in the lessons.

## Arguments

| Form | Example | Meaning |
|------|---------|---------|
| PR URL | `https://github.com/acme/repo/pull/142` | The PR to review |
| PR number | `142` | A PR in the current repo |
| `--repo owner/repo` | `--repo acme/billing-service` | Use a different repo |
| `--report-only` | — | Review and comment. Change no files, push nothing. |
| `--no-tests` | — | Repair the PR, but add no tests |
| `--no-comment` | — | Post no comment |
| Free text | `focus on the async changes` | Extra context for the review |

A PR reference is required. If it is absent, say so and stop.

## Workflow

### Phase 0 — Load context

1. Read `lessons.md` in this skill directory, and apply what applies. If you need the evidence for a lesson, search `learn-archive.md` by its date.
2. Read two config files on every run, because the policy can change:
   - `config.local.json` in this skill directory. It gives `internal.gitOrgs`, `internal.packageHosts`, and `repoPolicy`. `config.example.json` shows the shape. The file is gitignored.
   - `~/.claude/config.local.json`. It gives `repos.root`, `repos.services`, and `repos.sharedLibraries`. Other skills share these keys.

If a config file does not exist, continue:
- Use the organization managed policy for internal git orgs and package hosts. That policy is authoritative.
- Skip the sibling-repository checks, because `repos.root` is unknown.
- Name the missing file once, in the final output.

NEVER guess an internal registry host, a git org, or a service name.

### Phase 1 — Identify the update

```bash
gh pr view <ref> --json title,body,author,files,url,headRefName,baseRefName,headRefOid,state,mergeable,mergeStateStatus,isCrossRepository
gh pr diff <ref>
```

If the author is not `dependabot[bot]`, stop and report it. The workflow assumes a machine-generated bump.

Record:
- The package name and the ecosystem (pip/poetry/uv, npm/pnpm, go mod, GitHub Actions, Docker)
- The old version → the new version, and the bump type (patch, minor, or major)
- The scope: direct or transitive, and manifest, lockfile, or both
- `mergeable` and `mergeStateStatus`. A `CONFLICTING` PR cannot merge, whatever the review finds.

State the bump plainly, for example `sqlalchemy 2.0.28 → 2.0.30 (patch, direct)`.

### Phase 1.5 — Repo policy gate

If `repoPolicy` has an entry for this repo, and its `accept` does not contain `all`, read `policy-gate.md` and run it. It can stop the run here.

### Phase 2 — Read the upstream changelog

Find what changed between the two versions. Use this order:

1. The dependabot PR body. It usually holds the release notes and a commit list.
2. The GitHub releases of the upstream repo:
   ```bash
   gh api repos/<owner>/<repo>/releases --paginate --jq '.[] | "\(.tag_name)|\(.published_at)"'
   ```
3. `WebFetch` of the CHANGELOG or the release page, if the project is not on GitHub.

Read **every** release between the old and the new version. A 2.0.28 → 2.0.30 bump also contains 2.0.29, and a regression often hides there.

Record:
- **Breaking changes** — removed or renamed APIs, changed defaults, changed return types
- **Deprecations** — the API works now and stops later
- **Behaviour changes** — same signature, different result. These are the most dangerous.
- **Security fixes** — record the CVE if the notes name one. It raises the merge urgency.
- **Bug fixes that cut both ways** — code that depends on the old behaviour breaks

If you cannot find the release notes, say so. NEVER invent release contents, and NEVER infer them from the version number.

### Phase 3 — Find real usage

A breaking change matters only if this code reaches it.

```bash
grep -rn '<package>' --include='*.py' --include='*.go' --include='*.ts' .
```

For each breaking or behaviour change from Phase 2:
- Search for the exact symbol, function, class, or config key.
- Read the call site. Do not judge from the grep line.
- Decide: **affected**, **not affected**, or **uncertain**.

Check the deprecation trap. If a release adds a `DeprecationWarning`, find out whether the test config turns warnings into errors: search for `filterwarnings`, `-W error`, and `conftest.py`. If no such setting exists, the deprecation cannot break the suite. Say so.

If the package is one of `repos.sharedLibraries`, search the sibling checkouts under `repos.root`, read-only, to see whether the pattern repeats.

If the repo is a uv workspace and `repoPolicy.owns` names a path, run the **Workspace scope** check in `uv.md`.

If ten breaking changes reach none of the code, say exactly that. That result gives confidence.

### Phase 4 — Check lockfile and manifest integrity

A dependabot lockfile write can change more than a version. Tests cannot find this: a pipeline that installs every extra cannot see a lost extras gate. Every defect of this type passed a green CI.

1. **Find the merge base, and compare with it.** NEVER compare with the current base branch, because a PR that branched earlier then shows false drift.
   ```bash
   git fetch origin <baseRefName> <headRefName>
   git merge-base origin/<baseRefName> origin/<headRefName>
   ```
2. **Find the ecosystem.** Read `repoPolicy.<owner/repo>.ecosystem`. If it is absent, use the lockfile: `poetry.lock` is poetry, `uv.lock` is uv, `pnpm-lock.yaml` is pnpm, and `go.sum` is go.
3. **Run the checks of that ecosystem:**
   - poetry → read `poetry.md`
   - uv → read `uv.md`
   - npm → check `optionalDependencies` and `peerDependencies`
   - go → check `// indirect`

NEVER run a poetry check on a uv lock. The two formats store gating in different places, so a poetry-type search gives a false clean result.

### Phase 5 — Check org dependency policy

Report each rule as pass, fail, or n/a:

- **Release cooldown** — the new version is at least 3 days old. Check the upstream release date.
- **Cooldown in committed config** — the manager config declares a cooldown. Check the key and its unit in the docs of that manager:

  | Manager | File | Key |
  |---|---|---|
  | poetry | `poetry.toml` | `[solver] min-release-age`, in days |
  | uv | `pyproject.toml` | `[tool.uv] exclude-newer`, a duration such as `"3 days"` |
  | dependabot | `.github/dependabot.yml` | `cooldown` |

  A cooldown in the package manager satisfies this rule alone. Do not report a missing `cooldown` in `dependabot.yml` if the manager already gates by age.
- **Lockfile** — the PR updates both the manifest and the lockfile. A manifest-only bump breaks a frozen install in CI and in Docker.
- **Exact pins** — with no lockfile, the new version is pinned exactly. `@latest`, `@next`, `@main`, `*`, and a bare name fail.
- **GitHub Actions** — a third-party action uses a full commit SHA, with the version in a trailing comment (`uses: foo/bar@<sha> # v4.2.1`). The orgs in `internal.gitOrgs`, `actions/*`, `github/*`, `docker://`, and `./` are exempt.
- **Internal packages** are exempt from the cooldown and the pins. Identify them by URL: a git org in `internal.gitOrgs`, or a registry in `internal.packageHosts`. NEVER identify them by package name, because a package name often differs from its repository name.

If a rule blocks the merge, name that rule. Report a gap that existed before this PR as pre-existing, and recommend a separate PR for it.

### Phase 6 — Verify only what is in doubt

Read CI before you run anything: `gh pr checks <ref>`.

| State | Action |
|---|---|
| CI green, no breaking change suspected | Run nothing. Record `not re-run — CI green, no breaking change suspected`. |
| Only the lockfile was repaired | Run nothing. Phase 4 already proved the install surface. |
| CI fails | Read `ci-red.md` and follow it. |
| A breaking change is suspected at a real call site | Run the suite. Add a guard test only if that call site is at risk. |

Trust green CI. The pipeline already ran the suite on this commit. Run the suite only to answer a question that you have.

If you run it, use the test commands in `poetry.md` or `uv.md`. For Go, run `go build ./...`, `go test ./...`, and `go vet ./...`. Record what passed, what failed, and what you could not run.

If the repo is one of `repos.sharedLibraries` and you will change code, read `shared-library.md` before you commit.

### Phase 7 — Decide

| Finding | Action |
|---|---|
| Clean, and mergeable | Change nothing. Go to Phase 9, and post the "checked, clean" comment. |
| Conflicts with the base branch | Repair in Phase 8. |
| Lockfile or manifest defect | Repair in Phase 8. |
| A real call site is at risk | Add a guard test in Phase 8. |
| A policy rule blocks the merge | Do not repair. Name the rule, and report it. |

With `--report-only`, skip Phase 8.

**The safety ladder.** Use the lowest step that applies, and add nothing above it:
1. No risk found → add nothing.
2. A suspected breaking change reaches a real call site → add a guard test there.
3. A defect landed that the suite cannot catch by design → add a structural check, and state what it does not cover.

A lockfile repair never reaches step 2, because it changes no behaviour. NEVER write a test only to have one.

### Phase 8 — Repair the existing PR

Work in a worktree, and run everything below in it:

```bash
git rev-parse --show-toplevel
git fetch origin <headRefName>
git worktree add <repo-root>/.claude/worktrees/deps-<pkg>-<newver> origin/<headRefName>
```

Apply only the repairs that apply:

- **Conflict with the base branch** — `git fetch origin <baseRefName>`, then `git merge origin/<baseRefName>`.
- **Lockfile defect** — restore the base lockfile whole, then apply the bump again with the narrow command in `poetry.md` or `uv.md`. NEVER hand-merge lockfile hunks.
- **A real call site is at risk** — add a guard test (see below).

**Land the minimum version that closes every open advisory for the package.** Usually that is the version that dependabot proposed, and you must not exceed it, because a newer release brings behaviour the repo did not ask for. First check the new version against the `vulnerable_version_range` of **each** open alert for the package, because a dependabot security PR can be partial:

| Case | Action |
|---|---|
| The proposal clears every range | Land exactly that version. |
| The proposal leaves a range open | Raise it to the lowest version that clears all ranges. Name the advisory that forced the increase, and read the extra releases. |

NEVER let a security PR that leaves an advisory open read as complete. A partial fix that looks complete is worse than no fix, because it closes the ticket.

For an open constraint, the solver takes the newest allowed release, which usually goes past the PR. Hold it back with the age gate in `poetry.md` or `uv.md`. Confirm that the resolved version equals the version in the PR title. Change only the lockfile; leave `poetry.toml` and `pyproject.toml` as they are.

For a routine bump in a repo that accepts everything, accept the resolver result. Read the release notes of the extra versions, and report the version plainly.

**Guard test:**
- Target the call site from Phase 3.
- Assert on the observable behaviour of this code through the dependency, not on the internals of the dependency.
- Follow the patterns, names, and fixtures of the existing test file.
- Name the test for the behaviour that it protects, not for the package version.
- If the new test fails, that is the finding. Keep the test, and report DO NOT MERGE. NEVER tune a test until it passes.

**Before you commit**, check that a default install skips the optional packages, that an install with the extra installs them, and that the suite passes.

**Commit and push:**

```bash
git add <specific files>
git commit
git push origin HEAD:<headRefName>
```

- NEVER use `git add .` or `git add -A`.
- The push is safe, because dependabot stops rebasing a PR once another commit lands on its branch.
- NEVER put `[dependabot skip]`, `[skip dependabot]`, `[dependabot-skip]`, or `[skip-dependabot]` in the commit message. Those strings let dependabot force-push over the fix.
- Record lockfile repairs in the commit message. A restored extras gate or a regenerated lockfile never gets a line in the PR comment.

Remove the worktree when you finish.

**Second-PR fallback.** If `isCrossRepository` is `false`, you have write access, and the fix goes on the existing branch. This is true however large the repair is. A guard test, a new test file, a lockfile regeneration, and a base merge are all normal repair work.

Open a second PR only after a push that you tried has failed, for one of exactly two causes: the PR comes from a fork (`isCrossRepository: true`), or `git push` was rejected for missing write access. Then:
- Use the branch prefix `chore/`, for example `chore/deps-sqlalchemy-2.0.30`.
- Use the PR title prefix `chore(deps):`, for example `chore(deps): sqlalchemy 2.0.28 → 2.0.30`.
- Write `Supersedes #<N>` in the body.
- Post no comment on the original PR. GitHub links the two PRs.

### Phase 9 — Post one comment

Unless `--no-comment` is set, post exactly one comment. Use a heredoc, so the body has real newlines:

```bash
gh pr comment <ref> --body "$(cat <<'EOF'
Claude AI: **Dependabot review — <package> <old> → <new>**

**Verdict:** <SAFE TO MERGE | NEEDS ATTENTION | DO NOT MERGE>

### Security
- <advisory id>, <severity> — <one line>. This repo pins <old>, inside the
  vulnerable range <range>.

### Possible breaking changes
- <change> — `path/file.py:142`

### What I changed
- <a reason that changes the decision>

### Policy
- <the failing rule, named>

### Verification
- <CI state, or the local result if a suspicion forced a run>
EOF
)"
```

| Section | When to include it |
|---|---|
| Security | Only for a security bump |
| Possible breaking changes | Always. Write "none found. No file calls `<pkg>`." if there are none. |
| What I changed | Only if it changes the decision: the landed version differs from the title, a breaking change was found, or the base was merged to clear a conflict |
| Policy | Only if a rule fails |
| Verification | Always, in one or two lines, never a log |

Comment rules:
- Start every body with `Claude AI:`.
- Give the verdict first, so a reviewer gets the answer in one line.
- Write only the verdict, the security case, possible breaking changes, failing policy rules, and the consumer impact of a shared library. Every other line competes with the warning.
- State breaking changes plainly. Cite `file:line` for every impact.
- Link the release notes. Do not paste the changelog.
- If the review found nothing, still post the short "checked, clean" record, because it is a useful signal.
- Post one comment only. No comment for each finding, and no second pass.

### Phase 10 — Output

```
✅ Review complete — <owner/repo#N>

Verdict:   <verdict>
Repaired:  <what you pushed, or "nothing — PR was clean">
Pushed to: <headRefName>          (or "not pushed — --report-only")
Tests:     <"not re-run — CI green, no breaking change suspected",
            or the local result, or "N added in <files>">
Comment:   <url>                  (or "skipped (--no-comment)")

<one paragraph in plain language, with the recommendation>
```

Then record lessons with the entry rule at the top of `lessons.md`.

## Examples

- `/review-dependabot-pr https://github.com/acme/api-service/pull/142`
- `/review-dependabot-pr 142 --repo acme/billing-service`
- `/review-dependabot-pr 142 --report-only` ← review and comment, change nothing
- `/review-dependabot-pr 142 --no-tests` ← repair, but add no tests
- `/review-dependabot-pr 142 this bumps sqlalchemy, we use a lot of raw session handling`

## Retry

Say **"retry"** to run again from scratch. Use no cached PR data, changelog text, or usage findings. Fetch the PR again, read the releases again, search the code again, and discard any proposed test.
