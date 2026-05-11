# impl-workflow 설계 (living spec)

> 상태: 현재 동작하는 시스템의 명세 | 갱신 2026-05-08
> 변경 의도(향후 작업)는 `.claude/plans/LOCAL-20260507-harness-revamp/plan.md` 참조 — 본 문서에 중복 작성 금지.
> plan.md 의 task-2~9 는 2026-05-08 시점 머지 완료(또는 머지 대기) 상태.

## 목적

티켓 또는 자유 프롬프트 → 플래닝 → 구현 → 리뷰 → 통합. `/spec-plan`(플래닝)과 `/impl`(구현) 두 슬래시 커맨드로 흐름을 분리해 사용자 승인 단계를 사이에 둔다.

## 현재 흐름

```
/spec-plan {TICKET}   → Gate 1 (Requirements) → Gate 2 (Plan + Ambiguities) → Gate 3 (Test Strategy)
                        → Cross-review → Final Review → plan.md 저장 → 종료
                              ↓ 사용자 검토
/impl {TICKET} | {free text} | (no arg)
                              ↓
        task-N-*.md 생성 → preamble prepend → implementer → reviewer (핑퐁 p1/p2, max 3)
                        → ... → integrator → final report
```

### `/spec-plan` (정의: `claude-config/commands/spec-plan.md`)

- 입력: 티켓 ID. CLAUDE.md `## Implementation Config`(있으면)에서 `specs_path`/`prd_path`/`policies_path`/`log_repo`/`docs_path` 추출.
- **`user_prompt` 캡처**: `/spec-plan` 호출 시 사용자가 입력한 최초 프롬프트 원문을 그대로 보존. 요약·정제 금지. 비었으면 한 번 묻는다.
- Step 0: 5개 read-only 서브에이전트 병렬. 에이전트 ID: `Jira Agent|Jira` / `Spec Agent|Spec` / `Code Agent|Code` / `Context Agent|Context` / `Test Agent|test-engineer`.
  - **Iterative search protocol** (max 3 cycles): DISPATCH → EVALUATE → REFINE → LOOP. Spec Agent / Code Agent 가 사용.
  - Config 없으면 Spec / Context Agent 생략.
  - **Spec Agent `docs_path` 분기**: `docs_path` 가 설정돼 있고 `${docs_path}/adr.yaml` 또는 `${docs_path}/conventions.yaml` 이 존재하면 `stacks:` 태그 필터로 관련 ID(`ADR-014`, `CONV-007` 등) 단위 인용. yaml 부재 시 `prd_path`/`specs_path`/`policies_path` 평문 fallback — 기존 동작 회귀 없음.

#### Gate 1 — Requirements

사용자 승인 없이 Gate 2로 진행하지 않는다.

출력: Requirements (P0/P1) + **Intentional Exclusions** (각 항목에 비용/위험/타이밍 근거 필수 — 동어반복 금지) + Open Questions.

> Intentional Exclusions 이유 컬럼이 동어반복("out of scope", "not now")이면 Gate 2로 진행 불가.

#### Gate 2 — Plan + Ambiguities

사용자 승인 없이(그리고 Ambiguities가 하나라도 미결인 상태에서는) Gate 3로 진행하지 않는다.

출력: Impact Scope + Task Breakdown (XS~XL) + Risks + **Ambiguities** (지금 결정 안 하면 task 분해 붕괴 — Open Questions와 혼용 금지).

#### Gate 3 — Test Strategy

사용자 승인 없이 Step 2(Cross-review)로 진행하지 않는다.

출력: Test Strategy (Unit/Integration/E2E/Risk areas) + Quality Gates 체크리스트. Test Agent `<test-plan>` 결과 반영.

#### Step 2 — Cross-review (max 3 rounds)

충돌 유형 A~D (Code↔Spec / Code↔Tests / Jira↔Code / Test↔Code). 3회 후에도 미해결이면 Final Review에 양쪽 의견 제시.

#### Final Review (post cross-review)

통합 계획 요약 제시. 사용자: Revise / Investigate more / OK / Cancel.

#### Step 4 — plan.md 저장

