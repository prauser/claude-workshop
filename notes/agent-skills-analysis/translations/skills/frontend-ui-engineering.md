---
name: frontend-ui-engineering
description: Builds production-quality UIs. Use when building or modifying user-facing interfaces. Use when creating components, implementing layouts, managing state, or when the output needs to look and feel production-quality rather than AI-generated.
---

# Frontend UI Engineering

## Overview

접근 가능하고, 성능이 뛰어나며, 시각적으로 세련된 프로덕션 품질의 사용자 인터페이스를 구축하라. 목표는 상위 기업의 디자인 감각이 있는 엔지니어가 만든 것처럼 보이는 UI다 — AI가 생성한 것처럼 보이는 UI가 아니다. 이는 실제 디자인 시스템 준수, 올바른 접근성, 사려 깊은 인터랙션 패턴, 그리고 일반적인 "AI 미학" 없음을 의미한다.

## When to Use

- 새 UI 컴포넌트 또는 페이지 구축
- 기존 사용자 대면 인터페이스 수정
- 반응형 레이아웃 구현
- 인터랙티비티 또는 상태 관리 추가
- 시각적 또는 UX 문제 수정

## Component Architecture

### File Structure

컴포넌트와 관련된 모든 것을 함께 배치한다:

```
src/components/
  TaskList/
    TaskList.tsx          # 컴포넌트 구현
    TaskList.test.tsx     # 테스트
    TaskList.stories.tsx  # Storybook stories (사용하는 경우)
    use-task-list.ts      # Custom hook (복잡한 상태의 경우)
    types.ts              # 컴포넌트별 타입 (필요한 경우)
```

### Component Patterns

**설정보다 합성을 선호한다:**

```tsx
// 좋음: 합성 가능
<Card>
  <CardHeader>
    <CardTitle>태스크</CardTitle>
  </CardHeader>
  <CardBody>
    <TaskList tasks={tasks} />
  </CardBody>
</Card>

// 피할 것: 과도하게 설정됨
<Card
  title="태스크"
  headerVariant="large"
  bodyPadding="md"
  content={<TaskList tasks={tasks} />}
/>
```

**컴포넌트를 집중적으로 유지한다:**

```tsx
// 좋음: 한 가지 일을 한다
export function TaskItem({ task, onToggle, onDelete }: TaskItemProps) {
  return (
    <li className="flex items-center gap-3 p-3">
      <Checkbox checked={task.done} onChange={() => onToggle(task.id)} />
      <span className={task.done ? 'line-through text-muted' : ''}>{task.title}</span>
      <Button variant="ghost" size="sm" onClick={() => onDelete(task.id)}>
        <TrashIcon />
      </Button>
    </li>
  );
}
```

**데이터 가져오기를 표현에서 분리한다:**

```tsx
// Container: 데이터 처리
export function TaskListContainer() {
  const { tasks, isLoading, error } = useTasks();

  if (isLoading) return <TaskListSkeleton />;
  if (error) return <ErrorState message="태스크를 불러오지 못했습니다" retry={refetch} />;
  if (tasks.length === 0) return <EmptyState message="아직 태스크가 없습니다" />;

  return <TaskList tasks={tasks} />;
}

// Presentation: 렌더링 처리
export function TaskList({ tasks }: { tasks: Task[] }) {
  return (
    <ul role="list" className="divide-y">
      {tasks.map(task => <TaskItem key={task.id} task={task} />)}
    </ul>
  );
}
```

## State Management

**작동하는 가장 단순한 접근 방식을 선택한다:**

```
Local state (useState)           → 컴포넌트별 UI 상태
Lifted state                     → 2-3개의 형제 컴포넌트 간 공유
Context                          → 테마, 인증, 로케일 (읽기 多, 쓰기 少)
URL state (searchParams)         → 필터, 페이지네이션, 공유 가능한 UI 상태
Server state (React Query, SWR)  → 캐싱이 있는 원격 데이터
Global store (Zustand, Redux)    → 앱 전체에서 공유되는 복잡한 클라이언트 상태
```

**3단계 이상의 prop drilling을 피한다.** 사용하지 않는 컴포넌트를 통해 props를 전달하고 있다면, context를 도입하거나 컴포넌트 트리를 재구성한다.

## Design System Adherence

### AI 미학 피하기

AI가 생성한 UI에는 알아볼 수 있는 패턴이 있다. 모두 피한다:

| AI 기본값 | 문제인 이유 | 프로덕션 품질 |
|-----------|------------|--------------|
| 보라색/인디고 일색 | 모델이 시각적으로 "안전한" 팔레트로 기본 설정되어 모든 앱이 동일하게 보임 | 프로젝트의 실제 색상 팔레트 사용 |
| 과도한 그라디언트 | 그라디언트는 시각적 노이즈를 추가하고 대부분의 디자인 시스템과 충돌 | 디자인 시스템에 맞는 플랫 또는 은은한 그라디언트 |
| 모든 것에 과도한 둥근 모서리 (rounded-2xl) | 최대 둥근 모서리는 "친근함"을 신호하지만 실제 디자인의 모서리 반경 계층을 무시 | 디자인 시스템의 일관된 border-radius |
| 일반적인 히어로 섹션 | 실제 콘텐츠나 사용자 요구와 연결 없는 템플릿 기반 레이아웃 | 콘텐츠 우선 레이아웃 |
| Lorem ipsum 스타일 텍스트 | 플레이스홀더 텍스트는 실제 콘텐츠가 드러내는 레이아웃 문제를 숨김 (길이, 줄바꿈, 오버플로우) | 실제적인 플레이스홀더 콘텐츠 |
| 모든 곳에 과도한 패딩 | 동일하게 넉넉한 패딩은 시각적 계층을 파괴하고 화면 공간을 낭비 | 일관된 간격 스케일 |
| 스톡 카드 그리드 | 균일한 그리드는 정보 우선순위와 스캔 패턴을 무시하는 레이아웃 단축키 | 목적에 맞는 레이아웃 |
| 그림자가 많은 디자인 | 겹쳐진 그림자는 콘텐츠와 경쟁하고 저사양 기기에서 렌더링을 느리게 만드는 깊이를 추가 | 디자인 시스템이 지정하지 않으면 은은하거나 없는 그림자 |

### Spacing and Layout

일관된 간격 스케일을 사용한다. 임의의 값을 만들어내지 않는다:

```css
/* 스케일 사용: 0.25rem 단위 (또는 프로젝트에서 사용하는 것) */
/* 좋음 */  padding: 1rem;      /* 16px */
/* 좋음 */  gap: 0.75rem;       /* 12px */
/* 나쁨 */  padding: 13px;      /* 어떤 스케일에도 없음 */
/* 나쁨 */  margin-top: 2.3rem; /* 어떤 스케일에도 없음 */
```

### Typography

타입 계층을 존중한다:

```
h1 → 페이지 제목 (페이지당 하나)
h2 → 섹션 제목
h3 → 하위 섹션 제목
body → 기본 텍스트
small → 보조/도움말 텍스트
```

heading 레벨을 건너뛰지 않는다. heading이 아닌 콘텐츠에 heading 스타일을 사용하지 않는다.

### Color

- 시맨틱 색상 토큰 사용: `text-primary`, `bg-surface`, `border-default` — 원시 hex 값 아님
- 충분한 대비 확보 (일반 텍스트 4.5:1, 큰 텍스트 3:1)
- 정보를 전달하는 데 색상에만 의존하지 않는다 (아이콘, 텍스트, 또는 패턴도 사용)

## Accessibility (WCAG 2.1 AA)

모든 컴포넌트는 다음 기준을 충족해야 한다:

### Keyboard Navigation

```tsx
// 모든 인터랙티브 요소는 키보드로 접근 가능해야 함
<button onClick={handleClick}>클릭</button>        // ✓ 기본적으로 포커스 가능
<div onClick={handleClick}>클릭</div>               // ✗ 포커스 불가
<div role="button" tabIndex={0} onClick={handleClick}    // ✓ 그러나 <button>을 선호
     onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && handleClick()}>
  클릭
</div>
```

### ARIA Labels

```tsx
// 가시적 텍스트가 없는 인터랙티브 요소에 레이블 추가
<button aria-label="대화 상자 닫기"><XIcon /></button>

// 폼 입력에 레이블 추가
<label htmlFor="email">이메일</label>
<input id="email" type="email" />

// 가시적 레이블이 없을 때 aria-label 사용
<input aria-label="태스크 검색" type="search" />
```

### Focus Management

```tsx
// 콘텐츠가 변경될 때 포커스 이동
function Dialog({ isOpen, onClose }: DialogProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (isOpen) closeRef.current?.focus();
  }, [isOpen]);

  // 열려 있을 때 대화 상자 내부에 포커스 트랩
  return (
    <dialog open={isOpen}>
      <button ref={closeRef} onClick={onClose}>닫기</button>
      {/* 대화 상자 내용 */}
    </dialog>
  );
}
```

