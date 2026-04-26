# Result Schema

> File: `.claude/tasks/done/task-N-{name}-result.md` or `.claude/tasks/failed/task-N-{name}-result.md`

A result file records what a role completed for one task and provides evidence for later review, integration, and artifact-only audit.

## Required Frontmatter

```yaml
---
ticket: OVDR-1234
workflow: impl
task: task-1-parser-fallback
role: implementer
runner: codex
model: gpt-5
status: success
started_at: 2026-04-27T10:00:00+09:00
ended_at: 2026-04-27T10:20:00+09:00
---
```

Fields:

- `ticket`: Ticket ID or synthetic validation ID.
- `workflow`: `impl`, `review`, `integration`, or `validation`.
- `task`: Task slug matching the task filename without `.md`.
- `role`: `implementer`, `reviewer`, `integrator`, `debugger`, or `analyzer`.
- `runner`: `claude-code`, `codex`, or another explicit adapter name.
- `model`: Provider model name, or `mixed` if multiple models were used.
- `status`: `success`, `failure`, `approved`, `needs-fix`, or `partial`.
- `started_at`: ISO 8601 timestamp.
- `ended_at`: ISO 8601 timestamp.

Rules:

- Frontmatter is required for Phase 0 validation result files.
- Unknown or unavailable values should be explicit, for example `model: unknown`.
- Timestamps should use timezone offsets.

## Implementer Body

```markdown
## Status

success | failure | partial

## Files Changed

- `path`: description

## Tests

- Command: `npm test -- parser`
- Status: pass | fail | skipped
- Evidence: `.claude/runs/OVDR-1234/test-output.log`

## Decisions

- Decision and reason, or `none`.

## Handoff

Notes for reviewer or next task, or `none`.
```

## Reviewer Body

```markdown
## Status

approved | needs-fix

## Findings

- critical: issue summary, or `none`
- important: issue summary, or `none`
- suggestion: issue summary, or `none`

## Scope Check

- Declared outputs reviewed: pass | fail
- Unexpected changed files: list or `none`

## Summary

Overall verdict and key evidence.
```

## Integrator Body

```markdown
## Status

success | failure | partial

## Quality Gates

- Gate: All tests pass
  - Status: pass | fail | skipped | not-evaluated
  - Evidence: `.claude/runs/OVDR-1234/test-output.log`
  - Notes: short explanation

## Tests

- Command: `npm test`
- Status: pass | fail | skipped
- Evidence: `.claude/runs/OVDR-1234/test-output.log`

## Coverage

Summary of flows tested.

## Issues

Integration issues found, or `none`.

## Manifest

Finalized `.claude/runs/OVDR-1234/manifest.yaml`.
```

## Minimal Implementer Example

```markdown
---
ticket: OVDR-1234
workflow: impl
task: task-1-parser-fallback
role: implementer
runner: codex
model: gpt-5
status: success
started_at: 2026-04-27T10:00:00+09:00
ended_at: 2026-04-27T10:20:00+09:00
---

## Status

success

## Files Changed

- `src/parser.ts`: returns empty metadata when optional metadata is absent.
- `test/parser.test.ts`: adds missing metadata regression coverage.

## Tests

- Command: `npm test -- parser`
- Status: pass
- Evidence: `.claude/runs/OVDR-1234/test-output.log`

## Decisions

- Used an empty object fallback instead of `null` to match existing parser return shape.

## Handoff

Ready for reviewer.
```

## Audit Notes

The artifact-only auditor should be able to read:

- `status` from frontmatter and body
- changed file paths from `## Files Changed`
- test commands and evidence from `## Tests`
- scope evidence from reviewer `## Scope Check`
- gate evidence from integrator `## Quality Gates`