`.claude/plans/{TICKET}/plan.md` 저장. 기존 파일 있으면 `plan-v{N}.md`.

plan.md frontmatter 필수 필드:
- `user_prompt`: 최초 프롬프트 원문 그대로. 요약 금지.
- `docs_cited`: yaml docs 인용 시만 포함. yaml 미사용(평문 fallback)이면 필드 자체 생략.

코드 작성 / `/impl` 자동 트리거 금지.

### `/impl` (정의: `claude-config/commands/impl.md`)

- 입력: 티켓 / 자유 텍스트 / 없음. 티켓이면 `plan.md` 로드 후 요약·확인. 없으면 spec 토론으로 fallback. 외부 티켓 없으면 `LOCAL-{YYYYMMDD-HHMMSS}` 부여.
- 활성화 시 디렉토리 생성: `.claude/runs/{TICKET}`, `.claude/tasks/{pending,done,failed}`.

#### Runner selection

`--runner ID` 플래그로 runner 선택. 기본값 `in-session`.

| 플래그 | ID | 설명 |
|---|---|---|
| (기본) | `in-session` | 현재 Claude Code 세션의 sub-agent 호출 |
| `--runner headless-claude` | `headless-claude` | `templates/workflow-contract/runners/claude/impl.sh` 호출 |
| `--runner headless-codex` | `headless-codex` | `templates/workflow-contract/runners/codex/impl.sh` 호출 |

Runner enum / Status machine SSOT: `templates/workflow-contract/contract.md` §Runners / §Status Machine.

#### Per-role runner override

기본은 `--runner` 가 모든 role에 적용. role별 분리 시:
- `--runner-implementer ID` / `--runner-reviewer ID` / `--runner-integrator ID`
- 우선순위: **per-role > `--runner` > 기본값(`in-session`)**
- 미지정 role은 `--runner` 또는 기본값 사용

Per-role override / preset 매핑 SSOT: `claude-config/commands/impl.md` §Per-role runner override / §권장 프리셋.

#### 권장 프리셋

| 프리셋 | implementer | reviewer | integrator |
|---|---|---|---|
| `--preset cost-optimized` | `headless-codex` | `in-session` | `in-session` |
| `--preset claude-only` | `in-session` | `in-session` | `in-session` |

두 프리셋 동시 지정 → 에러. per-role 플래그와 동시 지정 시 per-role 우선.

#### Branch policy

현재 브랜치가 `master` / `main` / `develop` 이면 `feat/{TICKET}-{slug}` 자동 분기. uncommitted 변경 보호 (분기 전 `git status` 확인). `feat/{TICKET}-*` 브랜치면 resume — 그대로 사용.

PR 생성은 자동화하지 않는다 (Intentional Exclusions).

#### Commit policy

reviewer `approved` 직후, orchestrator(`/impl`)가 2단 커밋 수행:
1. **Code commit** (`feat`/`fix`/`refactor`/`docs`): task `## Outputs` 선언 경로만 `git add`. 와일드카드 전체 추가(`-A` 또는 `.` 인수) 금지. `--no-verify` hook 우회 금지.
2. **Artifact commit** (`chore`): `.claude/tasks/done/task-{N}-*.md` + `.claude/runs/{TICKET}/`.

자동 push / PR 생성 없음 (사용자 수동).

#### task 파일 형식

`templates/workflow-contract/task.schema.md` 의 6 Required Sections:
1. 사용자 최초 프롬프트 원문 (`plan.md` frontmatter `user_prompt` 원문 복사 — 요약 금지)
2. 사전 준비 (읽어야 할 파일 표)
3. 작업 내용
4. Acceptance Criteria (실행 가능 bash — zero exit = pass. 추상 서술 금지)
5. 주의사항 ("X 하지 마라. 이유: Y" 형식 — 이유 누락 시 무효)
6. On completion (result 파일 경로 + result.schema.md 링크)

#### Common Preamble (7항)

매 role 호출 직전 runner가 task 본문 앞에 prepend. 7가지 규칙 SSOT: `templates/workflow-contract/preamble.md`.

