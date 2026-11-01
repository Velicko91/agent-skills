# Technical Design: [Service Name]

> **Before starting**: Ensure you have a Product Requirements Document (PRD). Without it, a tech spec is premature.
>
> **Review process**: Share initial version on #eng-tech-specs for feedback. Involve Data Team early to avoid costly changes.

---

## 1. Introduction

### Problem Statement
Brief summary of what needs to be accomplished (not how). This is the TLDR of the PRD.

- **PRD Link**: [link]
- **NFR Link**: [link] *(optional - if you have specific Non-Functional Requirements)*

### Historical Context
Background needed to understand this document:
- Legacy considerations
- What's wrong with the current state (be precise, blameless)

---

## 2. Glossary

Define domain terms, abbreviations, and special words used in this document.

| Term | Definition |
|------|------------|
| | |

---

## 3. Scope

### In Scope
What this design addresses.

### Out of Scope
Related problems this design explicitly does NOT address. List problems someone might expect this to solve but won't be covered.

---

## 4. Summary

High-level description of the solution. Touch on key aspects without deep specifics. Reader should understand the general approach after this section.

---

## 5. System Architecture

### Components
List components in your design. Include a diagram (reusable in service runbook).

```
[Diagram placeholder]
```

### Dependencies

**Upstream** (services this design depends on):
-

**Downstream** (services/applications that depend on this design):
-

---

## 6. Data Model

### Datastore(s)
What storage solutions does this design use?

### Schema Overview
High-level database schema with key fields. Details like data types, foreign keys, indexes can be brief at this stage.

| Table | Key Fields | Purpose |
|-------|------------|---------|
| | | |

### Other Storage
Message brokers, caches, or other stores used.

---

## 7. Interfaces

### Internal APIs
Describe how system components communicate:
- GraphQL operations
- gRPC methods
- Events/messages

### External Dependencies
External services and interfaces this design depends on.

---

## 8. Impact & Risks

### Impact Assessment
How might this affect:
- Performance
- Security
- Data privacy
- Frontend/Mobile
- Other system parts

### Risks & Unknowns
- Known risks
- Open questions
- Areas needing investigation or PoC

---

## 9. Observability

### Monitoring
What aspects need monitoring and how?

### Alerts
Key alerts needed to ensure smooth operation:
-

---

## 10. Product Metrics

What data needs to be captured for product metrics and KRs?

Work with PM and Data Team to identify data needed for the feature's Looker dashboard.

---

## 11. Productionization *(optional)*

*Include this section for complex designs.*

### Migration Plan
Data migration steps if needed.

### Release Strategy
- Feature flags (separate release from deployment)?
- Canary release (gradual rollout)?
- Full release?

---

## 12. Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| | |

> This section invites contributions from other teams. The final design may differ significantly from the initial version.
