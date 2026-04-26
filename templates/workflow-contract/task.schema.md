# Task Schema

> File: `.claude/tasks/pending/task-N-{name}.md`

A task file is the self-contained work order for one implementation unit.

Tasks are feature-level, not file-level. Keep each task small enough for one implementer pass and one reviewer pass.

## Filename

```text
task-{N}-{kebab-name}.md
```

Rules:

- `N` is a 1-based task number.
- `{kebab-name}` must be stable and descriptive.
- Result filename must append `-result` before `.md`.

## Required Sections

```markdown
## Context

## Goal

## Inputs

## Outputs

## Reference Guidelines

## Verification

## On completion
```

## Section Requirements

### Context

Summarize the relevant plan, prior decisions, and constraints. The implementer must not need prior conversation context.

### Goal

Define the behavior or outcome to implement.

### Inputs

List files and artifacts to read.

Example:

```markdown
## Inputs

- Plan: `.claude/plans/OVDR-1234/plan.md`
- Ref files:
  - `src/parser.ts`
  - `test/parser.test.ts`
- Prior task results:
  - `.claude/tasks/done/task-1-parser-fallback-result.md`
```

### Outputs

Declare allowed create/modify paths.

Example:

```markdown
## Outputs

- Modify:
  - `src/parser.ts`
  - `test/parser.test.ts`
- Create:
  - none
```

Rules:

- Every changed file in `diff.patch` must be listed here by some task.
- Use `none` when no paths are expected for a category.
- Do not use broad globs unless the task genuinely owns a whole directory.

### Reference Guidelines

List applicable guideline or policy files. Use `none` when unavailable.

### Verification

Use checkboxes for required evidence.

Example:

```markdown
## Verification

- [ ] Write or update unit tests in `test/parser.test.ts`
- [ ] Run `npm test -- parser`
- [ ] Confirm fallback behavior for empty input
```

Rules:

- Every promised command must appear in `test-output.log` or the task result.
- If a checkbox is intentionally skipped, the result must explain why.

### On completion

Name the expected result file and required summary format.

Example:

```markdown
## On completion

Write `.claude/tasks/done/task-1-parser-fallback-result.md` using the shared result schema.
```

## Optional Sections

```markdown
## Quality Gates

## Review Notes

## Out of Scope
```

Use optional sections when they reduce ambiguity for the implementer or reviewer.

## Minimal Example

```markdown
# Task 1: Parser fallback

## Context

`OVDR-1234` requires parser fallback behavior when optional metadata is absent.

## Goal

Return an empty metadata object instead of throwing when metadata is missing.

## Inputs

- Plan: `.claude/plans/OVDR-1234/plan.md`
- Ref files:
  - `src/parser.ts`
  - `test/parser.test.ts`
- Prior task results: none

## Outputs

- Modify:
  - `src/parser.ts`
  - `test/parser.test.ts`
- Create:
  - none

## Reference Guidelines

- `CLAUDE.md`

## Verification

- [ ] Add a regression test for missing metadata
- [ ] Run `npm test -- parser`

## On completion

Write `.claude/tasks/done/task-1-parser-fallback-result.md` using the shared result schema.
```
