---
name: ci-cd-and-automation
description: CI/CD 파이프라인 설정을 자동화합니다. 빌드 및 배포 파이프라인을 설정하거나 수정할 때 사용하세요. 품질 게이트를 자동화하거나, CI에서 테스트 러너를 설정하거나, 배포 전략을 수립할 때 사용하세요.
---

# CI/CD and Automation

## 개요

어떤 변경도 테스트, 린트, 타입 검사, 빌드를 통과하지 않고는 프로덕션에 도달하지 못하도록 품질 게이트를 자동화하세요. CI/CD는 다른 모든 스킬을 위한 강제 메커니즘입니다 — 사람과 에이전트가 놓치는 것을 잡아내며, 모든 단일 변경에 대해 일관되게 그렇게 합니다.

**Shift Left:** 파이프라인에서 가능한 한 일찍 문제를 잡으세요. 린팅에서 잡힌 버그는 몇 분을 소비합니다; 프로덕션에서 잡힌 동일한 버그는 몇 시간을 소비합니다. 검사를 상류로 이동하세요 — 테스트 이전에 정적 분석, 스테이징 이전에 테스트, 프로덕션 이전에 스테이징.

**더 빠를수록 더 안전합니다:** 더 작은 배치와 더 잦은 릴리스는 위험을 낮추지, 높이지 않습니다. 3개의 변경이 있는 배포는 30개가 있는 것보다 디버깅하기 쉽습니다. 잦은 릴리스는 릴리스 프로세스 자체에 대한 신뢰를 쌓습니다.

## 언제 사용할까

- 새 프로젝트의 CI 파이프라인 설정 시
- 자동화된 검사 추가 또는 수정 시
- 배포 파이프라인 설정 시
- 변경이 자동화된 검증을 트리거해야 할 때
- CI 실패 디버깅 시

## 품질 게이트 파이프라인

모든 변경은 머지 전에 이 게이트들을 통과합니다:

```
Pull Request 열림
    │
    ▼
┌─────────────────┐
│   LINT CHECK     │  eslint, prettier
│   ↓ 통과         │
│   TYPE CHECK     │  tsc --noEmit
│   ↓ 통과         │
│   UNIT TESTS     │  jest/vitest
│   ↓ 통과         │
│   BUILD          │  npm run build
│   ↓ 통과         │
│   INTEGRATION    │  API/DB 테스트
│   ↓ 통과         │
│   E2E (선택)     │  Playwright/Cypress
│   ↓ 통과         │
│   SECURITY AUDIT │  npm audit
│   ↓ 통과         │
│   BUNDLE SIZE    │  bundlesize 확인
└─────────────────┘
    │
    ▼
  리뷰 준비 완료
```

**어떤 게이트도 건너뛸 수 없습니다.** 린트가 실패하면 린트를 수정하세요 — 규칙을 비활성화하지 마세요. 테스트가 실패하면 코드를 수정하세요 — 테스트를 건너뛰지 마세요.

## GitHub Actions 설정

### 기본 CI 파이프라인

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npx tsc --noEmit

      - name: Test
        run: npm test -- --coverage

      - name: Build
        run: npm run build

      - name: Security audit
        run: npm audit --audit-level=high
```

### 데이터베이스 통합 테스트 포함

```yaml
  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: ci_user
          POSTGRES_PASSWORD: ${{ secrets.CI_DB_PASSWORD }}
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - name: Run migrations
        run: npx prisma migrate deploy
        env:
          DATABASE_URL: postgresql://ci_user:${{ secrets.CI_DB_PASSWORD }}@localhost:5432/testdb
      - name: Integration tests
        run: npm run test:integration
        env:
          DATABASE_URL: postgresql://ci_user:${{ secrets.CI_DB_PASSWORD }}@localhost:5432/testdb
```

> **참고:** CI 전용 테스트 데이터베이스에도 값을 하드코딩하는 대신 GitHub Secrets를 사용하세요. 이는 좋은 습관을 만들고 테스트 자격증명이 다른 컨텍스트에서 실수로 재사용되는 것을 방지합니다.

### E2E 테스트

```yaml
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - name: Install Playwright
        run: npx playwright install --with-deps chromium
      - name: Build
        run: npm run build
      - name: Run E2E tests
        run: npx playwright test
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

