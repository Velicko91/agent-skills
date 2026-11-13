# Status update template

The form that the teams use for Linear project updates. Write the body in Markdown, with these parts in this order:

1. One headline sentence: the most important change since the last update.
2. `**What happened this week**`, with one bullet for each shipped or finished thing. Say where it is: in production, merged, or in review.
3. `**What's next**`, with one paragraph: the next work, and what must happen before it ships.
4. `**Blockers**`, with one paragraph. If there is none, write `None.` To ask a person, write `@displayName` and the question.

Example (invented):

```markdown
Webhook retries now run in production for card payments; the ACH retries are in review.

**What happened this week**

* Card payment webhooks now retry 5 times with backoff in production.
* The retry outbox table and its migration were merged.
* ACH webhook retries are in review.

**What's next**
Finish the ACH retry review, then add the dashboard for retries that failed 5 times. The dashboard needs the alert threshold from the operations team.

**Blockers**
@alice, please confirm the alert threshold for failed retries.
```

Rules:

- Write about the project, not about one person: "Card payment webhooks now retry", not "I added retries".
- Use the words of the issues and the PRs, but no issue keys and no PR numbers, because readers outside the team read the update.
- Write only what the issues, the milestones, and the work log show. If you are not sure that something is in production, say "merged" or "in review".
