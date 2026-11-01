# Shared libraries — check the consumers before you fix (Phase 6)

The repo is one of `repos.sharedLibraries`. A fix that satisfies this repo can break the services that depend on it.

Before you commit a fix:

1. **Find the consumers.** Search the sibling checkouts under `repos.root`, read-only, for the library name and for the symbol that you change:
   ```bash
   grep -rln '<library>' <repos.root>/*/pyproject.toml
   grep -rn '<symbol>' <repos.root>/<consumer>/ --include='*.py'
   ```
2. **Record which consumers touch the affected surface**, with `file:line`.
3. **Prefer a fix that needs no change in a consumer.** Keep the old signature and the old default working. Add, do not replace.
4. **If no compatible fix exists, say so.** Name each consumer that must change and what it needs. Do not land a breaking change quietly in a shared library.

State the consumer impact in the comment, also when no consumer touches the change. A reviewer needs that result to merge with confidence.
