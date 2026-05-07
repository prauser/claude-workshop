# impl-workflow 설계 (living spec)

> 상태: 현재 동작하는 시스템의 명세 | 갱신 2026-05-07
> 변경 의도(향후 작업)는 `.claude/plans/LOCAL-20260507-harness-revamp/plan.md` 참조 — 본 문서에 중복 작성 금지.

## 목적

티켓 또는 자유 프롬프트 → 플래닝 → 구현 → 리뷰 → 통합. `/spec-plan`(플래닝)과 `/impl`(구현) 두 슬래시 커맨드로 흐름을 분리해 사용자 승인 단계를 사이에 둔다.

## 현재 흐름

```
/spec-plan {TICKET}              → plan.md 저장 → 종료
                ↓ 사용자 검토
/impl {TICKET} | {free text} | (no arg)
                ↓
            task-N-*.md 생성 → implementer → reviewer (핑퐁 max 3) → ... → integrator → final report
```

### `/spec-plan` (정의: `claude-config/commands/spec-plan.md`)

- 입력: 티켓 ID. CLAUDE.md `## Implementation Config`(있으면)에서 `specs_path`/`prd_path`/`policies_path`/`log_repo` 추출.
- Step 0: 5개 read-only 서브에이전트 병렬 — Jira / Spec / Code / Context / test-engineer(Strategy mode).
  - Iterative search protocol(max 3 cycles): DISPATCH → EVALUATE → REFINE → LOOP. Spec / Code 에이전트가 사용.
  - Config 없으면 Spec / Context 생략.
- Step 1: Requirements(P0/P1) · Out of Scope · Impact scope · Task breakdown(XS~XL) · Test Strategy · Quality Gates · Open questions로 합성.
- Step 2: Cross-review (max 3 rounds). 충돌 유형 A~D (Code↔Spec / Code↔Tests / Jira↔Code / Test↔Code).
- Step 3: 사용자 검토 (revise / investigate more / OK / cancel).
- Step 4: `.claude/plans/{TICKET}/plan.md` 저장. 기존 파일 있으면 `plan-v{N}.md`. 종료.

코드 작성 / `/impl` 자동 트리거 금지.

### `/impl` (정의: `claude-config/commands/impl.md`)

- 입력: 티켓 / 자유 텍스트 / 없음. 티켓이면 `plan.md` 로드 후 요약·확인. 없으면 spec 토론으로 fallback. 외부 티켓이 없으면 `LOCAL-{YYYYMMDD-HHMMSS}` 부여.
- 활성화 시 디렉토리 생성: `.claude/runs/{TICKET}`, `.claude/tasks/{pending,done,failed}`.
- Decompose → task 파일 작성(`task-{N}-{name}.md` with Context / Goal / Inputs / Outputs / Reference Guidelines / Verification / On completion 섹션).
- 각 task 순차 실행: implementer → reviewer. needs-fix면 implementer 재호출 (max 3 round). 3회 후에도 needs-fix면 사용자 에스컬레이션. 실패는 `tasks/failed/`로 이동.
- 모든 task 완료 후 integrator가 plan.md `### Quality Gates`로 통합 검증.
- 종료 시 `rm .claude/current-ticket`. `log_repo` 설정돼 있으면 사용자에게 `sync-logs.sh {TICKET}` 실행 안내.

### 디버그/분석 분기

`/impl`은 디버그(증상)·분석(이해) 요청도 처리. task 파일 작성 후 `debugger`(opus, read-only) 또는 `analyzer`(opus, read-only)로 위임. 결과 보고 후 필요하면 fix 모드로 진행.

## 산출물 위치

```
{repo}/
├── .claude/
│   ├── plans/{TICKET}/plan.md            spec-plan 산출물 (plan-v{N}.md 누적)
│   ├── tasks/
│   │   ├── pending/task-{N}-{name}.md    impl이 발행
│   │   ├── done/task-{N}-{name}-result.md   implementer/integrator 결과
│   │   └── failed/                       실패 시 격리
│   ├── runs/{TICKET}/                    인테그레이터·헤드리스 러너 산출물 루트
│   │   ├── diff.patch
│   │   ├── test-output.log
│   │   └── manifest.yaml
│   └── current-ticket                    impl 진행 중에만 존재. .gitignore 필수
└── CLAUDE.md                             ## Implementation Config 섹션 (선택)
```

