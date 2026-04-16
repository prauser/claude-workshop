---
name: git-workflow-and-versioning
description: Structures git workflow practices. Use when making any code change. Use when committing, branching, resolving conflicts, or when you need to organize work across multiple parallel streams.
---

# Git Workflow and Versioning

## Overview

Git은 당신의 안전망이다. 커밋을 저장 지점으로, 브랜치를 샌드박스로, 기록을 문서로 취급하라. AI 에이전트가 고속으로 코드를 생성하는 환경에서 규율 있는 버전 관리는 변경 사항을 관리 가능하고, 검토 가능하며, 되돌릴 수 있게 하는 메커니즘이다.

## When to Use

항상. 모든 코드 변경은 git을 통해 흐른다.

## Core Principles

### Trunk-Based Development (권장)

`main`을 항상 배포 가능한 상태로 유지한다. 1-3일 안에 다시 병합되는 단명 feature 브랜치에서 작업한다. 장기간 유지되는 개발 브랜치는 숨겨진 비용이다 — 분기되고, 병합 충돌을 만들고, 통합을 지연시킨다. DORA 연구는 trunk-based development가 고성능 엔지니어링 팀과 일관되게 상관관계가 있음을 보여준다.

```
main ──●──●──●──●──●──●──●──●──●──  (항상 배포 가능)
        ╲      ╱  ╲    ╱
         ●──●─╱    ●──╱    ← 단명 feature 브랜치 (1-3일)
```

이것이 권장 기본값이다. gitflow 또는 장기간 브랜치를 사용하는 팀은 원칙(원자적 커밋, 소규모 변경, 설명적 메시지)을 자신의 브랜칭 모델에 적용할 수 있다 — 특정 브랜칭 전략보다 커밋 규율이 더 중요하다.

- **개발 브랜치는 비용이다.** 브랜치가 살아있는 매일 병합 위험이 누적된다.
- **릴리스 브랜치는 허용된다.** main이 앞으로 나아가는 동안 릴리스를 안정화해야 할 때.
- **Feature flag > 장기 브랜치.** 몇 주 동안 브랜치를 유지하는 것보다 미완성 작업을 flag 뒤에 배포하는 것을 선호한다.

### 1. 일찍 자주 커밋

성공적인 각 단계는 자체 커밋을 갖는다. 커밋되지 않은 대규모 변경이 쌓이도록 하지 않는다.

```
작업 패턴:
  슬라이스 구현 → 테스트 → 확인 → 커밋 → 다음 슬라이스

이렇게 하지 않는다:
  모든 것 구현 → 작동하길 바라기 → 거대한 커밋
```

커밋은 저장 지점이다. 다음 변경이 무언가를 망가뜨리면, 즉시 마지막으로 알려진 정상 상태로 되돌릴 수 있다.

### 2. Atomic Commits

각 커밋은 하나의 논리적인 일을 한다:

```
# 좋음: 각 커밋이 독립적
git log --oneline
a1b2c3d 유효성 검사를 포함한 태스크 생성 엔드포인트 추가
d4e5f6g 태스크 생성 폼 컴포넌트 추가
h7i8j9k 폼을 API에 연결하고 로딩 상태 추가
m1n2o3p 태스크 생성 테스트 추가 (단위 + 통합)

# 나쁨: 모든 것이 섞임
git log --oneline
x1y2z3a 태스크 기능 추가, 사이드바 수정, 의존성 업데이트, utils 리팩터
```

### 3. Descriptive Messages

커밋 메시지는 *무엇*뿐만 아니라 *이유*를 설명한다:

```
# 좋음: 의도를 설명함
feat: 등록 엔드포인트에 이메일 유효성 검사 추가

유효하지 않은 이메일 형식이 데이터베이스에 도달하는 것을 방지한다.
auth.ts의 기존 유효성 검사 패턴과 일관되게
라우트 핸들러 레벨에서 Zod 스키마 유효성 검사를 사용한다.

# 나쁨: diff에서 명백한 것을 설명함
auth.ts 업데이트
```

**형식:**
```
<type>: <짧은 설명>

<선택적 본문 — 무엇이 아닌 왜를 설명>
```

**Types:**
- `feat` — 새 기능
- `fix` — 버그 수정
- `refactor` — 버그를 수정하지도 기능을 추가하지도 않는 코드 변경
- `test` — 테스트 추가 또는 업데이트
- `docs` — 문서화만
- `chore` — 도구, 의존성, 설정

### 4. 관심사를 분리

