---
type: instruction
status: active
---

# Testing Standards

## Defaults

- Use `pytest` for Python tests.
- Keep tests in `tests/`, mirroring `src/`.
- Test public behavior through the CLI or module API, not private helpers.
- Keep each test focused on one behavior.

## For this repo

- CLI tests should call the `main()` function directly.
- Use `capsys` for stdout assertions.
- Prefer small, deterministic tests that do not need network or external services.
