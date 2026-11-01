# Diagram rules (Phase 2)

Add diagrams wherever one of these is true:
- A request flow involves 3+ services
- There's a state machine with 4+ states
- The before/after of an architecture change is non-obvious
- A data pipeline has multiple stages

**Which format to use:**

| Content | Format |
|---------|--------|
| Workflow, request flow, use case, anything with an order of messages | Mermaid `sequenceDiagram` |
| Component architecture | ASCII box diagram |
| State machine | ASCII (or Mermaid `stateDiagram-v2` if it has 6+ states) |
| Data pipeline | ASCII data flow |

## Mermaid Sequence Diagram Rules

- Put the diagram in a fenced code block with the `mermaid` language tag. Notion renders it as a diagram.
- Always use `autonumber`, and match the numbered steps under the diagram to it.
- Declare every participant with a short alias and a readable label: `participant API as Public API`.
- Use `actor` for humans and `participant` for systems.
- Use `->>` for requests and `-->>` for responses.
- Use `alt` / `else` for branches, `opt` for optional steps, `loop` for retries and polling, and `par` for parallel calls.
- Use `Note over X,Y:` to mark pain points (current workflow) or changes (new workflow).
- Keep one diagram to 15 messages or fewer. If a flow is longer, split it into two diagrams.
- Use the names from the Terms table for participants and messages.

## ASCII Styles

**State machine style:**
```
  ┌─────────┐    submit    ┌──────────┐   approve   ┌───────────┐
  │  DRAFT  │────────────▶│ PENDING  │────────────▶│ APPROVED  │
  └─────────┘             └──────────┘             └───────────┘
                               │                        │
                             reject                   execute
                               │                        │
                               ▼                        ▼
                          ┌──────────┐            ┌───────────┐
                          │ REJECTED │            │ COMPLETED │
                          └──────────┘            └───────────┘
```

**Data flow style:**
```
Raw Events ──▶ Kafka Topic ──▶ Consumer ──▶ Transform ──▶ Postgres
                                  │
                                  └──▶ Dead Letter Queue (on error)
```

Use `─`, `│`, `┌`, `┐`, `└`, `┘`, `├`, `┤`, `┬`, `┴`, `┼`, `▶`, `▲`, `▼` for clean box-drawing.
