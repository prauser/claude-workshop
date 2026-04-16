---
name: code-simplification
description: 명확성을 위해 코드를 단순화합니다. 동작을 변경하지 않고 명확성을 위해 코드를 리팩토링할 때 사용하세요. 코드가 동작하지만 읽고, 유지관리하고, 확장하기가 필요 이상으로 어려울 때 사용하세요. 불필요한 복잡성이 축적된 코드를 리뷰할 때 사용하세요.
---

# Code Simplification

> [Claude Code Simplifier plugin](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-simplifier/agents/code-simplifier.md)에서 영감을 받았습니다. 여기서 모든 AI 코딩 에이전트를 위한 모델에 구애받지 않는, 프로세스 중심의 스킬로 개편되었습니다.

## 개요

정확한 동작을 보존하면서 복잡성을 줄임으로써 코드를 단순화하세요. 목표는 더 적은 줄이 아닙니다 — 읽고, 이해하고, 수정하고, 디버그하기 더 쉬운 코드입니다. 모든 단순화는 간단한 테스트를 통과해야 합니다: "새 팀원이 원본보다 이것을 더 빨리 이해할 수 있는가?"

## 언제 사용할까

- 기능이 동작하고 테스트가 통과한 후, 하지만 구현이 필요 이상으로 무겁게 느껴질 때
- 가독성 또는 복잡성 문제가 플래그된 코드 리뷰 중
- 깊이 중첩된 로직, 긴 함수, 또는 불명확한 이름을 발견했을 때
- 시간 압박 하에 작성된 코드를 리팩토링할 때
- 파일 전체에 분산된 관련 로직을 통합할 때
- 중복 또는 불일치를 도입한 변경을 머지한 후

**사용하지 않을 때:**

- 코드가 이미 깨끗하고 읽기 쉬울 때 — 단순화를 위한 단순화는 하지 마세요
- 코드가 무엇을 하는지 아직 이해하지 못했을 때 — 단순화하기 전에 이해하세요
- 코드가 성능 크리티컬하고 "더 단순한" 버전이 측정 가능하게 느릴 것 같을 때
- 모듈을 완전히 재작성하려는 경우 — 버려질 코드를 단순화하는 것은 노력 낭비입니다

## 다섯 가지 원칙

### 1. 동작을 정확히 보존

코드가 하는 것이 아닌 표현하는 방식만 변경하세요. 모든 입력, 출력, 사이드 이펙트, 에러 동작, 엣지 케이스는 동일하게 유지되어야 합니다. 단순화가 동작을 보존하는지 확실하지 않다면, 하지 마세요.

```
모든 변경 전에 질문:
→ 이것이 모든 입력에 대해 동일한 출력을 생성하는가?
→ 이것이 동일한 에러 동작을 유지하는가?
→ 이것이 동일한 사이드 이펙트와 순서를 보존하는가?
→ 수정 없이 모든 기존 테스트가 통과하는가?
```

### 2. 프로젝트 컨벤션 따르기

단순화는 코드를 코드베이스와 더 일관되게 만드는 것이지, 외부 선호도를 강요하는 것이 아닙니다. 단순화하기 전에:

```
1. CLAUDE.md / 프로젝트 컨벤션 읽기
2. 이웃하는 코드가 유사한 패턴을 어떻게 처리하는지 연구
3. 다음에 대한 프로젝트 스타일 맞추기:
   - Import 순서 및 모듈 시스템
   - 함수 선언 스타일
   - 네이밍 컨벤션
   - 에러 처리 패턴
   - 타입 어노테이션 깊이
```

프로젝트 일관성을 깨뜨리는 단순화는 단순화가 아닙니다 — 그것은 혼란입니다.

### 3. 영리함보다 명확성을 선호

콤팩트한 버전이 파싱하기 위해 정신적 멈춤을 필요로 할 때는 명시적인 코드가 콤팩트한 코드보다 낫습니다.

```typescript
// 불명확: 밀집된 삼항 연산자 체인
const label = isNew ? 'New' : isUpdated ? 'Updated' : isArchived ? 'Archived' : 'Active';

// 명확: 읽기 쉬운 매핑
function getStatusLabel(item: Item): string {
  if (item.isNew) return 'New';
  if (item.isUpdated) return 'Updated';
  if (item.isArchived) return 'Archived';
  return 'Active';
}
```

