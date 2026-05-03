# Task 1: Implement experiment greet function

> Ticket: LOCAL-20260503-225201
> Task: task-1-experiment-greet

## Context

This is a synthetic Phase 0 direct Codex validation task. It uses a non-gitignored path so `diff.patch` can capture newly created files without force-staging ignored content.

## Goal

Implement `greet(name: str) -> str` in `experiments/workflow-improvement/fixtures/codex-direct-greet/hello.py`.
The function must return `"Hello, {name}!"`.
Include a `__main__` block that prints `greet("World")`.
Write unit tests in `experiments/workflow-improvement/fixtures/codex-direct-greet/test_hello.py`.

## Inputs

- Plan: `.claude/plans/LOCAL-20260503-225201/plan.md`
- Result schema: `templates/workflow-contract/result.schema.md`

## Outputs

- Modify:
  - none
- Create:
  - `experiments/workflow-improvement/fixtures/codex-direct-greet/hello.py`
  - `experiments/workflow-improvement/fixtures/codex-direct-greet/test_hello.py`

## Reference Guidelines

- Python standard library only.
- Follow PEP 8 naming and style.
- Tests must use `unittest`.

## Verification

- [ ] Run `python3 experiments/workflow-improvement/fixtures/codex-direct-greet/hello.py`
- [ ] Run `python3 -m unittest discover -s experiments/workflow-improvement/fixtures/codex-direct-greet -p 'test_*.py'`

## On completion

Write `.claude/tasks/done/task-1-experiment-greet-result.md` using the shared result schema.
