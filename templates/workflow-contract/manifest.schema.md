# Manifest Schema

> File: `.claude/runs/{TICKET}/manifest.yaml`  
> Owner: integrator finalizes; runner may create the initial stub

`manifest.yaml` binds ticket-level workflow runs, plan revisions, provider sessions, artifacts, and quality gate evidence.

## Top-Level Fields

```yaml
schema_version: 0.1
ticket: OVDR-1234
created_at: 2026-04-27T10:00:00+09:00
updated_at: 2026-04-27T10:45:00+09:00
status: success
workflow_runs: []
quality_gates: []
audit:
  status: not-run
  artifact: null
```

Fields:

- `schema_version`: Contract version. Phase 0 uses `0.1`.
- `ticket`: Ticket ID or synthetic validation ID.
- `created_at`: ISO 8601 timestamp for manifest creation.
- `updated_at`: ISO 8601 timestamp for last manifest update.
- `status`: `pending`, `success`, `failure`, or `partial`.
- `workflow_runs`: Ordered list of `spec-plan`, `impl`, or validation runs.
- `quality_gates`: Final gate evidence from the integrator.
- `audit`: Optional artifact-only audit status and output path.

## Workflow Run

```yaml
workflow_runs:
  - workflow: spec-plan
    plan_revision: v1
    runner: claude-code
    session_id: 019abc
    model: claude-sonnet
    status: success
    started_at: 2026-04-27T10:00:00+09:00
    ended_at: 2026-04-27T10:12:00+09:00
    artifacts:
      plan: .claude/plans/OVDR-1234/plan.md
```

Fields:

- `workflow`: `spec-plan`, `impl`, `review`, or `validation`.
- `plan_revision`: `v1`, `v2`, etc. Use `v1` for the first `plan.md`.
- `runner`: `claude-code`, `codex`, or another explicit adapter name.
- `session_id`: Provider session ID or stable local run ID.
- `model`: Primary model used for the run, or `mixed` when multiple models were used.
- `status`: `pending`, `success`, `failure`, or `partial`.
- `started_at`: ISO 8601 timestamp.
- `ended_at`: ISO 8601 timestamp, nullable while running.
- `artifacts`: Paths to shared artifacts produced or consumed by the run.

## Impl Run Artifacts

```yaml
artifacts:
  plan: .claude/plans/OVDR-1234/plan.md
  tasks:
    - .claude/tasks/pending/task-1-parser-fallback.md
  results:
    - .claude/tasks/done/task-1-parser-fallback-result.md
  diff: .claude/runs/OVDR-1234/diff.patch
  test_output: .claude/runs/OVDR-1234/test-output.log
  integration_result: .claude/runs/OVDR-1234/integration-result.md
```

Rules:

- Artifact paths are repository-relative.
- `tasks` and `results` are ordered by task number.
- `diff` and `test_output` are required for Phase 0 validation.
- Provider-native logs may be recorded in extra fields, but auditors must not depend on them during Phase 0.

## Quality Gates

```yaml
quality_gates:
  - name: All tests pass
    status: pass
    evidence:
      - .claude/runs/OVDR-1234/test-output.log
    notes: "Unit and integration suites passed."
```

Fields:

- `name`: Gate name copied from plan `### Quality Gates`.
- `status`: `pass`, `fail`, `skipped`, or `not-evaluated`.
- `evidence`: List of artifact paths supporting the status.
- `notes`: Short explanation.

Rules:

- Every plan quality gate should have one manifest entry.
- `success` status requires every gate to be `pass`.
- `skipped` requires a reason in `notes`.

## Audit

```yaml
audit:
  status: pass
  artifact: .claude/runs/OVDR-1234/artifact-audit.md
  checked_at: 2026-04-27T10:50:00+09:00
```

Fields:

- `status`: `not-run`, `pass`, `fail`, or `warning`.
- `artifact`: Path to audit output, nullable.
- `checked_at`: ISO 8601 timestamp, nullable before audit.

## Minimal Example

```yaml
schema_version: 0.1
ticket: OVDR-1234
created_at: 2026-04-27T10:00:00+09:00
updated_at: 2026-04-27T10:45:00+09:00
status: success
workflow_runs:
  - workflow: impl
    plan_revision: v1
    runner: codex
    session_id: codex-20260427-ovdr-1234
    model: gpt-5
    status: success
    started_at: 2026-04-27T10:10:00+09:00
    ended_at: 2026-04-27T10:44:00+09:00
    artifacts:
      plan: .claude/plans/OVDR-1234/plan.md
      tasks:
        - .claude/tasks/pending/task-1-parser-fallback.md
      results:
        - .claude/tasks/done/task-1-parser-fallback-result.md
      diff: .claude/runs/OVDR-1234/diff.patch
      test_output: .claude/runs/OVDR-1234/test-output.log
quality_gates:
  - name: All tests pass
    status: pass
    evidence:
      - .claude/runs/OVDR-1234/test-output.log
    notes: "Recorded test command exited 0."
audit:
  status: not-run
  artifact: null
  checked_at: null
```