## CI 실패를 에이전트에 피드백

AI 에이전트와 함께하는 CI의 강점은 피드백 루프입니다. CI가 실패하면:

```
CI 실패
    │
    ▼
실패 출력 복사
    │
    ▼
에이전트에 전달:
"CI 파이프라인이 다음 오류로 실패했습니다:
[특정 오류 붙여넣기]
문제를 수정하고 다시 푸시하기 전에 로컬에서 검증하세요."
    │
    ▼
에이전트 수정 → 푸시 → CI 재실행
```

**핵심 패턴:**

```
Lint 실패    → 에이전트가 `npm run lint --fix` 실행 후 커밋
Type 오류    → 에이전트가 오류 위치를 읽고 타입 수정
Test 실패    → 에이전트가 debugging-and-error-recovery 스킬 따름
Build 오류   → 에이전트가 설정과 의존성 확인
```

## 배포 전략

### Preview 배포

모든 PR은 수동 테스트를 위한 preview 배포를 받습니다:

```yaml
# PR에서 preview 배포 (Vercel/Netlify/등)
deploy-preview:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - uses: actions/checkout@v4
    - name: Deploy preview
      run: npx vercel --token=${{ secrets.VERCEL_TOKEN }}
```

### Feature Flags

Feature flags는 배포와 릴리스를 분리합니다. 불완전하거나 위험한 기능을 플래그 뒤에 배포하면 다음이 가능합니다:

- **활성화하지 않고 코드를 배포할 수 있습니다.** 일찍 main에 머지하고, 준비되면 활성화하세요.
- **재배포 없이 롤백할 수 있습니다.** 코드를 되돌리는 대신 플래그를 비활성화하세요.
- **새 기능을 카나리 배포할 수 있습니다.** 사용자의 1%에 활성화하고, 그 다음 10%, 그 다음 100%.
- **A/B 테스트를 실행할 수 있습니다.** 기능이 있는 경우와 없는 경우의 동작을 비교하세요.

```typescript
// 간단한 feature flag 패턴
if (featureFlags.isEnabled('new-checkout-flow', { userId })) {
  return renderNewCheckout();
}
return renderLegacyCheckout();
```

**플래그 수명주기:** 생성 → 테스트를 위해 활성화 → 카나리 → 전체 롤아웃 → 플래그와 죽은 코드 제거. 영원히 사는 플래그는 기술 부채가 됩니다 — 플래그를 생성할 때 정리 날짜를 설정하세요.

### 단계적 롤아웃

```
PR이 main에 머지됨
    │
    ▼
  Staging 배포 (자동)
    │ 수동 검증
    ▼
  Production 배포 (수동 트리거 또는 staging 후 자동)
    │
    ▼
  에러 모니터링 (15분 창)
    │
    ├── 에러 감지 → 롤백
    └── 깨끗함 → 완료
```

### 롤백 계획

모든 배포는 되돌릴 수 있어야 합니다:

```yaml
# 수동 롤백 워크플로우
name: Rollback
on:
  workflow_dispatch:
    inputs:
      version:
        description: '롤백할 버전'
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    steps:
      - name: Rollback deployment
        run: |
          # 지정된 이전 버전 배포
          npx vercel rollback ${{ inputs.version }}
```

## 환경 관리

```
.env.example       → 커밋됨 (개발자를 위한 템플릿)
.env                → 커밋 안 됨 (로컬 개발)
.env.test           → 커밋됨 (테스트 환경, 실제 시크릿 없음)
CI 시크릿          → GitHub Secrets / vault에 저장
Production 시크릿  → 배포 플랫폼 / vault에 저장
```

CI는 프로덕션 시크릿을 가져서는 안 됩니다. CI 테스트를 위해 별도의 시크릿을 사용하세요.

## CI 이외의 자동화

