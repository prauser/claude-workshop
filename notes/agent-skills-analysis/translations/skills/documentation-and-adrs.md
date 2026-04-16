---
name: documentation-and-adrs
description: Records decisions and documentation. Use when making architectural decisions, changing public APIs, shipping features, or when you need to record context that future engineers and agents will need to understand the codebase.
---

# Documentation and ADRs

## Overview

코드뿐만 아니라 결정을 문서화하라. 가장 가치 있는 문서는 *이유* — 결정을 이끈 맥락, 제약 조건, 트레이드오프를 담는다. 코드는 *무엇*이 만들어졌는지를 보여주고, 문서화는 *왜 이런 방식으로 만들어졌는지*와 *어떤 대안이 검토되었는지*를 설명한다. 이 맥락은 코드베이스에서 작업하는 미래의 인간과 에이전트에게 필수적이다.

## When to Use

- 중요한 아키텍처 결정을 내릴 때
- 경쟁하는 접근 방식 중 선택할 때
- public API를 추가하거나 변경할 때
- 사용자 대면 동작을 변경하는 기능을 출시할 때
- 새 팀원(또는 에이전트)을 프로젝트에 온보딩할 때
- 같은 내용을 반복해서 설명하는 자신을 발견할 때

**사용하지 않을 때:** 명백한 코드는 문서화하지 않는다. 코드가 이미 말하는 내용을 재진술하는 주석을 추가하지 않는다. 일회용 프로토타입에 대한 문서를 작성하지 않는다.

## Architecture Decision Records (ADRs)

ADR은 중요한 기술적 결정 이면의 추론을 담는다. 작성할 수 있는 가장 가치 높은 문서다.

### ADR을 작성할 시점

- 프레임워크, 라이브러리, 또는 주요 의존성 선택
- 데이터 모델 또는 데이터베이스 스키마 설계
- 인증 전략 선택
- API 아키텍처 결정 (REST vs. GraphQL vs. tRPC)
- 빌드 도구, 호스팅 플랫폼, 또는 인프라 선택
- 번복하기 비용이 큰 모든 결정

### ADR Template

ADR은 순서 번호를 붙여 `docs/decisions/`에 저장한다:

```markdown
# ADR-001: 기본 데이터베이스로 PostgreSQL 사용

## Status
Accepted | Superseded by ADR-XXX | Deprecated

## Date
2025-01-15

## Context
태스크 관리 애플리케이션을 위한 기본 데이터베이스가 필요하다. 주요 요구 사항:
- 관계형 데이터 모델 (관계가 있는 사용자, 태스크, 팀)
- 태스크 상태 변경을 위한 ACID 트랜잭션
- 태스크 내용에 대한 전체 텍스트 검색 지원
- 관리형 호스팅 가능 (소규모 팀, 제한된 운영 역량)

## Decision
Prisma ORM과 함께 PostgreSQL을 사용한다.

## Alternatives Considered

### MongoDB
- 장점: 유연한 스키마, 시작하기 쉬움
- 단점: 데이터가 본질적으로 관계형; 관계를 수동으로 관리해야 함
- 거부됨: 문서 저장소에서의 관계형 데이터는 복잡한 조인이나 데이터 중복으로 이어짐

### SQLite
- 장점: 설정 불필요, 내장형, 읽기 속도 빠름
- 단점: 동시 쓰기 지원 제한, 프로덕션용 관리형 호스팅 없음
- 거부됨: 프로덕션 멀티 사용자 웹 애플리케이션에 적합하지 않음

### MySQL
- 장점: 성숙하고, 널리 지원됨
- 단점: PostgreSQL이 더 나은 JSON 지원, 전체 텍스트 검색, 에코시스템 도구를 제공함
- 거부됨: PostgreSQL이 기능 요구 사항에 더 적합함

## Consequences
- Prisma는 타입 안전한 데이터베이스 접근과 마이그레이션 관리를 제공함
- Elasticsearch를 추가하는 대신 PostgreSQL의 전체 텍스트 검색을 사용할 수 있음
- 팀은 PostgreSQL 지식이 필요함 (표준 기술, 낮은 위험)
- 관리형 서비스 호스팅 (Supabase, Neon, 또는 RDS)
```

### ADR Lifecycle

```
PROPOSED → ACCEPTED → (SUPERSEDED 또는 DEPRECATED)
```

- **오래된 ADR을 삭제하지 않는다.** 역사적 맥락을 담고 있다.
- 결정이 바뀔 때, 이전 것을 참조하고 대체하는 새 ADR을 작성한다.

## Inline Documentation

### 주석을 달 때

*무엇*이 아닌 *이유*에 주석을 달라:

```typescript
// 나쁜 예: 코드를 재진술함
// 카운터를 1 증가
counter += 1;

// 좋은 예: 명확하지 않은 의도를 설명함
// Rate limit은 슬라이딩 윈도우를 사용 — 고정 스케줄이 아닌 윈도우 경계에서
// 카운터를 리셋하여, 윈도우 경계에서의 버스트 공격을 방지함
if (now - windowStart > WINDOW_SIZE_MS) {
  counter = 0;
  windowStart = now;
}
```

### 주석을 달지 않을 때

```typescript
// 자명한 코드에는 주석을 달지 않는다
function calculateTotal(items: CartItem[]): number {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

// 지금 당장 해야 할 일에 대한 TODO 주석을 남기지 않는다
// TODO: 에러 처리 추가  ← 그냥 추가하라

// 주석 처리된 코드를 남기지 않는다
// const oldImplementation = () => { ... }  ← 삭제하라, git에 기록이 있다
```

