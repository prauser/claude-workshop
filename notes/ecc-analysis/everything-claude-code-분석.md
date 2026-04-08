---
date: 2026-04-09
purpose: Everything Claude Code(ECC) 레포지토리 종합 분석 — 구조, 패턴, claude-workshop과의 비교, 전사 적용 가이드
---

# Everything Claude Code (ECC) 종합 분석

## 목차

1. [구조 분석](#1-구조-분석)
   - 1.1 [Memory Persistence — 세션 간 컨텍스트 자동 저장/복원](#11-memory-persistence--세션-간-컨텍스트-자동-저장복원)
   - 1.2 [Continuous Learning — 세션에서 패턴 자동 추출](#12-continuous-learning--세션에서-패턴-자동-추출)
   - 1.3 [Verification Loops — 평가 전략과 메트릭](#13-verification-loops--평가-전략과-메트릭)
   - 1.4 [Parallelization — Git Worktree와 Cascade](#14-parallelization--git-worktree와-cascade)
   - 1.5 [Subagent Orchestration — 컨텍스트 문제와 반복 검색](#15-subagent-orchestration--컨텍스트-문제와-반복-검색)
   - 1.6 [Rules 동작 방식](#16-rules-동작-방식)
2. [agentlens와의 비교 및 통합 분석](#2-agentlens와의-비교-및-통합-분석)
3. [전사 레벨 적용 분석](#3-전사-레벨-적용-분석)
4. [현재 레포(claude-workshop)와의 비교](#4-현재-레포claude-workshop와의-비교)
5. [ECC 선택적 적용 가이드](#5-ecc-선택적-적용-가이드)
6. [자동 분석 + 인간 승인 모델](#6-자동-분석--인간-승인-모델)

---

## 1. 구조 분석

### 1.1 Memory Persistence — 세션 간 컨텍스트 자동 저장/복원

**핵심 개념:** 세션의 전체 라이프사이클을 Hook으로 커버하여, 대화가 끝나도 맥락이 사라지지 않게 만드는 구조.

#### 구현 메커니즘

| Hook | 역할 |
|------|------|
| `SessionStart` | 이전 세션 데이터를 `~/.claude/session-data/`에서 로드 |
| `PreCompact` | 압축 타임스탬프를 세션 파일에 마킹 (컨텍스트 손실 추적) |
| `Stop:session-end` | JSONL 트랜스크립트에서 사용자 메시지/도구/파일 추출, 마크다운으로 저장. 멱등적 요약 업데이트 (`ECC:SUMMARY:START/END` 마커로 매번 교체, 무한 증식 방지) |
| `SessionEnd` | 정리 마커 |

#### 주요 커맨드

- **`/save-session`**: "실패한 것", "시도하지 않은 것" 섹션 포함 → 다음 세션 실수 반복 방지
- **`/sessions`**: 과거 세션 CRUD (목록, 로드, 별칭, 검색)
- **Strategic Compact 스킬**: 임의 자동압축 대신 논리적 경계점에서 수동 `/compact` 권장

#### 사용된 Claude Code 기능

`Hooks (SessionStart, PreCompact, Stop, SessionEnd)`, `Commands`, `Skills`

---

### 1.2 Continuous Learning — 세션에서 패턴 자동 추출

**핵심 개념:** 세션에서 반복되는 행동 패턴을 감지하여 재사용 가능한 Skill/Instinct로 자동 승격시키는 자기 개선 루프.

#### v1 — Stop Hook 방식

1. `Stop:evaluate-session` → 트랜스크립트 읽기
2. 사용자 메시지 10개 이상이면 패턴 추출 트리거
3. `~/.claude/skills/learned/`에 `SKILL.md`로 저장

#### v2 — Background Observer (Homunculus 영감)

1. `PreToolUse` / `PostToolUse` 훅이 모든 도구 사용을 JSONL로 기록
2. 20개마다 `SIGUSR1` → 백그라운드 `observer-loop.sh`에 시그널
3. 재진입 방지 + 60초 쿨다운 체크
4. Haiku 모델(`claude --model haiku`)이 최근 500줄 분석 → Instinct 파일 생성 (`confidence 0.3~0.85`, `domain/scope` 태깅)
5. 분석 완료 후 관측 데이터 아카이브

#### Skill Evolution 서브시스템

| 항목 | 설명 |
|------|------|
| **Provenance** | `curated` (레포) / `learned` (자동) / `imported` (외부) 분류 |
| **Versioning** | 스냅샷 + 롤백 |
| **Health Metrics** | 7일/30일 성공률, 하락 감지 → 품질 자동 관리 |
| **`/learn-eval` 커맨드** | 수동 추출 + 체크리스트 기반 품질 게이트 (Save / Improve / Absorb / Drop) |

---

### 1.3 Verification Loops — 평가 전략과 메트릭

**핵심 개념:** Eval-Driven Development (EDD) — 코드 작성 전에 평가 기준을 먼저 정의하고, 다양한 Grader로 검증.

#### Checkpoint vs Continuous

| 유형 | 트리거 | 내용 |
|------|--------|------|
| **Checkpoint** | 함수/컴포넌트 완성 후, PR 전 | TDD의 RED → GREEN → REFACTOR 각 단계에서 git commit |
| **Continuous** | 15~60분 간격 또는 주요 변경 후 | 6단계 루프: Build → Type Check → Lint → Test → Security → Diff Review |

#### 4가지 Grader 유형

| Grader | 방식 | 예시 |
|--------|------|------|
| **Code-based** | bash 명령으로 결정적 검증 | `npm test`, `grep` |
| **Rule-based** | regex/schema 제약 | JSON Schema 검증 |
| **Model-based** | LLM-as-judge, 1~5점 루브릭 | 코드 품질 평가 |
| **Human** | 수동 리뷰 플래그 | 위험도 기반 에스컬레이션 |
| **Compliance (`skill-comply`)** | LLM이 도구 호출 트레이스를 분류 + 시간순 검증 | 스킬 준수율 측정 |

#### pass@k vs pass^k

| 메트릭 | 의미 | 목표 | 특성 |
|--------|------|------|------|
| **pass@k** | k번 시도 중 1번이라도 성공 | pass@3 ≥ 90% | 낙관적 |
| **pass^k** | k번 모두 성공 | pass^3 = 100% | 엄격 (회귀/릴리스 경로) |

```
pass@1 = 70% → pass@3 = 91% → pass@5 = 97%
```

#### 특수 패턴

- **GAN-style Harness**: Generator와 Evaluator(Playwright) 에이전트를 분리 → 에이전트의 "자기평가 낙관편향" 해결
- **Healthcare Eval**: `CRITICAL` (100%) / `HIGH` (95%+) 티어 게이트

---

### 1.4 Parallelization — Git Worktree와 Cascade

**핵심 개념:** "Minimum Viable Parallelization" — 필요한 최소한의 병렬화만.

#### Git Worktree 오케스트레이션

```
plan.json → orchestrate-worktrees.js → tmux-worktree-orchestrator.js
```

1. **Plan 빌드**: worker마다 branch + worktree + tmux 커맨드 생성
2. **실행**: worktree 생성 → seed paths 복사(커밋 안 된 파일 포함) → tmux 세션 분할 → worker 실행
3. **롤백**: 실패 시 실제 생성된 리소스만 정리

> 주의: worktree에서 `.git`은 디렉토리가 아닌 파일이므로 `[ -e .git ]` 사용 필수

#### Cascade Method (인간 워크플로우)

새 작업은 오른쪽 탭에 열기, 왼→오 순서로 스윕, 동시 3~4개 집중

#### 스케일링 지침

| 패턴 | 설명 |
|------|------|
| **2-Instance Kickoff** | 새 레포에서 1개는 스캐폴딩, 1개는 리서치/PRD |
| **Team Builder** | 최대 5개 에이전트 병렬 (그 이상은 수확체감) |
| **dmux 통합** | tmux pane 관리자 + 5가지 워크플로우 패턴 |

---

### 1.5 Subagent Orchestration — 컨텍스트 문제와 반복 검색

**The Context Problem:** 서브에이전트는 컨텍스트 절약을 위해 존재하지만, 오케스트레이터가 가진 의미적 맥락(요청의 목적)을 물려받지 못한다.

#### Iterative Retrieval Pattern (핵심 해결책)

```
DISPATCH (광범위 키워드 검색)
  → EVALUATE (파일별 관련성 0.0~1.0 점수, 갭 식별)
    → REFINE (발견된 용어로 검색 기준 갱신)
      → LOOP (최대 3회, 고관련성 파일 3+개 확보 시 종료)
```

> 핵심 통찰: 1회차에서 코드베이스 고유 용어를 발견 (예: "rate limit" 대신 "throttle" 사용)

#### Sequential Phases Orchestrator

```
RESEARCH (Explore) → research-summary.md
  → PLAN (Planner) → plan.md
    → IMPLEMENT (TDD) → code changes
      → REVIEW (Reviewer) → review-comments.md
        → VERIFY (Build Resolver) → done or loop
```

- 각 에이전트는 **1 입력 → 1 출력**
- 중간 결과는 파일 시스템에 저장 (= inter-agent 통신 채널)
- 에이전트 간 `/clear`로 컨텍스트 해제

#### Context 최적화

| 항목 | 비고 |
|------|------|
| Agent description | 모든 Task 호출에 로딩됨 → 비대하면 토큰 낭비 |
| MCP 도구 | 도구당 ~500 토큰 → 30개 MCP는 모든 스킬 합산보다 비쌈 |
| Trigger table lazy loading | 기본 컨텍스트 50%+ 절감 |

---

### 1.6 Rules 동작 방식

#### 두 가지 계층

| 계층 | 경로 | 적용 범위 |
|------|------|-----------|
| User-level | `~/.claude/CLAUDE.md` + `~/.claude/rules/*.md` | 모든 프로젝트 |
| Project-level | `./CLAUDE.md` + `.claude/rules/*.md` | 해당 프로젝트만 |

#### 핵심 차이 — CLAUDE.md vs rules/

| 항목 | CLAUDE.md | `.claude/rules/*.md` |
|------|-----------|----------------------|
| 권한 수준 | user message 수준 | 시스템 주입 — LLM이 무시 불가 |
| 로딩 방식 | 모델이 읽는 대화형 가이드 | 자동 로딩 |
| 상위 권한 | `claude --system-prompt` | — |

> `system prompt > user message > tool result`

#### Rules 디렉토리 구조

```
.claude/rules/
├── common/      # 범용 규칙
├── typescript/  # TypeScript 특화
└── python/      # Python 특화
```

#### Rules vs Skills

| 항목 | Rules | Skills |
|------|-------|--------|
| 특성 | 결정적, always-on 제약 | 온디맨드 워크플로우 |
| 로딩 | 항상 로드됨 | 필요 시만 로드 |
| 톤 | "~하라" / "~하지 마라" | "~하는 방법" (플레이북) |
| 복잡도 | Lean 유지 (300줄 이상이면 경고) | 복잡한 절차 OK |

> 유지보수: `rules-distill` 스킬 — 2+ 스킬에 등장하는 원칙을 자동 감지 → Rules로 승격 제안

#### Claude Code Rules 공식 지원

- 정식 기능이며 Cursor의 `.cursorrules`와는 별개의 네이티브 시스템
- **4단계 로딩 계층**:

| 우선순위 | 경로 | 설명 |
|----------|------|------|
| 최하 | `/etc/claude-code/CLAUDE.md` | 관리자 정책 |
| 하 | `~/.claude/` | User 레벨 |
| 중 | `./` | Project 레벨 |
| 최상 | `./CLAUDE.local.md` | Local 오버라이드 |

- **Cursor와의 차이**: 모듈화(`.claude/rules/`), 계층(4단계), Path 스코핑, `@import`, Auto Memory 지원
- **AGENTS.md**: 2026년 Google, OpenAI, Sourcegraph, Cursor, Factory가 채택한 범용 표준

---

## 2. agentlens와의 비교 및 통합 분석

### 두 접근법의 근본적 차이

| 항목 | ECC | agentlens / context-central |
|------|-----|-----------------------------|
| **데이터 수집** | 실시간 Hook — PreToolUse/PostToolUse/Stop 훅이 매 도구 호출마다 이벤트 캡처 | 사후 파싱 — Claude Code가 이미 기록하는 JSONL을 나중에 파싱 |
| **분석 주체** | 인라인 LLM — Haiku가 백그라운드에서 관측 데이터 분석 | 별도 에이전트 — Improver/Curator가 독립 프로세스로 분석 |
| **출력물** | Instinct/Skill 파일 (`.claude/skills/learned/`) | 정제된 knowledge + skills 파일 + changelog |
| **통신 방식** | 시그널 기반 (SIGUSR1) + 파일 | 파일 기반 git repo (대화 패턴 명시적 거부) |
| **인간 개입** | `/learn-eval` 수동 커맨드 | 대시보드 (Knowledge Feed, Pending Review, Approve/Reject) |
| **현재 구현** | 완전 구현 | Parser/CLI만 구현, Improver/Curator는 설계 문서 |

#### 핵심 설계 철학 차이

- **ECC**: "실시간 관측 → 즉시 학습" — 세션 중에도 Instinct가 생성될 수 있음
- **agentlens**: "기록 후 개선 (record then improve)" — Hook은 품질 게이트 전용, 세션 끝난 뒤 별도 프로세스가 분석

---

### 통합 구조

통합은 가능하며 상호보완적:

```
[세션 실행 중]
  Claude Code 기본 JSONL 기록
  + ECC Stop:session-end → 구조화된 요약 저장
  + (선택적) ECC PreToolUse/PostToolUse → 실시간 관측

[세션 종료 후]
  agentlens parser → JSONL → SessionDetail 구조화
  → Curator → raw data → knowledge 정제
  → Improver → learnings → skills 개선
  → Dashboard → 인간 리뷰/승인
```

**통합 핵심**: 세션 ID로 조인 — JSONL 파일명의 세션 ID와 `save-session` 마크다운의 세션 ID를 매칭하면 "행동 기록 + 의미적 해석"을 하나로 묶을 수 있음

---

### 데이터 누적과 사후 개선의 연결 문제

현재 구조에서 `save-session` / `learn-eval`이 agentlens에 직접 영향을 미치려면:

| 레이어 | 특성 | 역할 |
|--------|------|------|
| **자동 레이어** (Stop 훅 세션 요약) | 얕지만 전수 커버 | agentlens 입력으로 사용 |
| **수동 레이어** (`/learn-eval` 결과) | 고품질 라벨링 데이터 | 전수가 아닌 샘플링 — Improver의 자동 패턴을 검증 |

> 현실적 문제: 수동 커맨드의 누적 데이터는 불규칙하고 편향됨 (문제 세션에서 더 자주 호출)

---

## 3. 전사 레벨 적용 분석

### 전사 적용에 적합한 것

**A. `/save-session` 패턴 — 세션 핸드오프 구조화**
- 팀 작업 인수인계, 온콜 핸드오프에 즉시 적용 가능
- 포맷 단순, 학습 곡선 없음

**B. Rules 계층**
- 전사 코딩 컨벤션, 보안 정책, 아키텍처 원칙 강제에 최적
- `/etc/claude-code/CLAUDE.md`로 관리자 강제 가능
- git 버전 관리

**C. Verification Loops + pass@k 메트릭**
- CI/CD 통합으로 AI 생성 코드 품질 조직 수준 측정
- 숫자 기반이라 대시보드/리포팅에 바로 활용

---

### 전사 적용에 부적합하거나 주의 필요한 것

**D. Continuous Learning v2 (Background Observer)**

| 리스크 | 설명 |
|--------|------|
| 비용 예측 불가 | N명 × M번 Haiku 호출 |
| 품질 통제 부재 | 잘못된 패턴 전파 가능 |
| 감사 추적 어려움 | 자동 생성 Instinct의 출처 불명확 |
| 보안 위험 | 민감정보가 관측 데이터에 포함될 수 있음 |

> 대안: 개인 opt-in 허용, 팀/조직 skill은 인간 승인 필수

**E. Skill Evolution**
- 자동 롤백 위험, 버전 분기 문제
- 추천: Health metrics는 리포팅만, 비활성화/롤백은 인간 판단

**F. Strategic Compact / PreCompact 마커**
- 개인 작업 흐름 문제, 조직 강제는 과잉

---

### 전사 적용 매트릭스

| 기능 | 전사 | 팀 | 개인 |
|------|------|----|------|
| Rules 계층 (managed policy) | 강력 추천 | O | O |
| save-session 핸드오프 템플릿 | 추천 | O | O |
| Verification + pass@k 메트릭 | 추천 | O | O |
| learn-eval 수동 패턴 추출 | 표준화 가능 | 추천 | O |
| Session persistence (Stop 훅) | 선택적 | O | 추천 |
| Background Observer (v2) | 비추천 | 주의 | O |
| Auto skill evolution | 리포팅만 | 주의 | O |
| Strategic compact | 불필요 | 불필요 | 선택적 |

---

## 4. 현재 레포(claude-workshop)와의 비교

### 현재 레포가 잘 하고 있는 것

- `/spec-plan` + `/impl` 2단계 파이프라인 (4개 병렬 서브에이전트 → 교차 리뷰 → 구현)
- 6개 에이전트 역할 분리 (`analyzer`, `implementer`, `reviewer`, `debugger`, `integrator`, `md-reviewer`)
- 모델 선택 전략 (opus=분석, sonnet=구현)
- Graduation flow 설계 (`notes` → `experiments` → `templates` → `claude-config` → `deploy`)
- Hook 스펙 문서화 (`exit 2` 블로킹, stdin JSON 포맷)

---

### 부족한 영역과 개선 제안

| # | 영역 | 현재 상태 | 개선 제안 |
|---|------|-----------|-----------|
| 1 | **Memory Persistence** | 없음 | `SessionStart`/`Stop` 훅으로 세션 데이터 자동 저장/복원. `/save-session` 커맨드 추가 |
| 2 | **Continuous Learning** | 없음 | `/learn-eval` 스타일 수동 패턴 추출 커맨드부터 시작 |
| 3 | **Verification Loops** | Reviewer 에이전트만 존재 | `eval-harness` 스킬 도입: 구현 전 평가 기준 정의, pass@k 메트릭 |
| 4 | **Parallelization** | `/spec-plan` 4개 서브에이전트 병렬만 | Worktree 오케스트레이션 스크립트 추가 |
| 5 | **Iterative Retrieval** | 서브에이전트가 1회 검색 후 반환 | `DISPATCH→EVALUATE→REFINE→LOOP` 3사이클 패턴 |
| 6 | **Context Budget** | 에이전트 description 크기 비관리 | `context-budget` 감사 스킬 도입 |
| 7 | **Rules 체계** | `CLAUDE.md` 1개만 사용 | `.claude/rules/` 디렉토리 활용, `common`/language별 분리 |
| 8 | **Strategic Compact** | 없음 | `PreCompact` 훅으로 압축 마커 기록 |
| 9 | **templates/ 디렉토리** | 미생성 | Graduation flow의 빈 단계 채우기 |
| 10 | **Skill Evolution** | 없음 | 커맨드/에이전트 실행 결과 추적 |

---

### 우선순위 추천 (구현 난이도 × 임팩트)

| 순위 | 항목 | 난이도 | 임팩트 | 이유 |
|------|------|--------|--------|------|
| 1 | **Rules 체계 정비** | 낮음 | 높음 | `.claude/rules/` 도입만으로 즉시 효과 |
| 2 | **Memory Persistence** | 중간 | 높음 | `session-end` 훅 + `/save-session` |
| 3 | **Verification Loops** | 중간 | 높음 | eval 기준 정의 + grader 패턴 |
| 4 | **Iterative Retrieval** | 낮음 | 중간 | 기존 Explore 에이전트에 루프 추가 |
| 5 | **templates/ 활성화** | 낮음 | 중간 | graduation flow 완성 |

---

## 5. ECC 선택적 적용 가이드

ECC에서 전부를 가져올 필요 없이, 적합하다고 판단된 부분만 선택적으로 적용 가능.

### 즉시 적용 가능 (낮은 난이도)

- **Rules 체계**: `.claude/rules/` 모듈 분리
- **`/save-session` 커맨드**: 세션 핸드오프 구조화
- **`templates/` 활성화**: graduation flow 빈 단계 채우기

### 중기 적용 (중간 난이도)

- **Session persistence**: `Stop` 훅 자동 요약
- **`/learn-eval`**: 수동 패턴 추출
- **Verification Loops**: eval 기준 + grader 패턴 도입

### 보류 / 개인 선택 (높은 난이도 또는 주의 필요)

- **Background Observer (v2)**: 비용/품질 리스크로 전사 비추천 — 개인 실험 수준에서만
- **Auto skill evolution**: 리포팅 외 자동화는 위험 — 수동 게이트 병행 필수
- **Strategic compact**: 개인 수준에서만 유의미, 조직 강제 불필요

---

## 6. 자동 분석 + 인간 승인 모델

### 문제: 수동 호출의 한계

ECC의 `/save-session`과 `/learn-eval`은 수동 호출이라 두 가지 문제가 있다:

1. **누적이 불규칙**: 사용자가 잊으면 데이터가 없음
2. **편향**: 문제가 있었던 세션에서 더 자주 호출 → "나쁜 패턴" 라벨만 쌓이고 "좋은 패턴"은 수집 안 됨

### 제안 모델: 자동 분석 → 대시보드 제안 → 인간 승인

```
세션 종료
   │
   ▼
Stop 훅이 자동으로 세션 분석
   │
   ├─ 세션 요약 자동 생성 (save-session 수준의 깊이를 자동으로)
   │    → "이 세션에서 grep 12회 반복 → iterative retrieval 부재"
   │    → "테스트 실패 3회 후 수동 수정 → verification loop 부재"
   │
   └─ 패턴 후보 자동 추출 (learn-eval 수준의 판단을 자동으로)
        → "제안: 'API 엔드포인트 작업 시 항상 타입 정의부터 확인' — 3개 세션에서 반복 관찰"
        │
        ▼
   agentlens 대시보드의 "Pending Review" 큐에 적재
        │
        ▼
   사용자가 대시보드에서:
     ✅ 승인 → skill/rule로 승격
     ❌ 거부 → 폐기 + 거부 이유 기록 (향후 유사 제안 억제)
     ✏️ 수정 후 승인 → 더 정확한 skill로 승격
```

### 기존 방식과의 비교

```
기존 (ECC):
  자동 수집 (얕음) ──────── 수동 라벨링 (깊지만 편향)
       ↕ 연결 약함

제안 모델:
  자동 수집 + 자동 분석 (깊음) ──→ 대시보드 제안 ──→ 인간 승인/거부
       │                              │
       └─ 전수 커버 (편향 없음)         └─ 고품질 판정 (인간)
```

핵심 차이:
- **기존**: 인간이 "언제 분석할지" + "뭘 추출할지" 둘 다 결정 → 누락 많음
- **제안**: 시스템이 "언제 분석할지" + "뭘 추출할지" 결정 → 인간은 "맞는지 아닌지"만 판단

### "고품질 라벨링"의 의미

**라벨링 = "이게 좋은 패턴인지 나쁜 패턴인지 판정하는 것"**

```
자동 데이터 (Stop 훅):
  "세션 A에서 grep 12회 호출됨"          ← 사실만 있음, 판정 없음
  "세션 B에서 파일 3개 생성됨"           ← 사실만 있음

수동 라벨링 (/learn-eval):
  "grep 12회 반복은 비효율적이다" ✗      ← 인간이 판정을 붙임
  "이 패턴을 skill로 만들어야 한다" ✓    ← 인간이 판정을 붙임
```

"고품질"인 이유: 인간이 맥락을 이해하고 판단했기 때문. LLM 자동 판단보다 신뢰도가 높음.

제안 모델에서는 이 라벨링이 **대시보드 승인/거부 액션**으로 대체된다. 수동 커맨드 호출이 아니라 큐에 올라온 제안에 대한 판정이므로, 누락과 편향이 모두 해소됨.

### 별도 분석기가 필요한가? — 아니다, Improver의 역할이다

agentlens 아키텍처의 기존 에이전트로 충분하다:

```
Collector (non-AI)  →  세션 JSONL 수집/구조화
Curator             →  raw data → 정제된 knowledge (사실 정리)
Improver            →  세션 패턴 분석 → skill/rule 개선 제안 (처방 제안)
```

| 에이전트 | 입력 | 출력 | 성격 |
|----------|------|------|------|
| **Curator** | 세션 데이터, 코드 구조 | "이 프로젝트의 API 구조는 이렇다" | **사실** 정리 |
| **Improver** | 세션 데이터, 패턴 관측 | "이 패턴이 반복되니 이렇게 바꿔라" | **처방** 제안 |

둘 다 같은 세션 데이터를 입력으로 받지만 출력이 다르다:
- Curator가 **knowledge**를 쌓고
- Improver가 **behavior**를 개선한다

여기에 세 번째 "분석기"를 추가하면 Improver와 역할이 겹칠 뿐이다. Improver가 이미 패턴 분석 + 제안 생성 + Pending Review 큐 적재까지의 전체 흐름을 담당하는 것이 올바른 설계.

### agentlens 세션 데이터와 결합 시 완성 구조

```
[데이터 계층]
  Claude Code JSONL (자동)     ──→  agentlens parser  ──→  SessionDetail
  ECC Stop 훅 요약 (자동)      ──→  세션 ID로 조인     ──→  행동 + 해석 통합 레코드

[분석 계층]
  Curator  ←── 통합 레코드 ──→  Improver
     │                            │
     ▼                            ▼
  knowledge/ (사실)          Pending Review 큐 (처방 제안)

[판정 계층]
  대시보드 ←── Pending Review
     │
     ├─ ✅ 승인 → skill/rule 자동 생성
     ├─ ❌ 거부 → 거부 이유 기록 → Improver 학습
     └─ ✏️ 수정 승인 → 정제된 skill/rule
```

이 구조에서:
- ECC의 Hook 기반 실시간 관측(Background Observer v2)은 불필요 — agentlens가 같은 데이터를 더 안전하게 사후 처리
- `/learn-eval`과 `/save-session`의 수동 호출도 불필요 — Improver가 자동 분석, 인간은 대시보드에서 승인만
- 다만 `/save-session`은 "긴급 핸드오프" 용도로 수동 옵션을 남겨두는 것이 유용