포맷팅 변경과 동작 변경을 합치지 않는다. 리팩터링과 기능을 합치지 않는다. 각 변경 유형은 별도의 커밋이어야 한다 — 이상적으로는 별도의 PR:

```
# 좋음: 관심사 분리
git commit -m "refactor: 유효성 검사 로직을 공유 유틸리티로 추출"
git commit -m "feat: 등록에 전화번호 유효성 검사 추가"

# 나쁨: 혼합된 관심사
git commit -m "유효성 검사 리팩터링 및 전화번호 필드 추가"
```

**리팩터링을 기능 작업에서 분리한다.** 리팩터링 변경과 기능 변경은 두 가지 다른 변경이다 — 별도로 제출한다. 이렇게 하면 각 변경을 검토하고, 되돌리고, 기록에서 이해하기 쉬워진다. 소규모 정리 (변수 이름 변경)는 검토자 재량으로 기능 커밋에 포함될 수 있다.

### 5. 변경 규모 조절

커밋/PR당 약 100줄을 목표로 한다. 약 1000줄 이상의 변경은 분리해야 한다. 큰 변경을 분리하는 방법은 `code-review-and-quality`의 분리 전략을 참조한다.

```
~100줄  → 검토하기 쉽고, 되돌리기 쉬움
~300줄  → 단일 논리적 변경으로 허용 가능
~1000줄 → 더 작은 변경으로 분리
```

## Branching Strategy

### Feature Branches

```
main (항상 배포 가능)
  │
  ├── feature/task-creation    ← 브랜치당 하나의 기능
  ├── feature/user-settings    ← 병렬 작업
  └── fix/duplicate-tasks      ← 버그 수정
```

- `main`(또는 팀의 기본 브랜치)에서 분기
- 브랜치를 단명으로 유지 (1-3일 안에 병합) — 장기간 브랜치는 숨겨진 비용
- 병합 후 브랜치 삭제
- 미완성 기능을 위한 장기간 브랜치보다 feature flag 선호

### Branch Naming

```
feature/<짧은-설명>   → feature/task-creation
fix/<짧은-설명>       → fix/duplicate-tasks
chore/<짧은-설명>     → chore/update-deps
refactor/<짧은-설명>  → refactor/auth-module
```

## Working with Worktrees

병렬 AI 에이전트 작업을 위해 git worktrees를 사용하여 여러 브랜치를 동시에 실행한다:

```bash
# feature 브랜치에 대한 worktree 생성
git worktree add ../project-feature-a feature/task-creation
git worktree add ../project-feature-b feature/user-settings

# 각 worktree는 자체 브랜치를 가진 별도 디렉터리
# 에이전트들이 서로 간섭 없이 병렬로 작업할 수 있음
ls ../
  project/              ← main 브랜치
  project-feature-a/    ← task-creation 브랜치
  project-feature-b/    ← user-settings 브랜치

# 완료 후 병합하고 정리
git worktree remove ../project-feature-a
```

장점:
- 여러 에이전트가 동시에 다른 기능을 작업할 수 있음
- 브랜치 전환 불필요 (각 디렉터리에 자체 브랜치 있음)
- 실험이 실패하면 worktree를 삭제 — 아무것도 잃지 않음
- 변경 사항은 명시적으로 병합될 때까지 격리됨

## The Save Point Pattern

```
에이전트가 작업 시작
    │
    ├── 변경을 만든다
    │   ├── 테스트 통과? → 커밋 → 계속
    │   └── 테스트 실패? → 마지막 커밋으로 되돌리기 → 조사
    │
    ├── 또 다른 변경을 만든다
    │   ├── 테스트 통과? → 커밋 → 계속
    │   └── 테스트 실패? → 마지막 커밋으로 되돌리기 → 조사
    │
    └── 기능 완성 → 모든 커밋이 깔끔한 기록을 형성
```

이 패턴은 한 번에 하나의 작업 단계 이상을 잃지 않는다는 것을 의미한다. 에이전트가 잘못된 방향으로 가면, `git reset --hard HEAD`로 마지막 성공 상태로 되돌아간다.

## Change Summaries

모든 수정 후 구조화된 요약을 제공한다. 이는 검토를 쉽게 만들고, 범위 규율을 문서화하며, 의도하지 않은 변경 사항을 드러낸다:

