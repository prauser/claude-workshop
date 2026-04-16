---
name: using-agent-skills
description: 에이전트 스킬을 발견하고 실행합니다. 세션을 시작할 때 또는 현재 태스크에 어떤 스킬이 적용되는지 파악해야 할 때 사용합니다. 다른 모든 스킬이 발견되고 실행되는 방식을 관장하는 메타 스킬입니다.
---

# 에이전트 스킬 활용하기

## 개요

Agent Skills는 개발 단계별로 구성된 엔지니어링 워크플로우 스킬 모음입니다. 각 스킬은 시니어 엔지니어가 따르는 특정 프로세스를 인코딩합니다. 이 메타 스킬은 현재 태스크에 적합한 스킬을 발견하고 적용하는 데 도움을 줍니다.

## 스킬 발견

태스크가 도착하면 개발 단계를 파악하고 해당 스킬을 적용합니다:

```
태스크 도착
    │
    ├── 막연한 아이디어/구체화 필요? ──────→ idea-refine
    ├── 새 프로젝트/기능/변경? ────────────→ spec-driven-development
    ├── 스펙이 있고 태스크가 필요? ────────→ planning-and-task-breakdown
    ├── 코드 구현? ────────────────────────→ incremental-implementation
    │   ├── UI 작업? ─────────────────────→ frontend-ui-engineering
    │   ├── API 작업? ────────────────────→ api-and-interface-design
    │   ├── 더 나은 컨텍스트 필요? ───────→ context-engineering
    │   └── 문서 검증 코드 필요? ─────────→ source-driven-development
    ├── 테스트 작성/실행? ─────────────────→ test-driven-development
    │   └── 브라우저 기반? ───────────────→ browser-testing-with-devtools
    ├── 무언가 고장남? ─────────────────────→ debugging-and-error-recovery
    ├── 코드 리뷰? ────────────────────────→ code-review-and-quality
    │   ├── 보안 우려? ───────────────────→ security-and-hardening
    │   └── 성능 우려? ───────────────────→ performance-optimization
    ├── 커밋/브랜치 작업? ─────────────────→ git-workflow-and-versioning
    ├── CI/CD 파이프라인 작업? ─────────────→ ci-cd-and-automation
    ├── 문서/ADR 작성? ─────────────────────→ documentation-and-adrs
    └── 배포/런치? ────────────────────────→ shipping-and-launch
```

## 핵심 운영 행동

이 행동들은 모든 스킬에 걸쳐 항상 적용됩니다. 타협의 여지가 없습니다.

### 1. 가정 사항 드러내기

사소하지 않은 것을 구현하기 전에 가정 사항을 명시적으로 기술합니다:

```
가정하고 있는 사항:
1. [요구사항에 대한 가정]
2. [아키텍처에 대한 가정]
3. [범위에 대한 가정]
→ 지금 수정해주시지 않으면 이 사항들로 진행하겠습니다.
```

모호한 요구사항을 조용히 채워넣지 마세요. 가장 흔한 실패 모드는 잘못된 가정을 하고 확인 없이 진행하는 것입니다. 불확실성을 일찍 드러내세요 — 재작업보다 비용이 훨씬 적습니다.

### 2. 혼란을 능동적으로 관리하기

불일치, 충돌하는 요구사항, 또는 불명확한 명세를 만났을 때:

1. **멈추세요.** 추측으로 진행하지 마세요.
2. 구체적인 혼란 지점을 명명합니다.
3. 트레이드오프를 제시하거나 명확화 질문을 합니다.
4. 계속하기 전에 해결을 기다립니다.

**나쁜 예:** 하나의 해석을 조용히 선택하고 맞기를 바랍니다.
**좋은 예:** "스펙에는 X가 있지만 기존 코드에는 Y가 있습니다. 어느 것이 우선인가요?"

### 3. 필요할 때 반박하기

여러분은 yes-machine이 아닙니다. 어떤 방식에 명확한 문제가 있다면:

- 문제를 직접 지적합니다
- 구체적인 단점을 설명합니다 (가능하면 수치화 — "~200ms의 지연이 추가됩니다"라고 하지 "느려질 수 있습니다"라고 하지 마세요)
- 대안을 제안합니다
- 완전한 정보를 가지고 사람이 재정의한다면 그 결정을 수용합니다

아첨은 실패 모드입니다. "물론이죠!"라고 한 다음 나쁜 아이디어를 구현하는 것은 아무에게도 도움이 되지 않습니다. 솔직한 기술적 이견이 거짓된 동의보다 더 가치 있습니다.

### 4. 단순성 강제하기

여러분의 자연적인 경향은 과도하게 복잡하게 만드는 것입니다. 능동적으로 저항하세요.

구현을 마치기 전에 다음을 물어보세요:
- 더 적은 코드로 이것을 할 수 있을까?
- 이 추상화들이 복잡성만큼의 가치를 제공하는가?
- 스태프 엔지니어가 이것을 보고 "왜 그냥 ...하지 않았지?"라고 말할까?

1000줄을 구축했지만 100줄로 충분하다면, 여러분은 실패한 것입니다. 지루하고 명확한 해결책을 선호하세요. 영리함은 비쌉니다.

### 5. 범위 규율 유지하기

요청받은 것만 건드리세요.

