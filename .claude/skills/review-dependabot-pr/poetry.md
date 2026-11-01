# Poetry

## Commands

| Purpose | Command |
|---|---|
| The lockfile is consistent | `poetry check --lock` |
| Targeted upgrade | `poetry update <pkg>` — not a full `poetry lock`, which re-resolves everything |
| Hold to one version | `POETRY_SOLVER_MIN_RELEASE_AGE=<n> poetry update <pkg>` |
| Cooldown in config | `[solver] min-release-age` in `poetry.toml`, in days |
| Default install surface | `poetry install --dry-run --no-root` |
| With extras | `--extras <name>` or `--all-extras` |
| Run a command | `poetry run <cmd>` |
| Tests (Phase 6) | `poetry run pytest -q` (or `make test`), `poetry run ruff check .`, `poetry run mypy .` |

## Phase 4 — Integrity checks

**Diff the metadata of every package, not only the versions.** Extract `name`, `optional`, and `markers` for every package from both files, and diff the two lists. Flag a package that:

- changes `optional = true` to `optional = false`, or
- loses its `markers` line.

Each change makes an opt-in extra a mandatory dependency.

**Prove the effect.** Run `poetry install --dry-run --no-root` on the merge base, then on the PR head. Compare `Installing <pkg>` with `Skipped ... Not required`. That output is the proof.

**Use the resolver version that the repo demands.** Read `requires-poetry` in `pyproject.toml` and the generator version in the lock header. If the local version is different, install that version, because an older resolver refuses the lock.

## Phase 8 — Lockfile repair

```bash
git checkout origin/<baseRefName> -- poetry.lock
poetry update <pkg>
```

To hold an open constraint back to the target version, use the global age gate. Read the publish dates of the target release and of the next release. Pick an `<n>` between them, so the target is the newest allowed release:

```bash
POETRY_SOLVER_MIN_RELEASE_AGE=<n> poetry update <pkg>
```

Before you commit, check that every package keeps the `optional` flag that it has on the base branch.