## 에이전트 (정의: `claude-config/agents/*.md`)

| 에이전트 | 모델 | 역할 | 권한 |
|---|---|---|---|
| `implementer` | sonnet | 코드 + 단위 테스트, 슬라이스 단위 커밋 | RW |
| `reviewer` | sonnet | 코드 품질·버그·엣지 검사 | read-only |
| `integrator` | sonnet | 통합 테스트, Quality Gates 평가 | RW |
| `debugger` | opus | 6-step 트리아지 (버그 원인 진단) | read-only |
| `analyzer` | opus | 코드 구조·흐름 분석 | read-only |
| `test-engineer` | sonnet | Strategy(spec-plan) / Coverage(standalone) 두 모드 | read-only |
| `md-reviewer` | opus | 프롬프트 markdown 리뷰 | read-only |

## Runner 모델

- 기본: **in-session** (`/impl`이 직접 서브에이전트를 호출하는 Claude Code 네이티브 흐름).
- 헤드리스 옵션: `templates/workflow-contract/runners/codex/impl.sh` (Codex 러너 — Phase 0 검증으로 동작 확인됨).
- 두 러너는 동일 artifact 계약(`task-result.md`, `diff.patch`, `test-output.log`, `manifest.yaml`)을 따름. 계약 정의는 `templates/workflow-contract/contract.md`, `task.schema.md`, `result.schema.md`.
- in-session 기본값은 변경되지 않음. 헤드리스는 명시 옵션.

## CLAUDE.md `## Implementation Config` (옵션)

| 키 | 용도 |
|---|---|
| `specs_path` | TechSpec 디렉토리 (Spec Agent) |
| `prd_path` | PRD 디렉토리 (Spec Agent) |
| `policies_path` | 정책 문서 (Spec Agent) |
| `log_repo` | impl-logs 동기화 대상 |
| `format_command` | pre-commit hook용 |
| `build_command` | pre-PR hook용 |
| `test_command` | pre-PR hook용 |

설정 없으면 Spec / Context Agent 생략, hooks도 생략 가능 (각 hook은 명령이 없으면 no-op).

## Hooks (선택)

품질 게이트만 담당. 자세한 스펙은 `hooks-spec.md` (`pre-commit-format.sh`, `pre-pr-validate.sh`, `sync-logs.sh`). 로깅은 session jsonl 후처리로 처리하고 hook이 직접 쌓지 않는다.

## 테스트 전략

`test-engineer`가 spec-plan에서는 Strategy 모드(범위·계층 권고), 단독 호출 시 Coverage 모드(갭 분석)로 동작. 언리얼 등 도메인별 계층은 `ue-test-strategy.md` 같은 도메인 노트에서 보강.

## Graduation 경로

```
notes/impl-workflow/        ← 살아있는 명세 + 미래 아이디어
experiments/                ← 가설/검증
templates/                  ← 검증된 후보 (workflow-contract 포함)
claude-config/              ← 배포 대상 → deploy.sh → ~/.claude/
```

`.claude/rules/claude-config.md`에 따라 `claude-config/` 외 직접 수정 금지.

## Roadmap

본 명세에서 의도된 변경은 모두 `.claude/plans/LOCAL-20260507-harness-revamp/plan.md`에서 추적. 신규 아이디어 / 의도적 제외는 `future-ideas.md`로 분리.

## 관련 문서

| 문서 | 내용 |
|---|---|
| [spec-plan-spec.md](spec-plan-spec.md) | spec-plan 한국어 요약 (의도) |
| [hooks-spec.md](hooks-spec.md) | hook 스크립트 + settings.json |
| [ue-test-strategy.md](ue-test-strategy.md) | 언리얼 테스트 계층 |
| [future-context-central.md](future-context-central.md) | context-central MCP 연동(예정) |
| [future-ideas.md](future-ideas.md) | plan.md 의도적 제외 + 미흡수 아이디어 |
| [_archive/phase0-codex/](_archive/phase0-codex/) | Phase 0 Codex parity 작업 이력 |
