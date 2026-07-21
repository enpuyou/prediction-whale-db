# Prediction Whale DB — Claude Code Instructions

## Working principles

1. Think first - state assumptions explicitly, name uncertainty, and prefer the simplest workable path.
2. Simplicity - minimum code that solves the problem; no speculative abstractions or unrequested polish.
3. Surgical - touch only what the task requires and keep changes aligned with the local style.
4. Verify - define a testable outcome before writing code, then prove it with a focused check.

## What this repo is

This repository is the build workspace for the prediction-market integrity pipeline described in `docs/plans/initial-plan.md`.
The current source of truth is that plan plus any future notes in `docs/plans/`, `docs/decisions/`, and `CONTEXT.md`.

The project goal is to turn the plan into a working Python codebase with:

- batch data collection
- matching between market platforms
- schema normalization and feature engineering
- scoring, alerts, and a small API layer

## Cold start

1. Read `docs/plans/initial-plan.md` first — the phased build plan, current phase is Phase 0.
2. Read `CONTEXT.md` before introducing or renaming domain terms.
3. Read `docs/instructions/workflow.md` and `docs/instructions/testing-standards.md` for build/test conventions.
4. Check `docs/plans/` and `docs/decisions/` before making architecture decisions.

## Workspace layout

- `src/prediction_whale_db/` - application code (ingestion, matching, features, detection, scoring, api)
- `tests/` - tests mirroring `src/`
- `docs/plans/` - phase plans and research notes
- `docs/decisions/` - architecture decisions
- `docs/instructions/` - workflow and testing conventions
- `docs/handoffs/` - session continuity notes

## Working conventions

- State acceptance criteria before a non-trivial change: done when [user action] -> [observable result].
- Keep the first implementation small and testable.
- Prefer behavior-level tests over internal implementation tests.
- Update docs when a change introduces a new durable concept or decision.
- If the repo structure changes, update this file and `CONTEXT.md` together.

## Baseline commands once the scaffold is in place

- `uv sync --group dev`
- `uv run pytest`
- `uv run ruff check src tests`
