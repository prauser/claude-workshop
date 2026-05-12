# Codex `/goal` 분석과 Type B 워크플로 정합성 검토

> 작성: 2026-05-13
> 맥락: `spec-plan` + `impl` 위에 자율 실행 레이어를 얹는 방안 논의 중, codex 의 `/goal`
> 명령이 자율 워크플로의 reference 로 거론되어 실제 메커니즘과 적용 한계를 정리.

## 1. `/goal` 의 실체 — 무엇을 하는 명령인가

### 1.1 한 줄 정의
Thread 당 1개의 `(objective, verifiable stopping condition, token budget?)` 을 SQLite 에
영속화해 두고, 에이전트가 plan → act → test → review → iterate 사이클을 사용자 입력 없이
계속 돌게 해주는 **런타임 continuation primitive**.

### 1.2 모델이 쓰는 tool 3종

| Tool | 동작 | 비고 |
|---|---|---|
| `create_goal(objective, token_budget?)` | 새 goal 생성 | 이미 존재 시 실패 |
| `update_goal(status="complete")` | goal 완료 처리 | **complete 로만 호출 가능** |
| `get_goal()` | 현재 goal 조회 | null 반환 가능 |

`pause` / `resume` / `budget_limited` 전이는 모델이 못 한다. 모델의 권한은
**시작과 종료** 만.

### 1.3 영속화 — `thread_goals` 테이블

```
status         : active | paused | budget_limited | complete
token_budget   : optional
tokens_used    : 누적 카운터
time_used_sec  : 누적 카운터
goal_id        : UUID (재생성 시 회전 → stale 회계 방지)
```

세션·리부팅·TUI 종료에도 살아남음. 사용자가 며칠 뒤 다시 들어와도 같은 goal 상태에서 재개.

### 1.4 State machine (비대칭 전이)

| 전이 | 누가 트리거 |
|---|---|
| `active → paused` | 사용자 인터럽트 / 시스템 abort |
| `paused → active` | thread resume |
| `active → budget_limited` | 런타임 회계가 token_budget 초과 감지 |
| `* → complete` | 모델 (`update_goal`) |

**비대칭이 핵심**: 모델은 자기 자신을 pause 못 함. 자가-부활 루프 차단.

### 1.5 명시된 guardrail

- `create_goal` 사양: *"Create a goal only when explicitly requested by the user or
  system/developer instructions; do not infer goals from ordinary tasks."*
- zero-tool-call turn 다음의 auto-continuation 억제 → 무한 루프 방지
- 완료 시 `completion_budget_report` 가 응답에 포함 → 모델이 자연스럽게 비용 보고

### 1.6 사용자가 제공해야 하는 것
- **Objective** — 무엇을 달성할지
- **Verifiable stopping condition** — exit code, 점수, visual diff 등 *측정 가능한* 종료 조건
- 참조 자료 (PLAN.md, 이슈, docs, 로그)
- 진척 측정용 command / artifact
- (선택) token_budget

> "Codex should know what 'done' means before it starts." — 공식 문서. *done* 의 정의는
> 사람이 만들어 줘야 한다.

## 2. 공식·실사례에서 어떤 용도로 쓰이나

### 2.1 OpenAI 가 명시한 적합 카테고리 3종

| 카테고리 | 전형적 objective | 전형적 stopping |
|---|---|---|
| **Migration** | "이 프로젝트를 stack X → Y 로 마이그레이션" | 모든 테스트 green + Playwright visual parity |
| **Prototype 생성** | "PLAN.md 따라 게임/툴 만들기" | milestone 별 테스트 + 인터랙티브 검증 |
| **Prompt / Eval 최적화** | "eval 점수 X 이상까지 prompt 개선" | 수치 임계 도달 |

명시된 부적합: **"loose list of unrelated work"** — 서로 무관한 잡일 묶음.

### 2.2 실사용 사례 (3rd party 보고)

- Andrew Chen — Mac eGPU/device driver 14시간 연속 자율 진행
- Alex Finn — extraction shooter 게임 1시간+, 이미지 생성까지 자율 (asset 포함)
- 사용자 보고: "며칠 동안 멈추지 않고 일함"

### 2.3 사례들의 공통 속성

모두 **자동화 가능한 oracle** 을 가진 작업.
- 마이그레이션 = 기존 동작 = 정답
- 게임 = "실행되고 플레이 가능" 자체가 정답
- Eval = 수치 점수

조직 합의·이해관계자 사인오프가 끼지 않는다.

## 3. 우리가 이해한 적용 영역 — 두 버킷

`/goal` 의 적합 조건의 본질은 한 줄: **automatable oracle + 합의 불필요**.
이 조건이 발현되는 모습이 두 가지.