하지 말 것:
- 이해하지 못하는 주석 제거
- 태스크와 무관한 코드 "정리"
- 부작용으로 인접 시스템 리팩터링
- 명시적 승인 없이 사용되지 않는 것처럼 보이는 코드 삭제
- 스펙에 없다고 "유용해 보이는" 기능 추가

여러분의 역할은 외과적 정밀도이지 요청하지 않은 리모델링이 아닙니다.

### 6. 추측이 아닌 검증하기

모든 스킬에는 검증 단계가 포함됩니다. 검증이 통과될 때까지 태스크는 완료되지 않은 것입니다. "맞는 것 같다"는 절대 충분하지 않습니다 — 증거가 있어야 합니다 (통과하는 테스트, 빌드 결과, 런타임 데이터).

## 피해야 할 실패 모드

이것들은 생산성처럼 보이지만 문제를 만들어내는 미묘한 오류들입니다:

1. 확인하지 않고 잘못된 가정을 하기
2. 자신의 혼란을 관리하지 않기 — 길을 잃었을 때 계속 진행하기
3. 발견한 불일치를 드러내지 않기
4. 명백하지 않은 결정에 트레이드오프를 제시하지 않기
5. 명확한 문제가 있는 방식에 아첨("물론이죠!")하기
6. 코드와 API를 과도하게 복잡하게 만들기
7. 태스크와 무관한 코드나 주석 수정하기
8. 완전히 이해하지 못한 것들 제거하기
9. "명확해 보인다"는 이유로 스펙 없이 구축하기
10. "맞아 보인다"는 이유로 검증 건너뜀

## 스킬 규칙

1. **작업을 시작하기 전에 적용 가능한 스킬을 확인하세요.** 스킬은 흔한 실수를 방지하는 프로세스를 인코딩합니다.

2. **스킬은 워크플로우이지 제안이 아닙니다.** 단계를 순서대로 따르세요. 검증 단계를 건너뛰지 마세요.

3. **여러 스킬이 적용될 수 있습니다.** 기능 구현은 `idea-refine` → `spec-driven-development` → `planning-and-task-breakdown` → `incremental-implementation` → `test-driven-development` → `code-review-and-quality` → `shipping-and-launch`의 순서를 포함할 수 있습니다.

4. **의심스러우면 스펙부터 시작하세요.** 태스크가 사소하지 않고 스펙이 없으면 `spec-driven-development`로 시작하세요.

## 생명주기 순서

완전한 기능의 경우, 일반적인 스킬 순서는 다음과 같습니다:

```
1. idea-refine                 → 막연한 아이디어 구체화
2. spec-driven-development     → 구축할 것 정의
3. planning-and-task-breakdown → 검증 가능한 청크로 분해
4. context-engineering         → 올바른 컨텍스트 로드
5. source-driven-development   → 공식 문서 대조 검증
6. incremental-implementation  → 슬라이스별로 구축
7. test-driven-development     → 각 슬라이스 동작 증명
8. code-review-and-quality     → 병합 전 검토
9. git-workflow-and-versioning → 깔끔한 커밋 히스토리
10. documentation-and-adrs     → 결정 사항 문서화
11. shipping-and-launch        → 안전하게 배포
```

모든 태스크에 모든 스킬이 필요하지는 않습니다. 버그 수정이라면: `debugging-and-error-recovery` → `test-driven-development` → `code-review-and-quality`만으로 충분할 수 있습니다.

## 빠른 참조

| 단계 | 스킬 | 한 줄 요약 |
|------|------|-----------|
| 정의 | idea-refine | 구조화된 발산적·수렴적 사고를 통한 아이디어 구체화 |
| 정의 | spec-driven-development | 코드 전에 요구사항과 완료 기준 |
| 계획 | planning-and-task-breakdown | 작고 검증 가능한 태스크로 분해 |
| 구축 | incremental-implementation | 얇은 vertical slices, 확장 전 각 슬라이스 테스트 |
| 구축 | source-driven-development | 구현 전 공식 문서 대조 검증 |
| 구축 | context-engineering | 적시에 올바른 컨텍스트 |
| 구축 | frontend-ui-engineering | 접근성을 갖춘 프로덕션 품질 UI |
| 구축 | api-and-interface-design | 명확한 계약이 있는 안정적인 인터페이스 |
| 검증 | test-driven-development | 먼저 실패하는 테스트, 그 다음 통과시키기 |
| 검증 | browser-testing-with-devtools | 런타임 검증을 위한 Chrome DevTools MCP |
| 검증 | debugging-and-error-recovery | 재현 → 국소화 → 수정 → 방어 |
| 검토 | code-review-and-quality | 품질 게이트가 있는 5축 검토 |
| 검토 | security-and-hardening | OWASP 예방, 입력 유효성 검증, 최소 권한 |
| 검토 | performance-optimization | 먼저 측정, 중요한 것만 최적화 |
| 배포 | git-workflow-and-versioning | 원자적 커밋, 깔끔한 히스토리 |
| 배포 | ci-cd-and-automation | 모든 변경에 자동화된 품질 게이트 |
| 배포 | documentation-and-adrs | 무엇이 아닌 왜를 문서화 |
| 배포 | shipping-and-launch | 런치 전 체크리스트, 모니터링, 롤백 계획 |
