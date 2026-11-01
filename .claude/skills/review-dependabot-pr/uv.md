# uv

## Commands

| Purpose | Command |
|---|---|
| The lockfile is consistent | `uv lock --check` — errors when the lockfile is out of date |
| Resolve without writing | `uv lock --dry-run` |
| Targeted upgrade | `uv lock --upgrade-package <pkg>` — not a bare `uv lock` |
| Hold to one version | `--exclude-newer-package '<pkg>=<YYYY-MM-DD>'` |
| Cooldown in config | `[tool.uv] exclude-newer` in `pyproject.toml`, a duration such as `"3 days"` |
| Default install surface | `uv export --no-hashes --no-emit-project` |
| With extras | `uv export --extra <name>` or `--all-extras` |
| One workspace member | `uv export --package <member>` |
| Why a package is here | `uv tree --invert --package <pkg>` |
| Sync preview | `uv sync --dry-run` |
| Run a command | `uv run <cmd>` |
| Tests (Phase 6) | `uv run pytest -q` (or `make test`), `uv run ruff check .`, `uv run mypy .` |

## Phase 4 — Integrity checks

A `uv.lock` has **no** `optional` field and **no** per-package `markers` field. Do not look for them. uv records the graph like this:

| Structure | Meaning |
|---|---|
| `[[package]]` | `name`, `version`, `source`, `dependencies`, `sdist`, `wheels` |
| `[package.optional-dependencies]` | extras |
| `[package.dev-dependencies]` | PEP 735 groups |
| `{ name = "x", marker = "...", extra = ["y"] }` | markers sit on dependency **edges** |
| `[manifest] members` | workspace members |

Prove the gating through the resolved install surface:

1. **Diff the install surface on both refs.** This is the core check.
   ```bash
   uv export --no-hashes --no-emit-project        > /tmp/<ref>.default.txt
   uv export --no-hashes --all-extras             > /tmp/<ref>.extras.txt
   uv export --no-hashes --package <owned-member> > /tmp/<ref>.member.txt
   ```
   Diff each pair. A package that is new in `.default.txt` is the uv form of the poetry gating defect.
2. **Diff the versions.** Parse the `[[package]]` blocks for `name` and `version` on both refs. Only the target package may change version.
3. **Diff the package set.** List every package that was added or removed. A lost extras gate shows as a package that enters the default resolution.
4. **Diff the structure.** Count the `[package.optional-dependencies]` blocks, the `marker =` edges, and the `[manifest] members` entries. A lower count means that gating or workspace structure was lost.
5. **Check consistency** with `uv lock --check`.

## Phase 3 — Workspace scope

If `repoPolicy.owns` names a path and the repo is a uv workspace, find out whether the bumped package is in the tree of that member:

```bash
uv tree --invert --package <pkg>
uv export --no-hashes --package <owned-member> | grep -i '^<pkg>=='
```

One root `uv.lock` covers every member, so an alert `manifest_path` of `uv.lock` says nothing about scope. Use `[manifest] members` and `uv export --package` instead. If the vulnerable package is outside the owned member, report it plainly. This changes who acts, not whether the fix is necessary.

## Phase 8 — Lockfile repair

```bash
git checkout origin/<baseRefName> -- uv.lock
uv lock --upgrade-package <pkg>
```

To hold an open constraint back to the target version, use a cutoff for this one package. Use the day after the target release:

```bash
uv lock --upgrade-package <pkg> --exclude-newer-package '<pkg>=<YYYY-MM-DD>'
```

This form is exact and touches only one package, so prefer it to a global age gate.
