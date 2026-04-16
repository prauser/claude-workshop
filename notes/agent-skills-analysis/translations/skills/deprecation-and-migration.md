---
name: deprecation-and-migration
description: Manages deprecation and migration. Use when removing old systems, APIs, or features. Use when migrating users from one implementation to another. Use when deciding whether to maintain or sunset existing code.
---

# Deprecation and Migration

## Overview

코드는 자산이 아니라 부채다. 모든 코드 라인은 지속적인 유지보수 비용을 수반한다 — 수정해야 할 버그, 업데이트해야 할 의존성, 적용해야 할 보안 패치, 그리고 온보딩해야 할 신규 엔지니어들. Deprecation(더 이상 사용하지 않음 처리)은 더 이상 가치를 창출하지 못하는 코드를 제거하는 규율이며, migration(마이그레이션)은 사용자를 구 시스템에서 신 시스템으로 안전하게 이전하는 과정이다.

대부분의 엔지니어링 조직은 무언가를 만드는 데는 능숙하다. 하지만 제거하는 데는 그렇지 않다. 이 skill은 그 격차를 해소한다.

## When to Use

- 오래된 시스템, API, 또는 라이브러리를 새로운 것으로 교체할 때
- 더 이상 필요하지 않은 기능을 종료할 때
- 중복 구현을 통합할 때
- 아무도 소유하지 않지만 모든 사람이 의존하는 dead code를 제거할 때
- 새로운 시스템의 수명 주기를 계획할 때 (deprecation 계획은 설계 시점에 시작됨)
- 레거시 시스템을 유지할지 마이그레이션에 투자할지 결정할 때

## Core Principles

### 코드는 부채다

모든 코드 라인에는 지속적인 비용이 따른다: 테스트, 문서화, 보안 패치, 의존성 업데이트, 그리고 근처에서 작업하는 모든 사람의 정신적 부담이 필요하다. 코드의 가치는 코드 자체가 아니라 제공하는 기능에 있다. 동일한 기능을 더 적은 코드, 더 낮은 복잡성, 또는 더 나은 추상화로 제공할 수 있다면 — 기존 코드는 제거되어야 한다.

### Hyrum의 법칙이 제거를 어렵게 만든다

충분한 사용자가 있으면, 모든 관찰 가능한 동작이 의존 대상이 된다 — 버그, 타이밍 특성, 문서화되지 않은 부작용까지 포함해서. 이것이 deprecation이 단순한 공지가 아니라 능동적인 마이그레이션을 필요로 하는 이유다. 사용자들은 교체품이 복제하지 않는 동작에 의존하고 있을 때 "그냥 전환"할 수 없다.

### Deprecation 계획은 설계 시점에 시작된다

새로운 것을 만들 때 다음을 자문하라: "3년 후에 이것을 어떻게 제거할 것인가?" 깔끔한 인터페이스, feature flag, 최소한의 노출 표면을 갖도록 설계된 시스템은 구현 세부 사항을 곳곳에 노출하는 시스템보다 deprecate하기 쉽다.

## The Deprecation Decision

무엇이든 deprecate하기 전에 다음 질문에 답하라:

```
1. 이 시스템이 아직 고유한 가치를 제공하는가?
   → 그렇다면 유지한다. 아니라면 계속 진행한다.

2. 얼마나 많은 사용자/소비자가 의존하는가?
   → 마이그레이션 범위를 정량화한다.

3. 교체품이 존재하는가?
   → 없다면, 먼저 교체품을 만든다. 대안 없이 deprecate하지 않는다.

4. 각 소비자의 마이그레이션 비용은 얼마인가?
   → 자동화하기 trivial하다면 그렇게 한다. 수동이고 많은 노력이 필요하다면 유지보수 비용과 비교 검토한다.

5. Deprecate하지 않을 경우의 지속적인 유지보수 비용은 얼마인가?
   → 보안 위험, 엔지니어 시간, 복잡성으로 인한 기회 비용.
```