```typescript
// 불명확: 인라인 로직으로 체이닝된 reduce
const result = items.reduce((acc, item) => ({
  ...acc,
  [item.id]: { ...acc[item.id], count: (acc[item.id]?.count ?? 0) + 1 }
}), {});

// 명확: 명명된 중간 단계
const countById = new Map<string, number>();
for (const item of items) {
  countById.set(item.id, (countById.get(item.id) ?? 0) + 1);
}
```

### 4. 균형 유지

단순화에는 실패 모드가 있습니다: 과도한 단순화. 이 함정들을 주의하세요:

- **너무 공격적인 인라이닝** — 개념에 이름을 준 헬퍼를 제거하면 호출 지점이 읽기 어려워집니다
- **관련 없는 로직 결합** — 두 개의 단순한 함수를 하나의 복잡한 함수로 합치는 것은 더 단순하지 않습니다
- **"불필요한" 추상화 제거** — 일부 추상화는 복잡성이 아닌 확장성이나 테스트 가능성을 위해 존재합니다
- **라인 수 최적화** — 더 적은 줄이 목표가 아닙니다; 더 쉬운 이해가 목표입니다

### 5. 변경된 것으로 범위 제한

기본적으로 최근 수정된 코드를 단순화하세요. 범위를 명시적으로 확대하도록 요청받지 않는 한 관련 없는 코드의 드라이브-바이 리팩토를 피하세요. 범위 없는 단순화는 diff에 노이즈를 만들고 의도하지 않은 회귀 위험이 있습니다.

## 단순화 프로세스

### 1단계: 건드리기 전에 이해하기 (Chesterton's Fence)

무언가를 변경하거나 제거하기 전에, 왜 존재하는지 이해하세요. 이것이 Chesterton's Fence입니다: 도로에 가로막고 있는 울타리를 보고 왜 있는지 이해하지 못한다면, 헐지 마세요. 먼저 이유를 이해하고, 그 이유가 아직도 적용되는지 결정하세요.

```
단순화하기 전에 답하세요:
- 이 코드의 책임은 무엇인가?
- 무엇이 이것을 호출하는가? 이것이 무엇을 호출하는가?
- 엣지 케이스와 에러 경로는 무엇인가?
- 예상 동작을 정의하는 테스트가 있는가?
- 왜 이렇게 작성되었을 수 있는가? (성능? 플랫폼 제약? 역사적 이유?)
- git blame 확인: 이 코드의 원래 컨텍스트는 무엇이었는가?
```

이것들에 답할 수 없다면, 아직 단순화할 준비가 안 된 것입니다. 더 많은 컨텍스트를 읽으세요.

### 2단계: 단순화 기회 파악

이 패턴들을 스캔하세요 — 각각은 모호한 냄새가 아닌 구체적인 신호입니다:

**구조적 복잡성:**

| 패턴 | 신호 | 단순화 |
|---------|--------|----------------|
| 깊은 중첩 (3+ 레벨) | 제어 흐름 따라가기 어려움 | 조건을 가드 절 또는 헬퍼 함수로 추출 |
| 긴 함수 (50+ 줄) | 여러 책임 | 설명적인 이름으로 집중된 함수로 분리 |
| 중첩된 삼항 연산자 | 파싱에 정신적 스택 필요 | if/else 체인, switch, 또는 룩업 객체로 대체 |
| Boolean 파라미터 플래그 | `doThing(true, false, true)` | 옵션 객체 또는 별도 함수로 대체 |
| 반복되는 조건문 | 여러 곳에서 동일한 `if` 검사 | 잘 명명된 술어 함수로 추출 |

**네이밍과 가독성:**

| 패턴 | 신호 | 단순화 |
|---------|--------|----------------|
| 일반적인 이름 | `data`, `result`, `temp`, `val`, `item` | 내용을 설명하도록 이름 변경: `userProfile`, `validationErrors` |
| 축약된 이름 | `usr`, `cfg`, `btn`, `evt` | 축약이 보편적이지 않으면 전체 단어 사용 (`id`, `url`, `api`는 괜찮음) |
| 오해하게 하는 이름 | 상태를 변이시키는 `get`으로 명명된 함수 | 실제 동작을 반영하도록 이름 변경 |
| "무엇"을 설명하는 주석 | `count++` 위의 `// increment counter` | 주석 삭제 — 코드로 충분히 명확함 |
| "왜"를 설명하는 주석 | `// 부하 시 API가 불안정하기 때문에 재시도` | 이것은 유지 — 코드가 표현할 수 없는 의도를 전달함 |

