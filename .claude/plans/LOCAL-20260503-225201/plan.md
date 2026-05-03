# Plan: Phase 0 Direct Codex Validation Task

> Ticket: LOCAL-20260503-225201
> Revision: v1
> Runner: codex
> Date: 2026-05-03

### Requirements

Add a `greet(name: str) -> str` function to a new Python module under `experiments/workflow-improvement/fixtures/codex-direct-greet/hello.py`.
The function must return `"Hello, {name}!"`.
Include a `__main__` block that prints `greet("World")`.
Write unit tests in `experiments/workflow-improvement/fixtures/codex-direct-greet/test_hello.py`.

### Out of Scope

- No external dependencies beyond the Python standard library.
- No changes outside `experiments/workflow-improvement/fixtures/codex-direct-greet/` and required `.claude/` run artifacts.
- No deployment.

### Impact scope

New files only:
- `experiments/workflow-improvement/fixtures/codex-direct-greet/hello.py`
- `experiments/workflow-improvement/fixtures/codex-direct-greet/test_hello.py`

No existing code is modified.

### Task breakdown

- Task 1 — `task-1-experiment-greet`: Implement `greet(name)` and write standard-library tests.

### Test Strategy

Run `python3 experiments/workflow-improvement/fixtures/codex-direct-greet/hello.py`.
Run `python3 -m unittest discover -s experiments/workflow-improvement/fixtures/codex-direct-greet -p 'test_*.py'`.

### Quality Gates

- `greet returns correct string`
- `module runs without error`
- `all tests pass`

### Open questions

None. This is a synthetic validation task with no external dependencies.
