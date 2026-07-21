---
type: instruction
status: active
---

# Workflow

## Build sequence

1. Start with a small plan.
2. State the acceptance criteria in observable terms.
3. Write the narrowest test that proves the behavior.
4. Implement the smallest change that passes.
5. Run the focused validation command.
6. Update docs when the change adds a durable concept or decision.

## Working rules

- Keep edits surgical.
- Do not add abstractions before they are needed.
- Prefer vertical slices over broad rewrites.
- If a task touches multiple layers, land the smallest end-to-end slice first.

## Documentation cadence

- Put phase research and plans in `docs/plans/`.
- Put architecture decisions in `docs/decisions/`.
- Put session continuity notes in `docs/handoffs/`.
