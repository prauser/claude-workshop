---
name: performance-optimization
description: Optimizes application performance. Use when performance requirements exist, when you suspect performance regressions, or when Core Web Vitals or load times need improvement. Use when profiling reveals bottlenecks that need fixing.
---

# Performance Optimization

## Overview

최적화하기 전에 측정하라. 측정 없는 성능 작업은 추측이다 — 그리고 추측은 중요한 것을 개선하지 않으면서 복잡성만 추가하는 성급한 최적화로 이어진다. 먼저 프로파일링하고, 실제 병목 지점을 파악하고, 수정하고, 다시 측정하라. 측정이 중요하다고 증명한 것만 최적화한다.

## When to Use

- 명세에 성능 요구 사항이 존재할 때 (로드 시간 예산, 응답 시간 SLA)
- 사용자 또는 모니터링이 느린 동작을 보고할 때
- Core Web Vitals 점수가 기준 미달일 때
- 변경 사항이 회귀를 도입했다고 의심될 때
- 대용량 데이터셋 또는 고트래픽을 처리하는 기능 구축 시

**사용하지 않을 때:** 문제의 증거 없이 최적화하지 않는다. 성급한 최적화는 얻는 성능보다 더 많은 비용이 드는 복잡성을 추가한다.

## Core Web Vitals Targets

| 메트릭 | 좋음 | 개선 필요 | 나쁨 |
|--------|------|-----------|------|
| **LCP** (Largest Contentful Paint) | ≤ 2.5s | ≤ 4.0s | > 4.0s |
| **INP** (Interaction to Next Paint) | ≤ 200ms | ≤ 500ms | > 500ms |
| **CLS** (Cumulative Layout Shift) | ≤ 0.1 | ≤ 0.25 | > 0.25 |

## The Optimization Workflow

```
1. 측정   → 실제 데이터로 기준선 설정
2. 파악   → 실제 병목 지점 찾기 (가정이 아닌)
3. 수정   → 특정 병목 지점 해결
4. 확인   → 다시 측정, 개선 확인
5. 감시   → 회귀 방지를 위한 모니터링 또는 테스트 추가
```

### Step 1: 측정

두 가지 보완적 접근 방식 — 둘 다 사용한다:

- **합성 방식 (Lighthouse, DevTools Performance 탭):** 통제된 조건, 재현 가능. CI 회귀 감지 및 특정 문제 격리에 최적.
- **RUM (web-vitals 라이브러리, CrUX):** 실제 조건에서의 실제 사용자 데이터. 수정이 실제로 사용자 경험을 개선했는지 검증하는 데 필수.

**프론트엔드:**
```bash
# 합성: Chrome DevTools의 Lighthouse (또는 CI)
# Chrome DevTools → Performance 탭 → 기록
# Chrome DevTools MCP → Performance trace

# RUM: 코드의 Web Vitals 라이브러리
import { onLCP, onINP, onCLS } from 'web-vitals';

onLCP(console.log);
onINP(console.log);
onCLS(console.log);
```

**백엔드:**
```bash
# 응답 시간 로깅
# Application Performance Monitoring (APM)
# 타이밍이 있는 데이터베이스 쿼리 로깅

# 단순 타이밍
console.time('db-query');
const result = await db.query(...);
console.timeEnd('db-query');
```

### 측정 시작 위치

증상을 사용하여 무엇을 먼저 측정할지 결정한다:

```
무엇이 느린가?
├── 첫 번째 페이지 로드
│   ├── 큰 번들? --> 번들 크기 측정, code splitting 확인
│   ├── 느린 서버 응답? --> DevTools Network waterfall에서 TTFB 측정
│   │   ├── DNS가 길다? --> 알려진 origin에 dns-prefetch / preconnect 추가
│   │   ├── TCP/TLS가 길다? --> HTTP/2 활성화, edge 배포 확인, keep-alive
│   │   └── Waiting (서버)이 길다? --> 백엔드 프로파일링, 쿼리와 캐싱 확인
│   └── 렌더링 차단 리소스? --> CSS/JS 차단을 위한 network waterfall 확인
├── 인터랙션이 느림
│   ├── 클릭 시 UI 정지? --> 메인 스레드 프로파일링, long task 찾기 (>50ms)
│   ├── 폼 입력 지연? --> 리렌더링 확인, controlled component 오버헤드
│   └── 애니메이션 끊김? --> layout thrashing, forced reflow 확인
├── 내비게이션 후 페이지
│   ├── 데이터 로딩? --> API 응답 시간 측정, waterfall 확인
│   └── 클라이언트 렌더링? --> 컴포넌트 렌더 시간 프로파일링, N+1 fetch 확인
└── 백엔드 / API
    ├── 단일 엔드포인트 느림? --> 데이터베이스 쿼리 프로파일링, 인덱스 확인
    ├── 모든 엔드포인트 느림? --> 연결 풀, 메모리, CPU 확인
    └── 간헐적 느림? --> lock contention, GC pause, 외부 의존성 확인
```

