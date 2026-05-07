# Workflow Artifact Contract

> Status: Phase 0 draft  
> Scope: provider-neutral artifacts for `/spec-plan` and `/impl` parity  
> Canonical role prompts: `claude-config/agents/*.md`

## Goal

This contract defines the shared artifacts that let Claude Code and Codex run the same workflow shape with comparable evidence.

Phase 0 targets process and gate parity:

- same plan, task, result, run, diff, and test-output artifacts
- same objective audit checks
- same quality gate evidence
- one end-to-end validation run per runner

It does not require identical model output quality or identical provider internals.

## Provider Boundaries

Shared contract:

- artifact paths and file purposes
- task and result metadata
- quality gate evidence
- manifest binding across workflow runs
- artifact-only audit checks

Provider-specific details:

- subagent or child-session mechanism
- hook lifecycle
- transcript or event format
- model names and reasoning controls
- tool permission implementation

## Runtime Paths

The `.claude/` runtime path is historical compatibility. It is not a Claude-only boundary.

```text
.claude/plans/{TICKET}/plan.md
.claude/tasks/pending/task-N-{name}.md
.claude/tasks/done/task-N-{name}-result.md
.claude/tasks/failed/task-N-{name}-result.md
.claude/runs/{TICKET}/manifest.yaml
.claude/runs/{TICKET}/diff.patch
.claude/runs/{TICKET}/test-output.log
```

Adapters can store provider-native logs elsewhere, but the auditor only relies on these shared artifacts during Phase 0.

## Workflow Artifacts

### Plan

`plan.md` is produced by `spec-plan` and read by `impl`.

Required sections:

- `### Requirements`
- `### Out of Scope`
- `### Impact scope`
- `### Task breakdown`
- `### Test Strategy`
- `### Quality Gates`
- `### Open questions`

When replanning occurs, preserve previous revisions and record the active revision in `manifest.yaml`.

### Task

Each implementation unit is a self-contained task file in `.claude/tasks/pending/`.

See `task.schema.md` for the current required sections.

### Result

Each completed task writes one result file in `.claude/tasks/done/`.

The result declares:

- minimal YAML frontmatter
- status
- changed files
- test evidence
- decisions and handoff notes

See `result.schema.md`.

### Run Manifest

`manifest.yaml` binds ticket-level runs, plan revisions, session identifiers, artifacts, and quality gate evidence.

The integrator owns final manifest writing. A runner can create an initial stub, but the integrator finalizes status and gate evidence after all task results are available.

See `manifest.schema.md`.

### Diff

`diff.patch` captures the final code changes for the run.

For validation, generate it from the repository state used by the runner and store it under `.claude/runs/{TICKET}/`.

### Test Output

`test-output.log` captures commands and outputs used as evidence for task verification and integration quality gates.

If multiple commands are run, append each command with enough context to connect it to a task or gate.

## Common Preamble

매 task 호출 직전 runner는 task 본문 앞에 다음 7개 규칙을 prepend한다. in-session·headless-claude·
headless-codex 모두 동일.

1. 작업 전에 task 파일과 §사전 준비에 명시된 모든 파일을 읽고 설계 의도를 이해하라.
2. 이전 task의 result 파일(`.claude/tasks/done/`)을 읽고 일관성을 유지하라.
3. task에 명시된 §Outputs(또는 §작업 내용에 적힌 파일) 외에는 수정·삭제하지 마라.
4. §Acceptance Criteria의 bash를 실제로 실행하고, 결과를 `.claude/runs/{TICKET}/test-output.log`에 append하라.
5. 실패한 테스트를 비활성화·skip·삭제하지 마라. 원인을 고치거나 result에 partial로 기록하라.
6. 모호한 결정은 result 파일 `<decisions>`에 한 줄로 기록하라.
7. 자동 commit / push / PR을 만들지 마라. 변경 후 `git status`만 보고하고 멈춘다 (commit은 사용자/orchestrator가 처리).

Runner 인터페이스: prepend는 텍스트 합성으로 구현. in-session은 `/impl`이 implementer에 보내는
prompt 앞에 직접 합치고, headless 러너는 task 파일 본문을 stdin/argv로 넘기기 전에 합친다.
프리앰블 본문은 `templates/workflow-contract/preamble.md`에 SSOT로 보관 (본 task에서 신규
파일로 생성).

## Runners

