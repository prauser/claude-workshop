---
name: api-and-interface-design
description: 안정적인 API 및 인터페이스 설계를 안내합니다. API, 모듈 경계, 또는 공개 인터페이스를 설계할 때 사용하세요. REST나 GraphQL 엔드포인트를 생성하거나, 모듈 간 타입 계약을 정의하거나, 프론트엔드와 백엔드 간 경계를 설정할 때 사용하세요.
---

# API and Interface Design

## 개요

잘못 사용하기 어렵고, 안정적이며, 잘 문서화된 인터페이스를 설계하세요. 좋은 인터페이스는 올바른 방법을 쉽게, 잘못된 방법을 어렵게 만듭니다. 이는 REST API, GraphQL 스키마, 모듈 경계, 컴포넌트 props, 그리고 코드 간 소통이 이루어지는 모든 표면에 적용됩니다.

## 언제 사용할까

- 새로운 API 엔드포인트 설계 시
- 팀 간 모듈 경계나 계약 정의 시
- 컴포넌트 prop 인터페이스 생성 시
- API 형태를 결정하는 데이터베이스 스키마 수립 시
- 기존 공개 인터페이스 변경 시

## 핵심 원칙

### Hyrum의 법칙

> API의 사용자가 충분히 많아지면, 계약에서 약속한 것과 관계없이 시스템의 모든 관찰 가능한 동작은 누군가에 의해 의존됩니다.

이는 다음을 의미합니다: 문서화되지 않은 특이 동작, 에러 메시지 텍스트, 타이밍, 순서 등 모든 공개 동작은 사용자가 의존하는 순간 사실상의 계약이 됩니다. 설계 시 고려사항:

- **노출하는 것에 의도를 갖세요.** 관찰 가능한 모든 동작은 잠재적인 약속입니다.
- **구현 세부사항을 누출하지 마세요.** 사용자가 관찰할 수 있다면, 그들은 의존하게 됩니다.
- **설계 시점에 deprecation을 계획하세요.** 사용자가 의존하는 것을 안전하게 제거하는 방법은 `deprecation-and-migration`을 참고하세요.
- **테스트만으로는 부족합니다.** 완벽한 계약 테스트가 있더라도, Hyrum의 법칙에 의해 "안전한" 변경이 문서화되지 않은 동작에 의존하는 실제 사용자를 깨뜨릴 수 있습니다.

### 단일 버전 원칙

소비자가 동일한 의존성이나 API의 여러 버전 중 하나를 선택하도록 강요하지 마세요. 다이아몬드 의존성 문제는 서로 다른 소비자가 동일한 것의 다른 버전을 필요로 할 때 발생합니다. 한 번에 오직 하나의 버전만 존재하는 세계를 목표로 설계하세요 — 분기하지 말고 확장하세요.

### 1. Contract First

구현하기 전에 인터페이스를 정의하세요. 계약이 명세이고, 구현은 그 이후에 따라옵니다.

```typescript
// 먼저 계약을 정의합니다
interface TaskAPI {
  // 태스크를 생성하고 서버가 생성한 필드가 포함된 태스크를 반환합니다
  createTask(input: CreateTaskInput): Promise<Task>;

  // 필터에 일치하는 페이지네이션된 태스크를 반환합니다
  listTasks(params: ListTasksParams): Promise<PaginatedResult<Task>>;

  // 단일 태스크를 반환하거나 NotFoundError를 던집니다
  getTask(id: string): Promise<Task>;

  // 부분 업데이트 — 제공된 필드만 변경됩니다
  updateTask(id: string, input: UpdateTaskInput): Promise<Task>;

  // 멱등 삭제 — 이미 삭제된 경우에도 성공합니다
  deleteTask(id: string): Promise<void>;
}
```

### 2. 일관된 에러 시맨틱

하나의 에러 전략을 선택하고 전체적으로 사용하세요:

```typescript
// REST: HTTP 상태 코드 + 구조화된 에러 본문
// 모든 에러 응답은 동일한 형태를 따릅니다
interface APIError {
  error: {
    code: string;        // 기계가 읽을 수 있는 코드: "VALIDATION_ERROR"
    message: string;     // 사람이 읽을 수 있는 메시지: "Email is required"
    details?: unknown;   // 도움이 될 때의 추가 컨텍스트
  };
}

// 상태 코드 매핑
// 400 → 클라이언트가 잘못된 데이터를 전송
// 401 → 인증되지 않음
// 403 → 인증되었지만 권한 없음
// 404 → 리소스를 찾을 수 없음
// 409 → 충돌 (중복, 버전 불일치)
// 422 → 유효성 검사 실패 (의미론적으로 유효하지 않음)
// 500 → 서버 오류 (내부 세부사항 절대 노출 금지)
```