### Step 2: 병목 지점 파악

카테고리별 일반적인 병목 지점:

**프론트엔드:**

| 증상 | 가능한 원인 | 조사 방법 |
|------|------------|----------|
| 느린 LCP | 큰 이미지, 렌더링 차단 리소스, 느린 서버 | network waterfall, 이미지 크기 확인 |
| 높은 CLS | 크기 없는 이미지, 늦게 로드되는 콘텐츠, 폰트 변화 | layout shift 귀인 확인 |
| 낮은 INP | 메인 스레드의 무거운 JavaScript, 대규모 DOM 업데이트 | Performance trace에서 long task 확인 |
| 느린 초기 로드 | 큰 번들, 많은 네트워크 요청 | 번들 크기, code splitting 확인 |

**백엔드:**

| 증상 | 가능한 원인 | 조사 방법 |
|------|------------|----------|
| 느린 API 응답 | N+1 쿼리, 누락된 인덱스, 비최적화 쿼리 | 데이터베이스 쿼리 로그 확인 |
| 메모리 증가 | 누출된 참조, 무한 캐시, 큰 페이로드 | heap snapshot 분석 |
| CPU 스파이크 | 동기적 무거운 계산, regex backtracking | CPU 프로파일링 |
| 높은 레이턴시 | 캐싱 누락, 중복 계산, 네트워크 홉 | 스택을 통한 요청 추적 |

### Step 3: 일반적인 Anti-Pattern 수정

#### N+1 Queries (백엔드)

```typescript
// 나쁨: N+1 — 소유자를 위한 태스크당 하나의 쿼리
const tasks = await db.tasks.findMany();
for (const task of tasks) {
  task.owner = await db.users.findUnique({ where: { id: task.ownerId } });
}

// 좋음: join/include가 있는 단일 쿼리
const tasks = await db.tasks.findMany({
  include: { owner: true },
});
```

#### Unbounded Data Fetching

```typescript
// 나쁨: 모든 레코드 가져오기
const allTasks = await db.tasks.findMany();

// 좋음: 제한이 있는 페이지네이션
const tasks = await db.tasks.findMany({
  take: 20,
  skip: (page - 1) * 20,
  orderBy: { createdAt: 'desc' },
});
```

#### 이미지 최적화 누락 (프론트엔드)

```html
<!-- 나쁨: 크기 없음, 포맷 최적화 없음 -->
<img src="/hero.jpg" />

<!-- 좋음: 히어로 / LCP 이미지 — art direction + resolution switching, 높은 우선순위 -->
<!--
  두 가지 기술을 결합:
  - Art direction (media): 브레이크포인트별 다른 크롭/구성
  - Resolution switching (srcset + sizes): 화면 밀도별 올바른 파일 크기
-->
<picture>
  <!-- 모바일: 세로 크롭 (8:10) -->
  <source
    media="(max-width: 767px)"
    srcset="/hero-mobile-400.avif 400w, /hero-mobile-800.avif 800w"
    sizes="100vw"
    width="800"
    height="1000"
    type="image/avif"
  />
  <source
    media="(max-width: 767px)"
    srcset="/hero-mobile-400.webp 400w, /hero-mobile-800.webp 800w"
    sizes="100vw"
    width="800"
    height="1000"
    type="image/webp"
  />
  <!-- 데스크톱: 가로 크롭 (2:1) -->
  <source
    srcset="/hero-800.avif 800w, /hero-1200.avif 1200w, /hero-1600.avif 1600w"
    sizes="(max-width: 1200px) 100vw, 1200px"
    width="1200"
    height="600"
    type="image/avif"
  />
  <source
    srcset="/hero-800.webp 800w, /hero-1200.webp 1200w, /hero-1600.webp 1600w"
    sizes="(max-width: 1200px) 100vw, 1200px"
    width="1200"
    height="600"
    type="image/webp"
  />
  <img
    src="/hero-desktop.jpg"
    width="1200"
    height="600"
    fetchpriority="high"
    alt="히어로 이미지 설명"
  />
</picture>

<!-- 좋음: 스크롤 아래 이미지 — lazy loading + 비동기 디코딩 -->
<img
  src="/content.webp"
  width="800"
  height="400"
  loading="lazy"
  decoding="async"
  alt="콘텐츠 이미지 설명"
/>
```

#### 불필요한 리렌더링 (React)