## Compulsory vs Advisory Deprecation

| 유형 | 사용 시점 | 방식 |
|------|-----------|------|
| **Advisory** | 마이그레이션이 선택 사항이고 구 시스템이 안정적인 경우 | 경고, 문서화, 권고. 사용자가 자신의 일정에 따라 마이그레이션한다. |
| **Compulsory** | 구 시스템에 보안 문제가 있거나, 진행을 막거나, 유지보수 비용이 지속 불가능한 경우 | 강제 마감일. 구 시스템은 X 날짜까지 제거될 것이다. 마이그레이션 도구를 제공한다. |

**기본값은 advisory다.** 유지보수 비용이나 위험이 마이그레이션 강제를 정당화할 때만 compulsory를 사용한다. Compulsory deprecation은 마이그레이션 도구, 문서화, 지원을 제공해야 한다 — 단순히 마감일을 공지할 수 없다.

## The Migration Process

### Step 1: 교체품 구축

작동하는 대안 없이 deprecate하지 않는다. 교체품은 반드시:

- 구 시스템의 모든 중요한 사용 사례를 포함해야 한다
- 문서화와 마이그레이션 가이드가 있어야 한다
- 프로덕션에서 검증되어야 한다 ("이론적으로 더 낫다"가 아닌)

### Step 2: 공지 및 문서화

```markdown
## Deprecation Notice: OldService

**Status:** 2025-03-01부로 deprecated
**교체품:** NewService (아래 마이그레이션 가이드 참조)
**제거 날짜:** Advisory — 아직 강제 마감일 없음
**이유:** OldService는 수동 스케일링이 필요하고 가시성이 부족하다.
          NewService는 두 가지를 자동으로 처리한다.

### 마이그레이션 가이드
1. `import { client } from 'old-service'`를 `import { client } from 'new-service'`로 교체
2. 설정 업데이트 (아래 예시 참조)
3. 마이그레이션 검증 스크립트 실행: `npx migrate-check`
```

### Step 3: 점진적 마이그레이션

소비자를 한 번에 모두가 아닌 하나씩 마이그레이션한다. 각 소비자에 대해:

```
1. deprecated 시스템과의 모든 접점 파악
2. 교체품을 사용하도록 업데이트
3. 동작이 일치하는지 확인 (테스트, 통합 검사)
4. 구 시스템에 대한 참조 제거
5. 회귀가 없는지 확인
```

**Churn Rule:** deprecated되는 인프라를 소유하고 있다면, 사용자를 마이그레이션하거나 — 마이그레이션이 필요 없는 하위 호환 업데이트를 제공할 책임이 있다. Deprecation을 공지하고 사용자가 알아서 해결하도록 내버려 두지 않는다.

### Step 4: 구 시스템 제거

모든 소비자가 마이그레이션한 후에만:

```
1. 활성 사용이 없음을 확인 (메트릭, 로그, 의존성 분석)
2. 코드 제거
3. 관련 테스트, 문서화, 설정 제거
4. Deprecation 공지 제거
5. 축하 — 코드 제거는 성과다
```

## Migration Patterns

### Strangler Pattern

구 시스템과 새 시스템을 병렬로 실행한다. 구에서 새로 트래픽을 점진적으로 라우팅한다. 구 시스템이 0%의 트래픽을 처리하면 제거한다.

```
Phase 1: 새 시스템 0%, 구 시스템 100%
Phase 2: 새 시스템 10% (카나리)
Phase 3: 새 시스템 50%
Phase 4: 새 시스템 100%, 구 시스템 유휴
Phase 5: 구 시스템 제거
```

### Adapter Pattern

구 인터페이스에서 새 구현으로 호출을 변환하는 어댑터를 만든다. 소비자들은 백엔드를 마이그레이션하는 동안 구 인터페이스를 계속 사용한다.

