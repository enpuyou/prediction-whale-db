# Prediction Whale DB

Research and build workspace for the prediction-market integrity pipeline.

## Current state

Phase 0 (environment & scoping) is in progress. The durable inputs are:

- `docs/plans/initial-plan.md` - the current phased build plan
- `CLAUDE.md` - agent instructions for working in this repo
- `CONTEXT.md` - domain glossary
- `docs/instructions/` - workflow and testing conventions

## Layout

- `src/` - application code
- `tests/` - unit and integration tests
- `docs/plans/` - phase plans and research notes
- `docs/decisions/` - architecture decisions
- `docs/handoffs/` - continuity notes

## Baseline commands

```bash
uv sync --group dev
uv run pytest
uv run ruff check src tests
```

## CLI

```bash
uv run prediction-whale-db status
```