`/impl` 가 task 를 실행할 때 사용하는 runner adapter 는 **3종**이며, 모두 같은 artifact 계약을
지킨다 (plan.md / task / result / runs/{TICKET}/{diff.patch,test-output.log,manifest.yaml}).

| ID | 설명 | 스크립트 위치 | 기본 model |
|---|---|---|---|
| `in-session` | 현재 Claude Code 세션의 sub-agent 호출. 기본값 | (스크립트 없음 — orchestrator 직접) | sonnet |
| `headless-claude` | `claude -p --output-format json` exec 1회/role | `templates/workflow-contract/runners/claude/impl.sh` (task-5b 에서 신규) | sonnet |
| `headless-codex` | `codex exec --json` exec 1회/role | `templates/workflow-contract/runners/codex/impl.sh` | (CLI 기본) |

### Runner 호출 인터페이스

각 runner script (in-session 제외) 는 다음 CLI 표준을 만족:

```text
impl.sh --ticket TICKET [--plan PATH] [--tasks-dir PATH] [--model MODEL] [--dry-run]
```

종료 코드:
- `0` — 모든 task 의 result 가 terminal status (`success`/`failure`/`partial`) 로 기록됨
- `2` — 인자 오류
- `3` — runner-specific 실패 (CLI 미설치 / network / auth). **fallback 금지** — 사용자가 in-session
  으로 재시도하도록 안내 (운영 사고 방지)
- `1` — 기타 / 알 수 없는 실패

### Codex 실패 정책 (fail-loud)

`codex` CLI 호출이 network / auth / sandbox / model-not-found 로 실패하면 (fail) runner 는:
1. stderr 에 사람 읽을 수 있는 에러 출력
2. 부분 결과를 `.claude/tasks/failed/` 로 이동
3. exit 3 으로 종료

`--silent` / `--ignore-error` / 자동 in-session fallback 을 도입하지 않는다 (조용한 fallback 은
사용자가 알아채지 못하는 운영 사고의 가장 흔한 원인). fallback 금지는 no automatic fallback 정책의
핵심 불변 규칙이다.

## Status Machine

result 의 `status` 필드는 다음 상태 머신을 따른다.

```text
pending → in-progress → success | failure | partial
                     ↘ (runner 종료 시 in-progress / pending 잔류) → error
```

| 상태 | 의미 | 누가 set |
|---|---|---|
| `pending` | task file 만 있고 runner 아직 시작 전 | (set 안 함 — 결과 파일 없음) |
| `in-progress` | runner 가 시작했으나 아직 종료 안 됨 | runner 시작 시 result frontmatter 에 stub 작성 (선택) |
| `success` | 의도한 결과 + 모든 AC 통과 | implementer/integrator |
| `partial` | 일부 AC 만 통과, 나머지는 follow-up | implementer/integrator |
| `failure` | AC 실패 또는 작업 중단 | implementer/integrator |
| `error` | runner / 환경 / 자기보고 누락 — **자동 강등** | runner 또는 orchestrator |

### Self-report 검증

runner 종료 후 orchestrator (또는 in-session `/impl`) 는 모든 task 의 result frontmatter status
를 점검:
- `pending` 또는 `in-progress` 가 남아 있으면 → **자동 `error` 강등** (auto-demote: frontmatter
  status 를 `error` 로 덮어쓰고 body 끝에 한 줄: `> auto-demoted: status was {original} at runner exit`)
- terminal status (`success` / `partial` / `failure`) 만 audit pass.

reviewer 의 status (`approved` / `needs-fix`) 는 별도 enum — 본 머신은 implementer / integrator /
debugger / analyzer 의 status 에만 적용.

## Phase 0 Audit Contract

The artifact-only auditor checks:

1. Every task in the plan or task directory has a matching result file.
2. Files changed in `diff.patch` are declared in task `## Outputs`.
3. Promised tests or quality gates have evidence in result files or `test-output.log`.
4. Integrator gate statuses match the plan `### Quality Gates`.
5. Result files include runner, role, model, status, and timestamps.
6. `spec-plan` runs stayed planning-only when a manifest records workflow `spec-plan`.

Treat Phase 0 audit output as advisory until one Claude-native and one Codex validation run succeed.

## Acceptance Criteria

This contract is sufficient for Phase 0 when:

- Claude-native and Codex exec-per-task runs can produce the same artifact set.
- The same artifact-only auditor can evaluate both runs.
- The validation report separates contract sufficiency, result quality, cost, and latency.