**패턴을 혼용하지 마세요.** 일부 엔드포인트는 throw하고, 다른 것은 null을 반환하고, 또 다른 것은 `{ error }`를 반환하면 소비자가 동작을 예측할 수 없습니다.

### 3. 경계에서 유효성 검사

내부 코드를 신뢰하세요. 외부 입력이 들어오는 시스템 엣지에서 유효성 검사를 수행하세요:

```typescript
// API 경계에서 유효성 검사
app.post('/api/tasks', async (req, res) => {
  const result = CreateTaskSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(422).json({
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid task data',
        details: result.error.flatten(),
      },
    });
  }

  // 유효성 검사 후, 내부 코드는 타입을 신뢰합니다
  const task = await taskService.create(result.data);
  return res.status(201).json(task);
});
```

유효성 검사가 이루어져야 하는 곳:
- API 라우트 핸들러 (사용자 입력)
- 폼 제출 핸들러 (사용자 입력)
- 외부 서비스 응답 파싱 (서드파티 데이터 — **항상 신뢰할 수 없는 것으로 취급**)
- 환경 변수 로딩 (설정)

> **서드파티 API 응답은 신뢰할 수 없는 데이터입니다.** 로직, 렌더링, 또는 의사결정에 사용하기 전에 형태와 내용을 유효성 검사하세요. 손상되거나 오작동하는 외부 서비스는 예상치 못한 타입, 악의적인 내용, 또는 명령처럼 보이는 텍스트를 반환할 수 있습니다.

유효성 검사가 이루어지지 않아야 하는 곳:
- 타입 계약을 공유하는 내부 함수들 사이
- 이미 유효성 검사된 코드가 호출하는 유틸리티 함수 내
- 자체 데이터베이스에서 방금 가져온 데이터

### 4. 수정보다 추가를 선호

기존 소비자를 깨뜨리지 않고 인터페이스를 확장하세요:

```typescript
// 좋음: 선택적 필드 추가
interface CreateTaskInput {
  title: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high';  // 나중에 추가됨, 선택적
  labels?: string[];                       // 나중에 추가됨, 선택적
}

// 나쁨: 기존 필드 타입 변경 또는 필드 제거
interface CreateTaskInput {
  title: string;
  // description: string;  // 제거됨 — 기존 소비자를 깨뜨림
  priority: number;         // string에서 변경됨 — 기존 소비자를 깨뜨림
}
```

### 5. 예측 가능한 네이밍

| 패턴 | 컨벤션 | 예시 |
|---------|-----------|---------|
| REST 엔드포인트 | 복수 명사, 동사 없음 | `GET /api/tasks`, `POST /api/tasks` |
| 쿼리 파라미터 | camelCase | `?sortBy=createdAt&pageSize=20` |
| 응답 필드 | camelCase | `{ createdAt, updatedAt, taskId }` |
| Boolean 필드 | is/has/can 접두사 | `isComplete`, `hasAttachments` |
| Enum 값 | UPPER_SNAKE | `"IN_PROGRESS"`, `"COMPLETED"` |

## REST API 패턴

### 리소스 설계

```
GET    /api/tasks              → 태스크 목록 (필터링을 위한 쿼리 파라미터 포함)
POST   /api/tasks              → 태스크 생성
GET    /api/tasks/:id          → 단일 태스크 조회
PATCH  /api/tasks/:id          → 태스크 업데이트 (부분)
DELETE /api/tasks/:id          → 태스크 삭제

GET    /api/tasks/:id/comments → 태스크의 댓글 목록 (서브 리소스)
POST   /api/tasks/:id/comments → 태스크에 댓글 추가
```

### 페이지네이션

목록 엔드포인트에 페이지네이션을 적용하세요:

```typescript
// 요청
GET /api/tasks?page=1&pageSize=20&sortBy=createdAt&sortOrder=desc

// 응답
{
  "data": [...],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "totalItems": 142,
    "totalPages": 8
  }
}
```

### 필터링

