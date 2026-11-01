# When CI is red (Phase 6)

NEVER report a red check without reproducing it. A red check has three possible causes, and only one of them is the bump.

1. **Reproduce locally.** Run the same job on the PR head.
2. **Compare with the merge base.** Check out the merge base and run the same test. If it fails on both sides, the failure is pre-existing and belongs in its own PR. Say which case it is.
3. **Read the failure, not the label.** A red check is not always a failed assertion. Look for a timeout, a cancelled job, a flaky network call, a port collision, or a coverage threshold. Quote the real error, because a timeout and an assertion failure need different answers.
4. **Fix it, and explain the cause.** If the bump caused the failure, fix it on the branch. State which upstream change broke which call site, and why the fix is correct. A fix without an explanation is not finished, because the next reader must be able to check your reasoning.

NEVER silence a failure. Do not delete an assertion, loosen a threshold, add a skip mark, or pin a dependency backwards. If the only way to green is a weaker test, the bump is the finding. Report it.