**중복:**

| 패턴 | 신호 | 단순화 |
|---------|--------|----------------|
| 중복된 로직 | 여러 곳에서 동일한 5+ 줄 | 공유 함수로 추출 |
| 죽은 코드 | 도달할 수 없는 분기, 사용되지 않는 변수, 주석 처리된 블록 | 삭제 (진짜 죽은 것임을 확인한 후) |
| 불필요한 추상화 | 가치를 추가하지 않는 래퍼 | 래퍼를 인라인하고, 기저 함수를 직접 호출 |
| 과도하게 엔지니어링된 패턴 | 팩토리의 팩토리, 하나의 전략만 있는 strategy 패턴 | 단순한 직접적 접근으로 대체 |
| 중복된 타입 어서션 | 이미 추론된 타입으로 캐스팅 | 어서션 제거 |

### 3단계: 변경을 점진적으로 적용

한 번에 하나의 단순화를 하세요. 각 변경 후 테스트를 실행하세요. **리팩토링 변경을 기능 또는 버그 수정 변경과 별도로 제출하세요.** 리팩토링하고 기능을 추가하는 PR은 두 개의 PR입니다 — 분리하세요.

```
각 단순화에 대해:
1. 변경 적용
2. 테스트 스위트 실행
3. 테스트 통과 → 커밋 (또는 다음 단순화로 계속)
4. 테스트 실패 → 되돌리고 재고
```

여러 단순화를 테스트되지 않은 단일 변경으로 묶지 마세요. 무언가가 깨지면 어떤 단순화가 원인인지 알아야 합니다.

**500 규칙:** 리팩토링이 500줄 이상을 건드릴 것이라면, 손으로 변경하는 대신 자동화에 투자하세요 (codemods, sed 스크립트, AST 변환). 그 규모에서의 수동 편집은 오류가 발생하기 쉽고 리뷰하기 지칩니다.

### 4단계: 결과 검증

모든 단순화 후, 물러서서 전체를 평가하세요:

```
이전과 이후 비교:
- 단순화된 버전이 진정으로 이해하기 쉬운가?
- 코드베이스와 일관성 없는 새로운 패턴을 도입했는가?
- diff가 깨끗하고 리뷰 가능한가?
- 팀원이 이 변경을 승인할 것인가?
```

"단순화된" 버전이 이해하거나 리뷰하기 더 어렵다면, 되돌리세요. 모든 단순화 시도가 성공하는 것은 아닙니다.

## 언어별 지침

### TypeScript / JavaScript

```typescript
// 단순화: 불필요한 async 래퍼
// 이전
async function getUser(id: string): Promise<User> {
  return await userService.findById(id);
}
// 이후
function getUser(id: string): Promise<User> {
  return userService.findById(id);
}

// 단순화: 장황한 조건부 할당
// 이전
let displayName: string;
if (user.nickname) {
  displayName = user.nickname;
} else {
  displayName = user.fullName;
}
// 이후
const displayName = user.nickname || user.fullName;

// 단순화: 수동 배열 구축
// 이전
const activeUsers: User[] = [];
for (const user of users) {
  if (user.isActive) {
    activeUsers.push(user);
  }
}
// 이후
const activeUsers = users.filter((user) => user.isActive);

// 단순화: 중복된 boolean 반환
// 이전
function isValid(input: string): boolean {
  if (input.length > 0 && input.length < 100) {
    return true;
  }
  return false;
}
// 이후
function isValid(input: string): boolean {
  return input.length > 0 && input.length < 100;
}
```

### Python

```python
# 단순화: 장황한 딕셔너리 구축
# 이전
result = {}
for item in items:
    result[item.id] = item.name
# 이후
result = {item.id: item.name for item in items}

# 단순화: 조기 반환으로 중첩된 조건문
# 이전
def process(data):
    if data is not None:
        if data.is_valid():
            if data.has_permission():
                return do_work(data)
            else:
                raise PermissionError("No permission")
        else:
            raise ValueError("Invalid data")
    else:
        raise TypeError("Data is None")
# 이후
def process(data):
    if data is None:
        raise TypeError("Data is None")
    if not data.is_valid():
        raise ValueError("Invalid data")
    if not data.has_permission():
        raise PermissionError("No permission")
    return do_work(data)
```