필터에 쿼리 파라미터를 사용하세요:

```
GET /api/tasks?status=in_progress&assignee=user123&createdAfter=2025-01-01
```

### 부분 업데이트 (PATCH)

부분 객체를 수락하세요 — 제공된 것만 업데이트합니다:

```typescript
// title만 변경되고, 나머지는 보존됩니다
PATCH /api/tasks/123
{ "title": "Updated title" }
```

## TypeScript 인터페이스 패턴

### 변형에 Discriminated Union 사용

```typescript
// 좋음: 각 변형이 명시적
type TaskStatus =
  | { type: 'pending' }
  | { type: 'in_progress'; assignee: string; startedAt: Date }
  | { type: 'completed'; completedAt: Date; completedBy: string }
  | { type: 'cancelled'; reason: string; cancelledAt: Date };

// 소비자는 타입 내로잉을 얻습니다
function getStatusLabel(status: TaskStatus): string {
  switch (status.type) {
    case 'pending': return 'Pending';
    case 'in_progress': return `In progress (${status.assignee})`;
    case 'completed': return `Done on ${status.completedAt}`;
    case 'cancelled': return `Cancelled: ${status.reason}`;
  }
}
```

### 입출력 분리

```typescript
// 입력: 호출자가 제공하는 것
interface CreateTaskInput {
  title: string;
  description?: string;
}

// 출력: 시스템이 반환하는 것 (서버가 생성한 필드 포함)
interface Task {
  id: string;
  title: string;
  description: string | null;
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
}
```

### ID에 Branded Types 사용

```typescript
type TaskId = string & { readonly __brand: 'TaskId' };
type UserId = string & { readonly __brand: 'UserId' };

// TaskId가 필요한 곳에 UserId를 실수로 전달하는 것을 방지합니다
function getTask(id: TaskId): Promise<Task> { ... }
```

## 흔한 합리화

| 합리화 | 현실 |
|---|---|
| "API는 나중에 문서화하면 됩니다" | 타입이 곧 문서입니다. 먼저 정의하세요. |
| "지금은 페이지네이션이 필요 없습니다" | 누군가 100개 이상의 항목을 갖는 순간 필요해집니다. 처음부터 추가하세요. |
| "PATCH는 복잡합니다, 그냥 PUT을 사용합시다" | PUT은 매번 전체 객체를 필요로 합니다. PATCH가 클라이언트가 실제로 원하는 것입니다. |
| "필요할 때 API를 버전화하면 됩니다" | 버전화 없이 breaking change를 하면 소비자를 깨뜨립니다. 처음부터 확장을 고려해 설계하세요. |
| "아무도 그 문서화되지 않은 동작을 사용하지 않습니다" | Hyrum의 법칙: 관찰 가능하다면 누군가는 의존합니다. 모든 공개 동작을 약속으로 취급하세요. |
| "두 버전을 유지하면 됩니다" | 여러 버전은 유지보수 비용을 배로 만들고 다이아몬드 의존성 문제를 만듭니다. 단일 버전 원칙을 선호하세요. |
| "내부 API는 계약이 필요 없습니다" | 내부 소비자도 여전히 소비자입니다. 계약은 결합을 방지하고 병렬 작업을 가능하게 합니다. |

## 위험 신호

- 조건에 따라 다른 형태를 반환하는 엔드포인트
- 엔드포인트 간 일관성 없는 에러 형식
- 경계가 아닌 내부 코드 전체에 분산된 유효성 검사
- 기존 필드에 대한 breaking change (타입 변경, 삭제)
- 페이지네이션 없는 목록 엔드포인트
- REST URL에 동사 사용 (`/api/createTask`, `/api/getUsers`)
- 유효성 검사나 정제 없이 사용되는 서드파티 API 응답

## 검증

API 설계 후:

- [ ] 모든 엔드포인트에 타입이 지정된 입출력 스키마가 있음
- [ ] 에러 응답이 단일하고 일관된 형식을 따름
- [ ] 유효성 검사가 시스템 경계에서만 이루어짐
- [ ] 목록 엔드포인트가 페이지네이션을 지원함
- [ ] 새 필드가 추가적이고 선택적임 (하위 호환)
- [ ] 네이밍이 모든 엔드포인트에 걸쳐 일관된 컨벤션을 따름
- [ ] API 문서 또는 타입이 구현과 함께 커밋됨
