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
- `status`: Role-specific outcome status.
  - `implementer`, `integrator`, `debugger`, `analyzer`: `success`, `failure`, or `partial`.
  - `reviewer`: `approved` or `needs-fix`.
- `started_at`: ISO 8601 timestamp.
- `ended_at`: ISO 8601 timestamp.

Rules:

- Unknown or unavailable values must be explicit, for example `model: unknown`.
- Timestamps must use timezone offsets.
- Auditors must interpret `status` according to `role`; reviewer results are not expected to use `success`.

## Body Compatibility

Phase 0 keeps Claude-native workflow behavior unchanged. Existing canonical agents can continue to write XML bodies:

- implementer: `<result>...</result>`
- reviewer: `<review>...</review>`
- integrator: `<integration-result>...</integration-result>`

These XML bodies are valid result bodies when the required frontmatter is present. Fresh adapters use the markdown body sections below because they are easier for lightweight auditors to parse.

Auditors must read frontmatter first, then parse either the existing XML body or the recommended markdown body for changed files, tests, findings, and gate evidence.

## Recommended Implementer Body

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

## Recommended Reviewer Body

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

## Recommended Integrator Body

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

The artifact-only auditor must be able to read:

- `status` from frontmatter and body
- changed file paths from `## Files Changed` or `<files_modified>`
- test commands and evidence from `## Tests` or XML test fields
- scope evidence from reviewer `## Scope Check` or `<review>` issues
- gate evidence from integrator `## Quality Gates` or `<integration-result><gates>`