### 알려진 함정 문서화

```typescript
/**
 * 중요: 이 함수는 첫 번째 렌더 전에 호출되어야 합니다.
 * 하이드레이션 후 호출되면, SSR 중에 테마 컨텍스트를 사용할 수 없어
 * 스타일이 없는 콘텐츠의 플래시가 발생합니다.
 *
 * 전체 설계 근거는 ADR-003을 참조하세요.
 */
export function initializeTheme(theme: Theme): void {
  // ...
}
```

## API Documentation

public API(REST, GraphQL, 라이브러리 인터페이스)의 경우:

### 타입 인라인 방식 (TypeScript에 권장)

```typescript
/**
 * 새 태스크를 생성합니다.
 *
 * @param input - 태스크 생성 데이터 (제목 필수, 설명 선택)
 * @returns 서버에서 생성된 ID와 타임스탬프가 포함된 생성된 태스크
 * @throws {ValidationError} 제목이 비어 있거나 200자를 초과하는 경우
 * @throws {AuthenticationError} 사용자가 인증되지 않은 경우
 *
 * @example
 * const task = await createTask({ title: '장 보기' });
 * console.log(task.id); // "task_abc123"
 */
export async function createTask(input: CreateTaskInput): Promise<Task> {
  // ...
}
```

### REST API를 위한 OpenAPI / Swagger

```yaml
paths:
  /api/tasks:
    post:
      summary: 태스크 생성
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateTaskInput'
      responses:
        '201':
          description: 태스크 생성됨
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '422':
          description: 유효성 검사 오류
```

## README Structure

모든 프로젝트는 다음을 포함하는 README가 있어야 한다:

```markdown
# 프로젝트 이름

이 프로젝트가 무엇을 하는지에 대한 한 단락 설명.

## Quick Start
1. 저장소 클론
2. 의존성 설치: `npm install`
3. 환경 설정: `cp .env.example .env`
4. 개발 서버 실행: `npm run dev`

## Commands
| 명령어 | 설명 |
|--------|------|
| `npm run dev` | 개발 서버 시작 |
| `npm test` | 테스트 실행 |
| `npm run build` | 프로덕션 빌드 |
| `npm run lint` | 린터 실행 |

## Architecture
프로젝트 구조와 주요 설계 결정에 대한 간략한 개요.
자세한 내용은 ADR 링크 참조.

## Contributing
기여 방법, 코딩 표준, PR 프로세스.
```

## Changelog Maintenance

출시된 기능의 경우:

```markdown
# Changelog

## [1.2.0] - 2025-01-20
### Added
- 태스크 공유: 사용자가 팀원과 태스크를 공유할 수 있음 (#123)
- 태스크 배정에 대한 이메일 알림 (#124)

### Fixed
- 빠르게 생성 버튼을 클릭할 때 중복 태스크가 나타나는 문제 (#125)

### Changed
- 태스크 목록이 이제 더 나은 UX를 위해 페이지당 50개 항목을 로드함 (기존 20개) (#126)
```

## Documentation for Agents

AI 에이전트 컨텍스트에 대한 특별 고려 사항:

- **CLAUDE.md / rules 파일** — 에이전트가 따를 수 있도록 프로젝트 규칙을 문서화한다
- **Spec 파일** — 에이전트가 올바른 것을 만들 수 있도록 spec을 최신 상태로 유지한다
- **ADR** — 에이전트가 과거 결정이 왜 내려졌는지 이해하는 데 도움을 준다 (재결정 방지)
- **Inline 함정** — 에이전트가 알려진 함정에 빠지는 것을 방지한다

## Common Rationalizations

| 합리화 | 현실 |
|--------|------|
| "코드는 자기 설명적이다" | 코드는 무엇을 보여준다. 왜, 어떤 대안이 거부되었는지, 어떤 제약이 적용되는지는 보여주지 않는다. |
| "API가 안정화되면 문서를 작성할 것이다" | API는 문서화할 때 더 빨리 안정화된다. 문서는 설계의 첫 번째 테스트다. |
| "아무도 문서를 읽지 않는다" | 에이전트는 읽는다. 미래의 엔지니어들도 읽는다. 3개월 후의 당신도 읽는다. |
| "ADR은 오버헤드다" | 10분짜리 ADR은 6개월 후 같은 결정에 대한 2시간짜리 토론을 방지한다. |
| "주석은 오래된 정보가 된다" | *이유*에 대한 주석은 안정적이다. *무엇*에 대한 주석이 오래된 정보가 된다 — 그래서 전자만 작성한다. |

## Red Flags

- 작성된 근거 없이 내려진 아키텍처 결정
- 문서화나 타입 없는 public API
- 프로젝트를 실행하는 방법을 설명하지 않는 README
- 삭제 대신 주석 처리된 코드
- 몇 주 동안 그대로인 TODO 주석
- 중요한 아키텍처 선택이 있는 프로젝트에 ADR 없음
- 의도를 설명하는 대신 코드를 재진술하는 문서화

## Verification

문서화 후:

- [ ] 모든 중요한 아키텍처 결정에 ADR이 존재한다
- [ ] README가 빠른 시작, 명령어, 아키텍처 개요를 포함한다
- [ ] API 함수에 파라미터와 반환 타입 문서화가 있다
- [ ] 알려진 함정이 관련 위치에 인라인으로 문서화되어 있다
- [ ] 주석 처리된 코드가 남아 있지 않다
- [ ] Rules 파일 (CLAUDE.md 등)이 현재 상태이고 정확하다