7번 규칙: 자동 commit/push/PR 금지 — implementer 에이전트의 자동 commit 금지 (orchestrator의 통제된 commit은 허용). SSOT 상세: `templates/workflow-contract/contract.md` §Common Preamble.

#### 핑퐁 라우팅

reviewer가 `needs-fix` 반환 시:
- **p1 / p2** 이슈만 implementer에 전달 (ping-pong 비용 절감).
- **p3 / p4** 이슈는 result `<handoff>` 에 follow-up 라인으로 기록 — implementer에 전달 안 함.
- max 3 rounds. 3회 후에도 p1/p2 미해결 → 사용자 에스컬레이션.
- 사용자 deferral: result `<decisions>` 의 `deferred:` 라인 또는 사용자 명시 메시지.

reviewer가 `approved` 반환 후 p3/p4 잔류 시: `<handoff>` 에 follow-up 기록하고 진행.

#### Self-report 검증 (자동 강등)

runner 종료 후 orchestrator가 모든 result frontmatter `status` 확인. `pending` / `in-progress` 잔류 시 **auto-demote**: `error` 로 강등하고 body에 `> auto-demoted: status was {original} at runner exit` 한 줄 추가. per-role 분리 환경에서도 동일 룰 적용.

### 디버그/분석 분기

`/impl`은 디버그(증상)·분석(이해) 요청도 처리. task 파일 작성 후 `debugger`(opus, read-only) 또는 `analyzer`(opus, read-only)로 위임. 결과 보고 후 필요하면 fix 모드로 진행.

## Runner 모델

| ID | 스크립트 | 기본 model | 비고 |
|---|---|---|---|
| `in-session` | (없음 — orchestrator 직접) | sonnet | 기본값 |
| `headless-claude` | `templates/workflow-contract/runners/claude/impl.sh` | sonnet | task-5b 신규 |
| `headless-codex` | `templates/workflow-contract/runners/codex/impl.sh` | (CLI 기본) | preamble prepend / fail-loud 일반화 |

종료 코드 0/1/2/3. exit 3 = codex 실패 (network/auth 등) — **자동 in-session fallback 금지**. 사용자에게 실패 출력 보여주고 명시적 재실행 요청.

**Status machine 6 상태**: `pending` / `in-progress` / `success` / `partial` / `failure` / `error`. 자동 강등 룰 포함. 상세: `templates/workflow-contract/contract.md` §Status Machine.

## reviewer / md-reviewer

### reviewer (정의: `claude-config/agents/reviewer.md`)

출력 포맷 (`<review>` 내):
- `<issue priority="p1|p2|p3|p4">` + `<description>` / `<fix>` / `<side_effect>` 필수 + `<doc_ref>` 옵션 (yaml docs 인용 시)
- `side_effect`: 항상 필수. downstream 없으면 `none`.
- `doc_ref`: `docs_path` 설정 + 관련 항목 존재 시 ID 인용. 관련 없으면 태그 자체 생략.

priority 라우팅:
- `[p1]`: 항상 `needs-fix` → ping-pong
- `[p2]`: `needs-fix` (사용자가 명시 deferral하지 않은 한)
- `[p3]` / `[p4]`: non-blocking — `needs-fix` 설정 안 함

### md-reviewer (정의: `claude-config/agents/md-reviewer.md`)

reviewer와 같은 `priority` + `side_effect` 포맷. 5-rule 룰북: Redundancy / Verbosity / Lost-in-the-middle / Structure / Weak directives. XML 출력: `<md-review>` 내 동일 `<issue priority="p1|p2|p3|p4">` 구조.

## 산출물 위치

