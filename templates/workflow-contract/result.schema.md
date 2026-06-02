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
risk_acks: []          # Optional. preamble.md §8 위험영역 ack 결과. 비어 있으면 생략 가능.
plan_deviations: []    # Optional. 런타임에 plan 에 없는 결정이 발생했을 때 append. 각 {ts, note}. 비어 있으면 생략.
---
```

Fields:

- `ticket`: Ticket ID or synthetic validation ID.
- `workflow`: `impl`, `review`, `integration`, or `validation`.
- `task`: Task slug matching the task filename without `.md`. For integrator results with no per-task slug, use `integration`.
- `role`: `implementer`, `reviewer`, `integrator`, `debugger`, or `analyzer`.
- `runner`: One of `in-session`, `headless-claude`, `headless-codex`, or `claude-code`/`codex`
  for legacy compatibility. Auditors must accept either form during transition. (`claude-code` 는
  과거 in-session 용 별칭; 신규 result 는 `in-session` 권장.)
- `model`: Provider model name, or `mixed` if multiple models were used.
- `status`: Role-specific outcome status.
  - `implementer`, `integrator`, `debugger`, `analyzer`: one of `success`, `partial`, `failure`,
    `error`, `in-progress`. Terminal values are the first three. `in-progress` is a transient
    stub written when a runner starts; orchestrator demotes it to `error` if still present at
    runner exit (see contract.md §Status Machine).
  - `reviewer`: `approved` or `needs-fix` (independent enum).
- `started_at`: ISO 8601 timestamp.
- `ended_at`: ISO 8601 timestamp.
- `risk_acks` (optional): preamble.md §8 위험영역에 닿았을 때 implementer/integrator 가 append. 각 항목 `{area, ack: confirmed|needs_check, ts}`. `area` 는 baseline 5 종 slug enum 중 하나 (`memory` / `replication` / `concurrency` / `architecture` / `build-deploy`) 또는 plan.md `risk_areas:` 에 선언된 +α slug. `needs_check` 가 하나라도 있으면 result `status` 를 `partial` 로 내리고 사용자 확인을 받아야 한다. 비어 있거나 영역에 안 닿으면 필드 자체 생략.
- `plan_deviations` (optional): 런타임에 plan 에 없는 결정이 발생하면 implementer / integrator 가 한 줄 append. 각 `{ts, note}`. reviewer 의 `<intent_check>` 가 참조. 한 task 에서 3 건 이상 누적되면 orchestrator 가 plan 갱신 권유 (강제 X). 비어 있으면 필드 생략.

Rules:

- Unknown or unavailable values must be explicit, for example `model: unknown`.
- Timestamps must use timezone offsets.
- Auditors must interpret `status` according to `role`; reviewer results are not expected to use `success`.

## Body Compatibility

Phase 0 keeps Claude-native workflow behavior unchanged. Existing canonical agents can continue to write XML bodies:

> **Migration note (post task-6/11):** new reviewer results must use the `<review>` XML body
> defined in `claude-config/agents/reviewer.md` §Output format. The markdown reviewer body
> documented in §Recommended Reviewer Body below is **legacy** — kept so auditors can still
> parse pre-task-6 result files, but no new reviewer output should use it. Implementer /
> integrator body forms are unaffected and may continue to use either XML or the recommended
> markdown form.

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

## Recommended Reviewer Body — Legacy form — see Migration note above. Do not emit for new reviews.

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

## Minimal In-session Example

```markdown
---
ticket: OVDR-1234
workflow: impl
task: task-2-auth-guard
role: implementer
runner: in-session
model: sonnet
status: success
started_at: 2026-04-27T11:00:00+09:00
ended_at: 2026-04-27T11:15:00+09:00
---

## Status

success

## Files Changed

- `src/auth.ts`: added guard middleware for protected routes.

## Tests

- Command: `npm test -- auth`
- Status: pass
- Evidence: `.claude/runs/OVDR-1234/test-output.log`

## Decisions

- none

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

> Auditor must demote any `pending` / `in-progress` status to `error` if observed in a finalized
> manifest (per contract.md §Status Machine).