```typescript
// 어댑터: 구 인터페이스, 새 구현
class LegacyTaskService implements OldTaskAPI {
  constructor(private newService: NewTaskService) {}

  // 구 메서드 시그니처, 새 구현에 위임
  getTask(id: number): OldTask {
    const task = this.newService.findById(String(id));
    return this.toOldFormat(task);
  }
}
```

### Feature Flag Migration

Feature flag를 사용하여 소비자를 하나씩 구 시스템에서 새 시스템으로 전환한다:

```typescript
function getTaskService(userId: string): TaskService {
  if (featureFlags.isEnabled('new-task-service', { userId })) {
    return new NewTaskService();
  }
  return new LegacyTaskService();
}
```

## Zombie Code

Zombie code는 아무도 소유하지 않지만 모든 사람이 의존하는 코드다. 적극적으로 유지보수되지 않고, 명확한 소유자나 팀이 없으며, 보안 취약점과 호환성 문제가 누적된다. 징후:

- 6개월 이상 커밋이 없지만 활성 소비자가 존재
- 지정된 관리자나 팀 없음
- 아무도 수정하지 않는 실패한 테스트
- 아무도 업데이트하지 않는 알려진 취약점이 있는 의존성
- 더 이상 존재하지 않는 시스템을 참조하는 문서화

**대응:** 소유자를 지정하고 제대로 유지보수하거나, 구체적인 마이그레이션 계획과 함께 deprecate한다. Zombie code는 방치 상태로 남아 있을 수 없다 — 투자를 받거나 제거되어야 한다.

## Common Rationalizations

| 합리화 | 현실 |
|--------|------|
| "아직 작동하는데 왜 제거하는가?" | 아무도 유지보수하지 않는 작동하는 코드는 보안 부채와 복잡성을 쌓는다. 유지보수 비용은 조용히 증가한다. |
| "나중에 필요할 수도 있다" | 나중에 필요하다면 다시 만들 수 있다. 혹시 몰라 사용하지 않는 코드를 유지하는 것은 다시 만드는 것보다 더 비용이 많이 든다. |
| "마이그레이션 비용이 너무 비싸다" | 2-3년에 걸친 지속적인 유지보수 비용과 마이그레이션 비용을 비교하라. 마이그레이션이 장기적으로는 보통 더 저렴하다. |
| "새 시스템을 완성한 후에 deprecate할 것이다" | Deprecation 계획은 설계 시점에 시작된다. 새 시스템이 완성될 때쯤이면 새로운 우선순위가 생겨 있을 것이다. 지금 계획하라. |
| "사용자들이 스스로 마이그레이션할 것이다" | 그러지 않는다. 도구, 문서화, 인센티브를 제공하거나 — 직접 마이그레이션을 수행하라 (Churn Rule). |
| "두 시스템을 무기한 유지할 수 있다" | 동일한 기능을 하는 두 시스템은 유지보수, 테스트, 문서화, 온보딩 비용이 두 배다. |

## Red Flags

- 대안 없이 deprecated된 시스템
- 마이그레이션 도구나 문서화 없는 deprecation 공지
- 수년 동안 advisory 상태로 진전 없는 "소프트" deprecation
- 소유자 없이 활성 소비자가 있는 zombie code
- Deprecated된 시스템에 추가되는 새 기능 (교체품에 투자하라)
- 현재 사용량 측정 없이 deprecation
- 활성 소비자가 없음을 확인하지 않고 코드 제거

## Verification

Deprecation 완료 후:

- [ ] 교체품이 프로덕션에서 검증되었고 모든 중요한 사용 사례를 포함한다
- [ ] 구체적인 단계와 예시가 있는 마이그레이션 가이드가 존재한다
- [ ] 모든 활성 소비자가 마이그레이션되었다 (메트릭/로그로 확인)
- [ ] 구 코드, 테스트, 문서화, 설정이 완전히 제거되었다
- [ ] 코드베이스에 deprecated 시스템에 대한 참조가 남아 있지 않다
- [ ] Deprecation 공지가 제거되었다 (목적을 다했다)
