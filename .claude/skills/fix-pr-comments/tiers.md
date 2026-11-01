# Two-tier runs (`--escalate` and `--only`)

`/sweep-pr-comments` uses two tiers, so the expensive PR session handles only the comments that need its history:

| Tier | Flag | Runs in | Handles |
|---|---|---|---|
| 1 | `--escalate` | A fresh session in the PR folder | The comments that the code and the design document can settle |
| 2 | `--only <ids>` | The resumed PR session, with the full history | Only the comments that tier 1 escalated |

## Tier 1 — `--escalate`

In Step 3, put each comment in one group:

| Handle it | Escalate it |
|---|---|
| Typo or formatting | Design or architecture |
| Style or naming, if the comment names the exact change | Ambiguous: it is not clear what the reviewer wants |
| Invalid, if the code proves it: the line is removed, or the issue is already fixed | The fix touches more than the commented function, or a public interface, a schema, or a migration |
| A real bug whose fix stays inside the commented function | The comment asks to change a decision of the design document |
| A question that the code or the design document answers | A "why" question, if no document records the reason |
| | Any fix whose lint, tests, or `/review-code` fail (undo it first) |

If you are not sure, escalate. A wrong answer costs more than one escalation.

- Fix and reply only to the comments that you handle, as in `unattended.md`.
- Post **no** reply to an escalated comment, because tier 2 answers it.
- End the output with exactly one line, after the Step 8 table:
  ```
  ESCALATE: <comment id>,<comment id>
  ```
  or `ESCALATE: none`. Use the comment `id` from the courier.

## Tier 2 — `--only <ids>`

You run in the PR session, so you have the history of the implementation.

1. Process only the root comments with these ids. Skip every other comment, because tier 1 already handled it.
2. Read the `Claude AI:` replies that tier 1 posted on this PR in this round, so you know what it fixed and why.
3. Use the history of this session and the design document for the answer:
   - **Design or "why" comment:** if the history or the document records the reason, reply with it. If the comment is right and the change stays inside the plan, make the change.
   - **A larger fix** (more than one function): make it, if you verified the issue and lint, the tests, and `/review-code` pass.
   - **A change of a decision** (an interface, a schema, the agreed approach): do not change it unattended. Reply `Claude AI: Acknowledged — this changes a design decision and needs a human decision.`, and give the reason that the decision was made.
   - **Ambiguous:** reply with the question that would settle it.
4. The tier-2 rules above replace the "Design / architecture" and "Ambiguous" rows of `unattended.md`. All its other rules apply.