```
{repo}/
├── .claude/
│   ├── plans/{TICKET}/plan.md            spec-plan 산출물 (plan-v{N}.md 누적)
│   ├── tasks/
│   │   ├── pending/task-{N}-{name}.md    impl이 발행
│   │   ├── done/task-{N}-{name}-result.md   implementer/integrator 결과
│   │   ├── done/task-{N}-{name}-review.md   reviewer 결과 (task-6 신규)
│   │   └── failed/                       실패 시 격리
│   ├── runs/{TICKET}/                    인테그레이터·헤드리스 러너 산출물 루트
│   │   ├── diff.patch
│   │   ├── test-output.log
│   │   ├── manifest.yaml
│   │   ├── claude/                       headless-claude sidecar (선택)
│   │   └── codex/                        headless-codex sidecar (선택)
│   └── current-ticket                    impl 진행 중에만 존재. .gitignore 필수
├── templates/
│   ├── workflow-contract/
│   │   ├── preamble.md                   7항 SSOT (task-3 신규)
│   │   └── runners/
│   │       ├── claude/impl.sh            headless-claude 어댑터 (task-5b 신규)
│   │       ├── codex/impl.sh             headless-codex 어댑터
│   │       └── in-session/README.md      in-session 어댑터 문서
│   └── project-setup/docs/
│       ├── adr.yaml                      ADR 스켈레톤 (opt-in, task-7 신규)
│       └── conventions.yaml              Conventions 스켈레톤 (opt-in, task-7 신규)
├── claude-config/commands/
│   └── init-docs.md                      /init-docs 슬래시 커맨드 (task-7 신규)
└── CLAUDE.md                             ## Implementation Config 섹션 (선택)
```

## 에이전트 (정의: `claude-config/agents/*.md`)

| 에이전트 | 모델 | 역할 | 권한 | 비고 |
|---|---|---|---|---|
| `implementer` | sonnet | 코드 + 단위 테스트, 슬라이스 단위 커밋 | RW | 6 Required Sections task 형식 인식 (task-3) |
| `reviewer` | sonnet | 코드 품질·버그·엣지 검사 | read-only | `<issue priority="p1~p4">` + `side_effect` 필수 + `doc_ref` 옵션 (task-6/7) |
| `integrator` | sonnet | 통합 테스트, Quality Gates 평가 | RW | 6 Required Sections task 형식 인식 (task-3) |
| `debugger` | opus | 6-step 트리아지 (버그 원인 진단) | read-only | |
| `analyzer` | opus | 코드 구조·흐름 분석 | read-only | |
| `test-engineer` | sonnet | Strategy(spec-plan) / Coverage(standalone) 두 모드 | read-only | |
| `md-reviewer` | opus | 프롬프트 markdown 리뷰 | read-only | 동일 `priority` + `side_effect` 포맷, 5-rule 룰북 (task-6) |

## CLAUDE.md `## Implementation Config` (옵션)

| 키 | 용도 |
|---|---|
| `specs_path` | TechSpec 디렉토리 (Spec Agent) |
| `prd_path` | PRD 디렉토리 (Spec Agent) |
| `policies_path` | 정책 문서 (Spec Agent) |
| `log_repo` | impl-logs 동기화 대상 |
| `docs_path` | 구조화 docs 디렉토리 (`.claude/docs/` 기본, `adr.yaml`/`conventions.yaml` 사용 시). `/init-docs` 로 초기화 (task-7) |
| `format_command` | pre-commit hook용 |
| `build_command` | pre-PR hook용 |
| `test_command` | pre-PR hook용 |

설정 없으면 Spec / Context Agent 생략, hooks도 생략 가능 (각 hook은 명령이 없으면 no-op). `docs_path` 미설정 시 Spec Agent는 평문 fallback.

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

본 plan 의 task-2~9 는 2026-05-08 시점 머지 완료 (또는 머지 대기) 상태. 다음 작업은 plan.md §Open Questions 5건 + future-ideas.md 의 trigger 조건이 충족되었을 때.

## 관련 문서

| 문서 | 내용 |
|---|---|
| [spec-plan-spec.md](spec-plan-spec.md) | spec-plan 한국어 요약 (의도) |
| [hooks-spec.md](hooks-spec.md) | hook 스크립트 + settings.json |
| [ue-test-strategy.md](ue-test-strategy.md) | 언리얼 테스트 계층 |
| [future-context-central.md](future-context-central.md) | context-central MCP 연동(예정) |
| [future-ideas.md](future-ideas.md) | plan.md 의도적 제외 + 미흡수 아이디어 |
| [_archive/phase0-codex/](_archive/phase0-codex/) | Phase 0 Codex parity 작업 이력 |