```tsx
// 나쁨: 매 렌더마다 새 객체를 생성하여 자식이 리렌더링되게 함
function TaskList() {
  return <TaskFilters options={{ sortBy: 'date', order: 'desc' }} />;
}

// 좋음: 안정적인 참조
const DEFAULT_OPTIONS = { sortBy: 'date', order: 'desc' } as const;
function TaskList() {
  return <TaskFilters options={DEFAULT_OPTIONS} />;
}

// 비용이 많은 컴포넌트에는 React.memo 사용
const TaskItem = React.memo(function TaskItem({ task }: Props) {
  return <div>{/* 비용이 많은 렌더링 */}</div>;
});

// 비용이 많은 계산에는 useMemo 사용
function TaskStats({ tasks }: Props) {
  const stats = useMemo(() => calculateStats(tasks), [tasks]);
  return <div>{stats.completed} / {stats.total}</div>;
}
```

#### 큰 번들 크기

```typescript
// 현대 번들러(Vite, webpack 5+)는 의존성이 ESM을 제공하고
// package.json에 `sideEffects: false`로 표시된 경우 named import에서
// 자동으로 tree-shaking을 처리한다.
// import 스타일을 변경하기 전에 프로파일링하라 — 실제 이득은 splitting과 lazy loading에서 나온다.

// 좋음: 무겁고 드물게 사용되는 기능을 위한 dynamic import
const ChartLibrary = lazy(() => import('./ChartLibrary'));

// 좋음: Suspense로 감싼 라우트 레벨 code splitting
const SettingsPage = lazy(() => import('./pages/Settings'));

function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <SettingsPage />
    </Suspense>
  );
}
```

#### 캐싱 누락 (백엔드)

```typescript
// 자주 읽히고 드물게 변경되는 데이터 캐싱
const CACHE_TTL = 5 * 60 * 1000; // 5분
let cachedConfig: AppConfig | null = null;
let cacheExpiry = 0;

async function getAppConfig(): Promise<AppConfig> {
  if (cachedConfig && Date.now() < cacheExpiry) {
    return cachedConfig;
  }
  cachedConfig = await db.config.findFirst();
  cacheExpiry = Date.now() + CACHE_TTL;
  return cachedConfig;
}

// 정적 자산을 위한 HTTP 캐싱 헤더
app.use('/static', express.static('public', {
  maxAge: '1y',           // 1년 캐시
  immutable: true,        // 재검증 없음 (파일명에 콘텐츠 해싱 사용)
}));

// API 응답을 위한 Cache-Control
res.set('Cache-Control', 'public, max-age=300'); // 5분
```

## Performance Budget

예산을 설정하고 강제한다:

```
JavaScript 번들: < 200KB gzipped (초기 로드)
CSS: < 50KB gzipped
이미지: < 200KB per image (스크롤 위)
폰트: < 100KB 합계
API 응답 시간: < 200ms (p95)
Time to Interactive: < 3.5s on 4G
Lighthouse 성능 점수: ≥ 90
```

**CI에서 강제한다:**
```bash
# 번들 크기 확인
npx bundlesize --config bundlesize.config.json

# Lighthouse CI
npx lhci autorun
```

## See Also

자세한 성능 체크리스트, 최적화 명령어, anti-pattern 참조는 `references/performance-checklist.md`를 참조하라.

## Common Rationalizations

| 합리화 | 현실 |
|--------|------|
| "나중에 최적화할 것이다" | 성능 부채는 누적된다. 명백한 anti-pattern은 지금 수정하고, 미세 최적화는 나중으로 미룬다. |
| "내 기기에서는 빠르다" | 당신의 기기는 사용자의 것이 아니다. 대표적인 하드웨어와 네트워크에서 프로파일링하라. |
| "이 최적화는 명백하다" | 측정하지 않았다면 모른다. 먼저 프로파일링하라. |
| "사용자는 100ms를 알아채지 못할 것이다" | 연구에 따르면 100ms 지연이 전환율에 영향을 미친다. 사용자는 당신이 생각하는 것보다 더 많이 알아챈다. |
| "프레임워크가 성능을 처리한다" | 프레임워크는 일부 문제를 방지하지만 N+1 쿼리나 과도한 번들 크기는 수정할 수 없다. |

## Red Flags

- 정당화할 프로파일링 데이터 없이 최적화
- 데이터 가져오기에서 N+1 쿼리 패턴
- 페이지네이션 없는 목록 엔드포인트
- 크기, lazy loading, 또는 반응형 크기 없는 이미지
- 검토 없이 증가하는 번들 크기
- 프로덕션에 성능 모니터링 없음
- 모든 곳에 `React.memo`와 `useMemo` (과도 사용은 미사용만큼 나쁘다)

## Verification

성능 관련 변경 후:

- [ ] 변경 전후 측정이 존재한다 (구체적인 수치)
- [ ] 특정 병목 지점이 파악되고 해결되었다
- [ ] Core Web Vitals가 "좋음" 기준 내에 있다
- [ ] 번들 크기가 크게 증가하지 않았다
- [ ] 새 데이터 가져오기 코드에 N+1 쿼리가 없다
- [ ] CI에서 성능 예산이 통과한다 (설정된 경우)
- [ ] 기존 테스트가 여전히 통과한다 (최적화가 동작을 망가뜨리지 않았다)