### 3.1 버킷 A — 좁은 영역 grind
- 마이그레이션, perf 최적화, refactor, eval 튜닝
- 좁아서 정답 = 측정 가능
- 좁아서 *결정해야 할 게 없음* — 그냥 수렴시키는 일

### 3.2 버킷 B — 1인/소규모 풀 자율
- 사이드 프로젝트, 개인 prototype, 소규모 신규 레포
- 산출물 자체가 정답 (실행됨/안됨)
- 이해관계자 = 본인 1명, self-consensus

### 3.3 안 맞는 영역
- 다이해관계자 합의 필요 작업
- 보안/법무/PM 사인오프가 oracle 의 일부인 작업
- 출시 후 D+N 메트릭으로만 평가 가능한 작업
- 대규모 운영 코드베이스 — 변경의 blast radius 가 큰 곳

## 4. 우리 레포에서 흉내 내려면 — 필요한 빌딩블록

`/goal` 의 4가지 핵심 기능을 분해하면 각각 우리 레포의 어떤 자산으로 매핑 가능한지가
보인다.

| `/goal` 기능 | 매핑 / 신설 필요 |
|---|---|
| objective + verifiable stopping condition | `goal.md` 신설 — `acceptance:` 와 `stopping:` 분리, 후자는 실행 가능 bash·점수·diff 만 허용 |
| token budget + budget_limited 전이 | `.claude/runs/{TICKET}/manifest.yaml` 에 누적 카운터 + 캡, 초과 시 자동 stop |
| SQLite 영속성 + pause/resume | 파일 기반 manifest + 명시적 resume 명령 |
| auto-continuation 루프 | `spec-plan` → `impl` 사이의 surrogate 자동 진행, zero-tool-call 감지 시 정지 |

### 4.1 신설해야 할 것 (최소 셋)

1. **`/goal-draft` (협업 모드)** — 사용자와 함께 objective + verifiable stopping +
   참조자료 + budget 을 채우는 슬래시 커맨드. PRD 가 아님 (자율 작성 안 함).
2. **`/autopilot {goal.md}`** — `spec-plan` + `impl` 를 surrogate 로 감싸 연쇄 실행하는
   오케스트레이터. 휴먼 게이트를 정책으로 대체.
3. **`policy-resolver` / `scope-guardian` / `goal-verifier` 에이전트**
   - `policy-resolver`: 휴먼 게이트 자리에서 goal.md 기반 결정
   - `scope-guardian`: 매 단계 산출이 goal.md scope 밖으로 부풀었는지 검사
   - `goal-verifier`: stopping condition 충족 여부 의미 검증 (단순 테스트 통과를 넘어
     "정말 goal 달성됐는가")

### 4.2 두 가지 codex 교훈 (구현에 반영)

1. **Verifiable stopping 을 일급 시민으로** — 우리 `spec-plan` 의 Quality Gates 는
   체크리스트형이라 "verifiable" 강제가 약함. `goal.md` 의 `stopping:` 은 반드시 실행
   가능 검증으로만 받게 스키마 박기.
2. **State transition 비대칭 강제** — surrogate 가 자기 자신을 pause/resume 하지
   못하게. 그렇지 않으면 자율 에이전트가 자기 자신을 pause 했다 resume 하는 자가-부활
   루프 발생 가능.

### 4.3 안 만들 것 (의도적 제외)

- **PRD 자율 작성** — codex 도 안 함. 자율로 hallucinated requirements 가 plan → impl
  까지 흘러가면 "정교하게 만들어진 잘못된 제품" 산출.
- **`/goal` 의 fullscale 모방** — SQLite·feature flag 등 codex 의 인프라 디테일까지
  복제할 필요 없음. 파일 기반으로 충분.

## 5. Type B — `/goal` 과 별개로 필요한 영역

대규모 운영 코드베이스의 feature 개발 (Type B) 은 `/goal` 의 설계 의도와 *구조적으로*
mismatch. 별도 워크플로 필요.

### 5.1 Type B 의 정의 — 4축 모두 right

| 축 | Type A (= `/goal` 가능) | Type B (= 별도 워크플로 필요) |
|---|---|---|
| Oracle | 자동화 가능 (테스트, 점수, diff) | 사람 판단 일부 (보안 리뷰, PM 사인오프, D+N 메트릭) |
| Objective | 단일 coherent | 여러 ticket 으로 갈라짐 |
| 이해관계자 | 1인 또는 소팀 | 다부서·다팀·법무·디자인 |
| 코드베이스 | 신규/소규모 — 실패 비용 저렴 | 운영 중 대규모 — blast radius 큼 |

