# 구현 워크플로우 설계 개요

> 상태: 설계 완료, 구현 대기 | 2026-04-06
> 원본 설계 문서: `studio-docs/output/docs/002~006_design-impl-*.md`

## 목적

Jira 티켓 → 플래닝 → 구현 → 테스트 → 리뷰 → PR 자동화.
`/spec-plan`(플래닝) + `/impl`(구현) + Hook(품질 게이트).

## 파이프라인

```
/brainstorm (PRD) → /design (TechSpec) → /spec-plan (플래닝) → /impl (구현) → /review (검증)
                                          ^^^^^^^^^^
                                          이번에 만드는 것
```

---

## 레포별 배치

### claude-workshop → ~/.claude/ (user scope)

```
claude-config/
├── commands/
│   ├── impl.md          구현 실행 엔진
│   ├── spec-plan.md     ★ 신규. 플래닝
│   └── cost-report.md   비용 추적
└── agents/
    ├── implementer.md   코드+테스트 (sonnet)
    ├── reviewer.md      코드 리뷰 (sonnet, 읽기전용)
    ├── integrator.md    통합 테스트 (sonnet)
    ├── debugger.md      버그 진단 (opus, 읽기전용)
    ├── analyzer.md      코드 분석 (opus, 읽기전용)
    └── md-reviewer.md   프롬프트 MD 리뷰 (opus, 읽기전용)
```

플래닝용 에이전트는 `/spec-plan` 안에서 인라인 스폰 (1회성).

### 각 프로젝트 레포 (project scope)

```
{repo}/
├── CLAUDE.md                    Implementation Config 섹션
└── .claude/
    ├── settings.json            hooks 설정
    ├── plans/{TICKET}/          ★ plan.md 저장 (spec-plan이 생성)
    └── hooks/
        ├── pre-commit-format.sh 커밋 전 포맷 체크
        ├── pre-pr-validate.sh   PR 전 빌드+테스트
        └── sync-logs.sh         impl-logs 동기화
```

**Implementation Config** (CLAUDE.md):
```yaml
specs_path: ../studio-docs/output/specs/
prd_path: ../studio-docs/output/prd/
policies_path: ../studio-docs/policies/
format_command: ...
build_command: ...
test_command: ...
log_repo: ../impl-logs
```

### impl-logs (로그 레포)

sync-logs.sh로 동기화. 실시간이 아닌 impl 완료 후 일괄.

```
impl-logs/{repo_name}/{TICKET}/
├── plan.md          플랜 (프로젝트 레포에서 복사)
├── steps/           태스크별 결과
├── quality.md       품질 메트릭
├── summary.md       비용 요약
└── retro.md         회고 (선택)
```

---

## 흐름 요약

```
/spec-plan OVDR-1234
  ├── Implementation Config 읽기
  ├── 서브에이전트 4개 병렬: Jira · Spec · Code · Context
  ├── 플랜 초안 → 핑퐁 리뷰 → 사용자 확인
  └── .claude/plans/OVDR-1234/plan.md 저장 → 종료

사용자: /impl OVDR-1234

/impl
  ├── .claude/plans/OVDR-1234/plan.md 읽기 → 태스크 분해
  ├── implementer → reviewer → done
  ├── integrator → 통합 테스트
  └── Final report → sync-logs.sh 안내

Hooks (품질 게이트만)
  ├── 매 커밋: 포맷 체크
  └── PR 생성 전: 빌드 + 테스트

로깅: session jsonl 후처리 (Hook으로 쌓지 않음)
```

---

## graduation 경로

```
notes/impl-workflow/        ← 설계
experiments/impl-workflow/  ← 실험
templates/impl-workflow/    ← 검증 통과
claude-config/commands/     ← deploy.sh → ~/.claude/
```

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| [spec-plan-spec.md](spec-plan-spec.md) | /spec-plan 동작 상세 |
| [hooks-spec.md](hooks-spec.md) | Hook 설정 + 스크립트 |
| [future-context-central.md](future-context-central.md) | 향후 context-central 연동 |
| 원본 002~006 (studio-docs) | 배경, 기능 매핑, 메트릭 |
