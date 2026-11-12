# Repo policy gate (Phase 1.5)

Run this gate before any other work. It stops a full review of a PR that the repo does not want.

## `repoPolicy` keys

`repoPolicy` in `config.local.json` in this skill directory maps `owner/repo` to an acceptance rule:

```json
"repoPolicy": {
  "acme/legacy-lib": {
    "status": "deprecated",
    "accept": ["security"],
    "onOutOfPolicy": "comment-and-close",
    "note": "Deprecated library. Security patches only."
  }
}
```

| Key | Meaning |
|---|---|
| `status` | `active`, `maintenance`, or `deprecated`. Informational. |
| `accept` | Bump classes the repo still takes: `all` or `security`. |
| `minSeverity` | Lowest advisory severity the repo takes. If it is absent, the repo takes every severity. |
| `owns` | Paths the user is responsible for. Phase 3 uses it. |
| `ecosystem` | `poetry`, `uv`, `npm`, or `go`. Phase 4 uses it. |
| `onOutOfPolicy` | `comment-only` keeps the PR open. `comment-and-close` closes it. |
| `note` | The reason. Quote it in the comment, so the author sees why. |

Severity order, lowest first: `low < medium < high < critical`. `moderate` is the same as `medium`, because GitHub returns both names from different endpoints.

## Step 1 — Is the bump a security fix?

Ask the repository first. Its answer is authoritative, and the call is cheap:

```bash
gh api repos/<owner>/<repo>/dependabot/alerts \
  --jq '.[] | select(.state=="open") | "\(.security_advisory.ghsa_id)\t\(.security_vulnerability.package.name)\t\(.security_advisory.severity)\t\(.security_vulnerability.vulnerable_version_range)"'
```

The bump is a **security** bump when both conditions are true:

1. An open alert names the package that this PR bumps.
2. The new version is outside the `vulnerable_version_range` of that alert.

If no alert matches, check the upstream advisories before you call the bump routine:

```bash
gh api repos/<upstream-owner>/<upstream-repo>/security-advisories \
  --jq '.[] | {ghsa_id, severity, summary, vulnerabilities}'
```

Also search the release notes for `CVE-`, `GHSA-`, "security", and "advisory". A fix can ship with no alert on this repository.

## Step 2 — Read the severity, if `minSeverity` is set

Use the severity of the advisory that this bump closes. If several advisories apply, use the highest. A bump that closes a `high` and a `medium` advisory counts as `high`. Compare it with `minSeverity`.

## Step 3 — Decide

| Result | Action |
|---|---|
| Security fix, and the severity meets `minSeverity` | Continue to Phase 2. Name the advisory, and raise the urgency in the comment. |
| Security fix, but the severity is below `minSeverity` | **Skip.** Go to Step 4. |
| Routine bump, and `accept` excludes it | **Skip.** Do no repair. Go to Step 4. |

NEVER skip a bump that closes an advisory at or above `minSeverity`, whatever the repo `status` is. A deprecated repo still takes security patches.

## Step 4 — Skip cleanly

Post exactly one comment. Quote the `note`, so the reason is visible:

```
Claude AI: **Skipped — out of policy for this repository.**

`<owner>/<repo>` is **<status>**. It accepts **<accept>** only.
> <note>

This PR bumps `<pkg>` <old> → <new>, and no open security advisory covers it.
I checked the dependabot alerts for this repository and the upstream advisories
for `<pkg>`. Neither names this bump.

No review was run, and nothing was pushed.
```

If the bump is a security fix below `minSeverity`, replace the middle paragraph with this one, and name both values:

```
This PR closes <GHSA-id> (<severity>). This repository takes <minSeverity>
and above, so it is out of policy. The advisory stays open, and the alert
stays visible.
```

NEVER present a skipped advisory as fixed. State that the alert stays open.

Then apply `onOutOfPolicy`:

- `comment-only` — leave the PR open.
- `comment-and-close` — run `gh pr close <ref>`.

Report the skip in Phase 10, and stop. Do not run Phases 2 to 9.