### 5.2 `spec-plan` + `impl` 이 채우는 영역과 빈 영역

현 워크플로의 커버리지: **티켓 1개를 안전하게 분해·구현**.
빈 영역: 위 (upstream), 옆 (coexisting), 아래 (downstream).

#### Upstream — 티켓이 만들어지기 전

| 추가 단계 | 푸는 문제 |
|---|---|
| `/prd` (협업) | problem framing, user, success metric, scope 합의 |
| Alternative exploration | "안 만들기 / 기성품 / 재사용" 검토 |
| Pre-mortem (비-코드) | 법무·보안·운영·재무 위험 |
| Success metric 설계 | D+N retention, conversion 등 *출시 후* 측정 기준 |
| Cross-team impact 스캔 | 다른 레포 caller, 공유 schema/OpenAPI/protobuf |

#### Coexisting — `spec-plan` / `impl` 진행 중 빠진 것

| 추가 단계 | 푸는 문제 |
|---|---|
| ADR 자동 생성 | Gate 2 Ambiguities 결정 = ADR 후보. 지금은 plan.md 안에 묻혀 사라짐 |
| Stakeholder sign-off trail | 누가 무엇을 언제 승인했는지 감사 |
| Cost tracking | task 별 시간·토큰·라운드 수 누적 |
| Security review hook | 민감 영역 감지 시 강제 호출 |
| Contract/schema diff alarm | public surface 변경이 plan.md 미선언 시 escalate |

#### Downstream — `impl` 끝났는데 *제품으로서* 안 끝난 것

| 추가 단계 | 푸는 문제 |
|---|---|
| `/launch` | feature flag, % rollout, rollback 조건 — 머지 ≠ 출시 |
| Operational readiness gate | 모니터링·알람·runbook·on-call 인지 검증 |
| Documentation propagation | README / API docs / 내부 위키 / release note 자동 업데이트 |
| Post-ship verifier | 출시 후 D+N 메트릭 측정 → PRD acceptance 비교, drift 감지 |
| Deprecation/migration plan | 대체되는 이전 경로 제거 일정 |
| Incident loop-back | 사고 발생 시 plan.md Risk 와 매핑 → 다음 spec-plan 학습 |

### 5.3 우선순위 (Type B 한정)

전부 만들지 말고 ROI 순:

1. `/launch` + Operational readiness gate — 즉각 통증 가장 큼
2. ADR 자동 생성 — 데이터 있음, 비용 0
3. Cross-team impact 스캔 — 대규모 환경 사고 예방
4. `/prd` + Success metric → Post-ship verifier 의 closed loop
5. 나머지 (Alt exploration, Pre-mortem, Sign-off trail, Incident loop-back) — 조직 규모
   커질 때

## 6. Size × Risk classifier — Type B 내부 적응성

Type B 안에서도 ticket 크기·위험에 따라 위 add-on 들의 필요 정도가 다르다. 매번 다
강제하면 무겁고, 매번 생략하면 사고. → 분류 단계 필요.

### 6.1 두 축

**Size**

| | 전형 | 필요한 spine |
|---|---|---|
| XS | 오타, copy 수정 | `impl` 만 |
| S | 단일 파일 버그 | `impl` 만 |
| M | 한 모듈 안 기능 | `spec-plan` + `impl` (현 디폴트) |
| L | 모듈 횡단, 신규 endpoint | + downstream 일부 |
| XL | 신규 subsystem, 외부 연동 | PRD + spec-plan × N + 전 downstream |
| XXL | epic — 분해 필요 | 워크플로 X, 분해 먼저 |

**Risk surface** (size 와 독립)

| 건드리는 영역 | 강제 단계 |
|---|---|
| auth / authz | security review |
| PII / 사용자 데이터 | privacy review, 로그 마스킹 |
| 결제·금융 | compliance, 이중 리뷰, rollback rehearsal |
| public API / 외부 contract | contract diff alarm, doc propagation, deprecation |
| DB schema, event payload | migration plan, 호환성 매트릭스 |
| 공유 인프라 (CI/build/deploy) | cross-team notification |
| 성능-민감 경로 | perf budget + 회귀 벤치마크 |
| UX 변경 | feature flag, A/B, 시각 회귀 |

### 6.2 운영 방법

- **`spec-plan` Step 0 끝의 1분 단계**로 분류
- 3 질문이면 80% 해결:
  1. 파일/모듈 수 — size
  2. public surface (API/schema/UX/보안) 변하나? — risk
  3. 머지 후 통보 대상 — launch/comm 비용