### Meaningful Empty and Error States

```tsx
// 빈 화면을 표시하지 않는다
function TaskList({ tasks }: { tasks: Task[] }) {
  if (tasks.length === 0) {
    return (
      <div role="status" className="text-center py-12">
        <TasksEmptyIcon className="mx-auto h-12 w-12 text-muted" />
        <h3 className="mt-2 text-sm font-medium">태스크 없음</h3>
        <p className="mt-1 text-sm text-muted">새 태스크를 만들어 시작하세요.</p>
        <Button className="mt-4" onClick={onCreateTask}>태스크 만들기</Button>
      </div>
    );
  }

  return <ul role="list">...</ul>;
}
```

## Responsive Design

모바일 우선으로 설계한 후 확장한다:

```tsx
// Tailwind: 모바일 우선 반응형
<div className="
  grid grid-cols-1      /* 모바일: 단일 열 */
  sm:grid-cols-2        /* 소형: 2열 */
  lg:grid-cols-3        /* 대형: 3열 */
  gap-4
">
```

다음 브레이크포인트에서 테스트한다: 320px, 768px, 1024px, 1440px.

## Loading and Transitions

```tsx
// 스켈레톤 로딩 (콘텐츠에 스피너 사용 안 함)
function TaskListSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="태스크 로딩 중">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="h-12 bg-muted animate-pulse rounded" />
      ))}
    </div>
  );
}

// 체감 속도를 위한 낙관적 업데이트
function useToggleTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: toggleTask,
    onMutate: async (taskId) => {
      await queryClient.cancelQueries({ queryKey: ['tasks'] });
      const previous = queryClient.getQueryData(['tasks']);

      queryClient.setQueryData(['tasks'], (old: Task[]) =>
        old.map(t => t.id === taskId ? { ...t, done: !t.done } : t)
      );

      return { previous };
    },
    onError: (_err, _taskId, context) => {
      queryClient.setQueryData(['tasks'], context?.previous);
    },
  });
}
```

## See Also

자세한 접근성 요구 사항 및 테스트 도구는 `references/accessibility-checklist.md`를 참조하라.

## Common Rationalizations

| 합리화 | 현실 |
|--------|------|
| "접근성은 있으면 좋은 것이다" | 많은 국가에서 법적 요구 사항이며 엔지니어링 품질 기준이다. |
| "나중에 반응형으로 만들 것이다" | 반응형 디자인을 나중에 추가하는 것은 처음부터 구축하는 것보다 3배 더 어렵다. |
| "디자인이 확정되지 않아서 스타일링을 건너뛸 것이다" | 디자인 시스템 기본값을 사용하라. 스타일 없는 UI는 리뷰어에게 좋지 않은 첫인상을 만든다. |
| "이것은 그냥 프로토타입이다" | 프로토타입은 프로덕션 코드가 된다. 처음부터 기반을 올바르게 만든다. |
| "지금은 AI 미학으로 괜찮다" | 낮은 품질을 신호한다. 처음부터 프로젝트의 실제 디자인 시스템을 사용하라. |

## Red Flags

- 200줄 이상의 컴포넌트 (분리하라)
- 인라인 스타일 또는 임의의 픽셀 값
- 오류 상태, 로딩 상태, 또는 빈 상태 누락
- 키보드 내비게이션 테스트 없음
- 상태의 유일한 표시로 색상 사용 (텍스트나 아이콘 없는 빨간색/초록색)
- 일반적인 "AI 외관" (보라색 그라디언트, 과도하게 큰 카드, 스톡 레이아웃)

## Verification

UI 구축 후:

- [ ] 컴포넌트가 콘솔 오류 없이 렌더링된다
- [ ] 모든 인터랙티브 요소가 키보드로 접근 가능하다 (페이지를 탭으로 탐색)
- [ ] 화면 읽기 프로그램이 페이지의 콘텐츠와 구조를 전달할 수 있다
- [ ] 반응형: 320px, 768px, 1024px, 1440px에서 작동한다
- [ ] 로딩, 오류, 빈 상태가 모두 처리된다
- [ ] 프로젝트의 디자인 시스템을 따른다 (간격, 색상, 타이포그래피)
- [ ] 개발자 도구 또는 axe-core에서 접근성 경고 없음