```
변경 사항:
- src/routes/tasks.ts: POST 엔드포인트에 유효성 검사 미들웨어 추가
- src/lib/validation.ts: Zod를 사용한 TaskCreateSchema 추가

의도적으로 건드리지 않은 것:
- src/routes/auth.ts: 유사한 유효성 검사 gap이 있지만 범위 외
- src/middleware/error.ts: 오류 형식을 개선할 수 있음 (별도 작업)

잠재적 우려 사항:
- Zod 스키마가 엄격함 — 추가 필드를 거부함. 이것이 원하는 것인지 확인이 필요.
- zod를 의존성으로 추가 (72KB gzipped) — 이미 package.json에 있음
```

이 패턴은 잘못된 가정을 일찍 발견하고 검토자에게 변경의 명확한 지도를 제공한다. "건드리지 않은 것" 섹션이 특히 중요하다 — 범위 규율을 발휘했고 요청하지 않은 리노베이션을 하지 않았음을 보여준다.

## Pre-Commit Hygiene

모든 커밋 전에:

```bash
# 1. 커밋하려는 것을 확인
git diff --staged

# 2. 비밀 정보가 없는지 확인
git diff --staged | grep -i "password\|secret\|api_key\|token"

# 3. 테스트 실행
npm test

# 4. 린팅 실행
npm run lint

# 5. 타입 검사 실행
npx tsc --noEmit
```

git hooks로 자동화한다:

```json
// package.json (lint-staged + husky 사용)
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{json,md}": ["prettier --write"]
  }
}
```

## Handling Generated Files

- **생성된 파일을 커밋**하는 것은 프로젝트가 기대하는 경우에만 (예: `package-lock.json`, Prisma 마이그레이션)
- **커밋하지 않을 것:** 빌드 출력 (`dist/`, `.next/`), 환경 파일 (`.env`), IDE 설정 (공유하지 않는 `.vscode/settings.json`)
- **`.gitignore`를 가져야 한다**: `node_modules/`, `dist/`, `.env`, `.env.local`, `*.pem`을 포함

## Using Git for Debugging

```bash
# 버그를 도입한 커밋 찾기
git bisect start
git bisect bad HEAD
git bisect good <알려진-정상-커밋>
# Git이 중간 지점을 체크아웃; 각 지점에서 테스트를 실행하여 범위를 좁힘

# 최근 변경 사항 보기
git log --oneline -20
git diff HEAD~5..HEAD -- src/

# 특정 줄을 마지막으로 변경한 사람 찾기
git blame src/services/task.ts

# 키워드로 커밋 메시지 검색
git log --grep="validation" --oneline
```

## Common Rationalizations

| 합리화 | 현실 |
|--------|------|
| "기능이 완성되면 커밋할 것이다" | 하나의 거대한 커밋은 검토하거나, 디버깅하거나, 되돌리기 불가능하다. 각 슬라이스를 커밋하라. |
| "메시지는 중요하지 않다" | 메시지는 문서다. 미래의 당신 (그리고 미래의 에이전트들)이 무엇이 변경되었고 왜인지 이해해야 할 것이다. |
| "나중에 모두 squash할 것이다" | Squashing은 개발 서사를 파괴한다. 처음부터 깔끔한 점진적 커밋을 선호한다. |
| "브랜치는 오버헤드를 추가한다" | 단명 브랜치는 무료이며 충돌하는 작업이 충돌하는 것을 방지한다. 장기간 브랜치가 문제 — 1-3일 안에 병합한다. |
| "나중에 이 변경을 분리할 것이다" | 큰 변경은 검토하기 더 어렵고, 배포하기 더 위험하며, 되돌리기 더 어렵다. 제출 전에 분리하라, 후가 아니라. |
| ".gitignore가 필요 없다" | 프로덕션 비밀이 있는 `.env`가 커밋될 때까지는. 즉시 설정한다. |

## Red Flags

- 대규모 커밋되지 않은 변경이 쌓임
- "fix", "update", "misc" 같은 커밋 메시지
- 동작 변경과 섞인 포맷팅 변경
- 프로젝트에 `.gitignore` 없음
- `node_modules/`, `.env`, 또는 빌드 아티팩트 커밋
- main에서 크게 분기된 장기간 브랜치
- 공유 브랜치에 force push

## Verification

모든 커밋에 대해:

- [ ] 커밋이 하나의 논리적인 일을 한다
- [ ] 메시지가 이유를 설명하고 타입 규칙을 따른다
- [ ] 커밋 전에 테스트가 통과한다
- [ ] diff에 비밀 정보가 없다
- [ ] 동작 변경과 혼합된 포맷팅 전용 변경이 없다
- [ ] `.gitignore`가 표준 제외 사항을 포함한다