### Dependabot / Renovate

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: npm
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
```

### Build Cop 역할

CI를 그린 상태로 유지하는 책임자를 지정하세요. 빌드가 깨지면, Build Cop의 역할은 수정하거나 되돌리는 것입니다 — 변경을 유발한 사람이 아닙니다. 이는 모두가 다른 사람이 수정할 것이라 가정하면서 깨진 빌드가 쌓이는 것을 방지합니다.

### PR 검사

- **필수 리뷰:** 머지 전 최소 1개의 승인
- **필수 상태 검사:** 머지 전 CI 통과 필수
- **브랜치 보호:** main에 강제 푸시 금지
- **자동 머지:** 모든 검사가 통과하고 승인되면 자동으로 머지

## CI 최적화

파이프라인이 10분을 초과할 때, 다음 전략을 영향도 순서로 적용하세요:

```
느린 CI 파이프라인?
├── 의존성 캐싱
│   └── node_modules에 actions/cache 또는 setup-node cache 옵션 사용
├── 병렬 작업 실행
│   └── lint, typecheck, test, build를 별도의 병렬 작업으로 분리
├── 변경된 것만 실행
│   └── 경로 필터를 사용해 관련 없는 작업 건너뜀 (예: docs 전용 PR에서 e2e 건너뜀)
├── matrix 빌드 사용
│   └── 여러 러너에 걸쳐 테스트 스위트를 샤딩
├── 테스트 스위트 최적화
│   └── 느린 테스트를 크리티컬 경로에서 제거하고 스케줄로 실행
└── 더 큰 러너 사용
    └── GitHub 호스팅 대형 러너 또는 CPU 집약적 빌드를 위한 자체 호스팅
```

**예시: 캐싱과 병렬화**
```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22', cache: 'npm' }
      - run: npm ci
      - run: npm run lint

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22', cache: 'npm' }
      - run: npm ci
      - run: npx tsc --noEmit

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22', cache: 'npm' }
      - run: npm ci
      - run: npm test -- --coverage
```

## 흔한 합리화

| 합리화 | 현실 |
|---|---|
| "CI가 너무 느립니다" | 파이프라인을 최적화하세요 (아래 CI 최적화 참조), 건너뛰지 마세요. 5분 파이프라인은 수시간의 디버깅을 방지합니다. |
| "이 변경은 사소하니 CI를 건너뛰겠습니다" | 사소한 변경도 빌드를 깨뜨립니다. CI는 사소한 변경에 대해서도 빠릅니다. |
| "테스트가 불안정합니다, 그냥 재실행합시다" | 불안정한 테스트는 실제 버그를 가리고 모두의 시간을 낭비합니다. 불안정함을 수정하세요. |
| "나중에 CI를 추가하겠습니다" | CI가 없는 프로젝트는 깨진 상태가 쌓입니다. 첫날에 설정하세요. |
| "수동 테스트로 충분합니다" | 수동 테스트는 확장되지 않고 반복 가능하지 않습니다. 할 수 있는 것을 자동화하세요. |

## 위험 신호

- 프로젝트에 CI 파이프라인 없음
- 무시되거나 묵살된 CI 실패
- 파이프라인을 통과시키기 위해 CI에서 비활성화된 테스트
- 스테이징 검증 없는 프로덕션 배포
- 롤백 메커니즘 없음
- 코드 또는 CI 설정 파일에 저장된 시크릿 (시크릿 매니저 아님)
- 최적화 노력 없는 긴 CI 시간

## 검증

CI를 설정하거나 수정한 후:

- [ ] 모든 품질 게이트가 존재함 (lint, types, tests, build, audit)
- [ ] 파이프라인이 모든 PR과 main 푸시에서 실행됨
- [ ] 실패가 머지를 차단함 (브랜치 보호 설정됨)
- [ ] CI 결과가 개발 루프에 피드백됨
- [ ] 시크릿이 코드가 아닌 시크릿 매니저에 저장됨
- [ ] 배포에 롤백 메커니즘이 있음
- [ ] 파이프라인이 테스트 스위트에 대해 10분 미만으로 실행됨
