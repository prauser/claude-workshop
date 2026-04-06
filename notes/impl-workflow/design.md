# 구현 워크플로우 설계 개요

> 상태: 설계 완료, 구현 대기 | 2026-04-06
> 원본 설계 문서: `studio-docs/output/docs/002~006_design-impl-*.md`

## 목적

Jira 티켓 하나를 입력하면, 플래닝 → 구현 → 테스트 → 리뷰 → PR까지 자동으로 진행하는 워크플로우.
기존 `/orchestrate` 위에 플래닝 레이어(`/implement`)를 얹고, Hook으로 품질 게이트를 자동화한다.

---

## 파이프라인 위치

SETUP_GUIDE의 목표 파이프라인에서 `/implement`의 위치:

```
요구사항 → /brainstorm (PRD) → /design (TechSpec) → /implement (플래닝) → /orchestrate (구현) → /review (검증)
                                                      ^^^^^^^^^^
                                                      이번에 만드는 것
```

`/implement`는 PRD/TechSpec이 이미 있는 상태에서, Jira 티켓 기반으로 구현 플랜을 세우고 `/orchestrate`에 넘긴다.

---

## 각 레포별 배치

### claude-workshop → ~/.claude/ (user scope, 모든 레포 공통)

워크플로우 구조와 범용 에이전트. `deploy.sh`로 `~/.claude/`에 배포.

```
claude-config/
├── commands/
│   ├── orchestrate.md       기존 유지. 실행 엔진.
│   ├── implement.md         ★ 신규. 플래닝 + orchestrate 호출.
│   └── cost-report.md       기존 유지. 비용 추적.
└── agents/
    ├── implementer.md       기존 유지. 코드+테스트 작성 (sonnet).
    ├── reviewer.md          기존 유지. 코드 리뷰 (sonnet, 읽기전용).
    ├── integrator.md        기존 유지. 통합 테스트 (sonnet).
    ├── debugger.md          기존 유지. 버그 진단 (opus, 읽기전용).
    └── analyzer.md          기존 유지. 코드 분석 (opus, 읽기전용).
```

**플래닝용 에이전트는 별도 .md 파일 없음.**
→ `/implement` 커맨드 안에서 서브에이전트를 인라인 스폰.
→ 이유: 1회성 분석이라 반복 호출되지 않음. orchestrate의 에이전트들(implementer 등)과 다름.

**변경 요약:**
- 신규 파일: `commands/implement.md` (1개)
- 기존 파일 변경: 없음

### 각 프로젝트 레포 — sandbox, client 등 (project scope)

레포별 테스트 명령, 린터, 경로 설정. 코드 레포 안에서 관리.

```
{repo}/
├── CLAUDE.md                    ★ Implementation Config 섹션 추가
└── .claude/
    ├── settings.json            ★ 신규. hooks 설정.
    └── hooks/                   ★ 신규. 품질 게이트 + 로깅 스크립트.
        ├── log-agent-usage.sh       Agent 호출 시 토큰 기록
        ├── log-file-change.sh       코드 변경 기록
        ├── run-related-tests.sh     편집 후 관련 테스트 실행
        ├── pre-commit-lint.sh       커밋 전 린트
        └── sync-logs.sh            완료 후 impl-logs로 동기화
```

**CLAUDE.md의 Implementation Config**:
`/implement` 커맨드가 이 섹션을 읽어서 프로젝트별 경로를 파악함.
```yaml
specs_path: ../studio-docs/output/specs/
prd_path: ../studio-docs/output/prd/
policies_path: ../studio-docs/policies/
test_command: ...  (레포별 다름)
lint_command: ...  (레포별 다름)
log_repo: ../impl-logs
```

### impl-logs (전용 로그 레포)

모든 레포, 모든 작업자의 구현 로그를 중앙 저장.
워크플로우 자체의 디버깅과 회고에 사용.

```
impl-logs/
├── README.md                    목적, 구조, 사용법
├── INDEX.md                     전체 작업 인덱스
├── sandbox/                     sandbox 레포 작업 로그
│   └── {TICKET}/
│       ├── plan.md              확정 플랜
│       ├── metrics.jsonl        토큰·시간 원시 데이터
│       ├── changes.jsonl        파일 변경 기록
│       ├── steps/               태스크별 결과
│       ├── quality.md           품질 메트릭 (5축)
│       ├── summary.md           토큰·비용 요약
│       └── retro.md             회고 (선택)
└── client/                      client 레포 작업 로그
    └── {TICKET}/
```

### studio-docs (변경 없음, 참조만)

`/implement`가 읽어가는 소스:
- `output/prd/{기능명}.md` — PRD
- `output/specs/{기능명}.md` — TechSpec
- `policies/` — 정책 문서

설계 문서 보관: `output/docs/002~006_design-impl-*.md`

---

## 흐름 요약

```
사용자: cd ~/sbx-work/sandbox && claude
사용자: /implement OVDR-1234

  /implement (user scope)
  ├── CLAUDE.md에서 Implementation Config 읽기
  ├── 서브에이전트 4개 병렬: Jira · Spec · Code · Context
  ├── 플랜 초안 → 핑퐁 리뷰 → 사용자 확인
  └── 플랜 확정 → /orchestrate 자동 호출

  /orchestrate (user scope)
  ├── 태스크 분해 → .claude/tasks/pending/
  ├── implementer → [Hook: auto-test] → reviewer → done
  ├── integrator → 통합 테스트
  └── Final report

  Hooks (project scope, 자동)
  ├── 매 편집: 관련 테스트 실행 + 변경 로깅
  ├── 매 Agent 호출: 토큰 로깅
  ├── 매 커밋: 린트
  └── 완료 후: impl-logs/ 동기화
```

---

## graduation 경로 (claude-workshop)

```
notes/impl-workflow/        ← 지금 여기 (설계)
  ↓
experiments/impl-workflow/  ← 다음 (실제 테스트)
  ↓
templates/impl-workflow/    ← 검증 통과
  ↓
claude-config/commands/     ← deploy.sh → ~/.claude/
```

---

## 관련 문서

| 문서 | 위치 | 내용 |
|------|------|------|
| [implement 커맨드 스펙](implement-spec.md) | claude-workshop/notes/ | /implement 동작 상세 |
| [Hook 스크립트 스펙](hooks-spec.md) | claude-workshop/notes/ | Hook 설정 + 스크립트 상세 |
| 원본 설계 문서 002~006 | studio-docs/output/docs/ | 배경, 기능 매핑, 메트릭, Agent Teams |