### React / JSX

```tsx
// 단순화: 장황한 조건부 렌더링
// 이전
function UserBadge({ user }: Props) {
  if (user.isAdmin) {
    return <Badge variant="admin">Admin</Badge>;
  } else {
    return <Badge variant="default">User</Badge>;
  }
}
// 이후
function UserBadge({ user }: Props) {
  const variant = user.isAdmin ? 'admin' : 'default';
  const label = user.isAdmin ? 'Admin' : 'User';
  return <Badge variant={variant}>{label}</Badge>;
}

// 단순화: 중간 컴포넌트를 통한 prop drilling
// 이전 — context 또는 composition이 이것을 더 잘 해결하는지 고려하세요.
// 이것은 판단 문제입니다 — 플래그를 달되, 자동으로 리팩토하지 마세요.
```

## 흔한 합리화

| 합리화 | 현실 |
|---|---|
| "동작하고 있으니 건드릴 필요 없습니다" | 읽기 어려운 동작하는 코드는 깨질 때 고치기도 어렵습니다. 지금 단순화하면 미래의 모든 변경에 시간을 절약합니다. |
| "적은 줄이 항상 더 단순합니다" | 1줄의 중첩된 삼항 연산자는 5줄의 if/else보다 단순하지 않습니다. 단순성은 이해 속도에 관한 것이지 줄 수가 아닙니다. |
| "이 관련 없는 코드도 빠르게 단순화하겠습니다" | 범위 없는 단순화는 노이즈가 있는 diff를 만들고 변경하려 하지 않은 코드에서 회귀 위험이 있습니다. 집중하세요. |
| "타입이 자기 문서화됩니다" | 타입은 구조를 문서화하지, 의도는 아닙니다. 잘 명명된 함수는 타입 시그니처가 *무엇*을 설명하는 것보다 *왜*를 더 잘 설명합니다. |
| "이 추상화는 나중에 유용할 수 있습니다" | 추측성 추상화를 보존하지 마세요. 지금 사용되지 않는다면, 그것은 가치 없는 복잡성입니다. 제거하고 필요할 때 다시 추가하세요. |
| "원래 작성자에게 이유가 있었을 것입니다" | 아마도. git blame을 확인하세요 — Chesterton's Fence를 적용하세요. 하지만 축적된 복잡성은 종종 이유가 없습니다; 그것은 단지 압박 하에 반복의 잔재물입니다. |
| "이 기능을 추가하면서 리팩토링하겠습니다" | 리팩토링과 기능 작업을 분리하세요. 혼합된 변경은 리뷰하고, 되돌리고, 히스토리에서 이해하기 더 어렵습니다. |

## 위험 신호

- 통과하기 위해 테스트를 수정해야 하는 단순화 (동작을 변경했을 가능성이 높음)
- 원본보다 길고 따라가기 어려운 "단순화된" 코드
- 프로젝트 컨벤션보다 개인 선호도에 맞게 이름 변경
- "코드를 더 깨끗하게 만든다"는 이유로 에러 처리 제거
- 완전히 이해하지 못한 코드 단순화
- 여러 단순화를 하나의 크고 리뷰하기 어려운 커밋으로 묶기
- 요청받지 않고 현재 작업 범위를 벗어난 코드 리팩토링

## 검증

단순화 패스를 완료한 후:

- [ ] 수정 없이 모든 기존 테스트 통과
- [ ] 새로운 경고 없이 빌드 성공
- [ ] Linter/formatter 통과 (스타일 회귀 없음)
- [ ] 각 단순화가 리뷰 가능하고 점진적인 변경임
- [ ] diff가 깨끗함 — 관련 없는 변경이 섞이지 않음
- [ ] 단순화된 코드가 프로젝트 컨벤션을 따름 (CLAUDE.md 또는 동등한 것에 대해 확인됨)
- [ ] 에러 처리가 제거되거나 약화되지 않음
- [ ] 죽은 코드가 남겨지지 않음 (사용되지 않는 imports, 도달할 수 없는 분기)
- [ ] 팀원 또는 리뷰 에이전트가 변경을 순수 개선으로 승인할 것임