- 산출은 plan.md frontmatter 라벨 2개: `size: M`, `risk: [auth, contract]`
- 라벨에 따라 plan.md 템플릿이 섹션을 *추가* 또는 *생략*
- 사용자가 라벨 수정 가능 (오분류 보호)
- **자동 결정 ≠ 자동 강제**. classifier 가 잘못 판단했을 때 안전판 필요

### 6.3 size 단축회로

- XS/S → `spec-plan` 의 3 Gate 디폴트로 단일 Gate 압축 (기존 "건너뛰기" 옵션 자동 트리거)
- XL → `/prd` 선행 강제. XL 인 채로 `spec-plan` 들어오는 걸 reject

## 7. Type B 와 `/goal` 의 관계 — 분리되지만 합성 가능

### 7.1 전체 차원 — 정합 안 함

Type B 의 워크플로 전체를 `/goal` 위에 얹는 건 **도구 오용**. 이유:
- `/goal` 의 stopping condition 에 "PM 사인오프", "보안 리뷰 통과", "D+30 메트릭" 같은
  것 못 박음
- 다이해관계자 합의는 surrogate 로 흉내 내봤자 진짜 합의가 안 됨
- 운영 코드베이스 변경의 blast radius 를 `/goal` 의 단순 stop 조건이 못 다룸

### 7.2 sub-task 차원 — 자연스러운 합성

Type B 안의 *grind 모양 sub-task* 는 `/goal`-적합. 큰 그림은 Type B 워크플로가 짊어지고,
sub-task 하나를 `/goal` 로 위임하는 형태.

| Type B 안 sub-task 예시 | `/goal` 적용 |
|---|---|
| 모든 caller 를 oldAPI → newAPI 로 마이그레이션 | objective: migration / stopping: grep 결과 0 + 테스트 green |
| 이 모듈 커버리지 80% 까지 백필 | stopping: 임계 도달 |
| 이 함수 p99 50ms 까지 최적화 | stopping: 벤치마크 통과 |
| shadcn → 신규 디자인 시스템 시각 parity | stopping: Playwright visual diff = 0 |

### 7.3 그림

```
[XL] PRD → 다수 ticket
   ├─ [L] ticket  → spec-plan → impl → /launch → readiness → post-ship verify
   │     └─ 그 안의 migration/refactor/perf sub-task → /goal 자율
   ├─ [M] ticket  → spec-plan(축약) → impl → 머지
   │     └─ 비-grind 종류면 /goal 안 씀
   └─ [XS] ticket → impl 만
```

Classifier 의 진짜 가치는 size 라벨 자체가 아니라 **"이 ticket 안에 `/goal`-적합 grind
가 있는가, 어디에?"** 를 식별하는 것. 그게 자율화 ROI 가장 높은 지점.

## 8. 결론

1. `/goal` 은 **PRD 작성 도구가 아니다**. continuation primitive + 영속화 + budget 가드.
2. 적합 조건은 "automatable oracle + 합의 불필요". 두 발현 형태 (좁은 grind / 1인 풀
   자율) 가 같은 본질.
3. 우리 레포에서 흉내 내려면 `goal.md` 스키마, surrogate 3종, manifest 의 budget/state
   필드면 충분. PRD 자율 작성은 시도하지 않는다.
4. Type B 는 `/goal` 과 **워크플로 차원에서 분리**. 별도로 `/prd` + `/launch` + ops
   readiness + post-ship verifier + ADR/security/cross-team add-on 이 필요.
5. Type B 안의 sub-task 차원에서는 `/goal` 과 **자연스럽게 합성**. Size × Risk
   classifier 가 어디서 합성할지를 결정.
6. 우선 만들 순서:
   1. Size × Risk classifier (`spec-plan` 안에 1분 단계로)
   2. `/launch` + Operational readiness gate (Type B 의 가장 큰 펑크 지점)
   3. `/goal-draft` + `/autopilot` (Type A 시나리오 + Type B sub-task 용)
   4. `/prd` (조직 합의 필요해질 때)
   5. Post-ship verifier (closed loop)

## Sources

- [Follow a goal | Codex use cases](https://developers.openai.com/codex/use-cases/follow-goals)
- [Slash commands in Codex CLI](https://developers.openai.com/codex/cli/slash-commands)
- [Codex Best Practices](https://developers.openai.com/codex/learn/best-practices)
- [Codex /goal Ralph Loop 14-hour autonomous task — MindStudio](https://www.mindstudio.ai/blog/codex-goal-ralph-loop-14-hour-autonomous-task)
- [How OpenAI Codex implements /goal — patleeman gist](https://gist.github.com/patleeman/b1b5768393f9bf2f60865b1defeeb819)
- [Document the /goal CLI command — openai/codex issue #20536](https://github.com/openai/codex/issues/20536)
