# Spec → Impl → Review 워크플로우 온보딩

> 대상: 이 워크플로우(`/spec-plan` + `/impl` + reviewer 핑퐁)를 처음 써 보는 팀원
> 핵심 메시지: **"AI가 계획·구현·리뷰를 분담하되, 사람이 매 Gate에서 판단을 잠근다"**

---

## 1. 왜 이 워크플로우인가 (의도)

LLM에게 큰 작업을 한 번에 시키면 흔히 발생하는 문제:

1. **요구사항이 굳기 전에 코드가 먼저 써진다** — 잘못된 가정 위에 100줄을 쌓고 나서야 발견.
2. **자기검증의 사각지대** — 같은 컨텍스트에서 구현·테스트·리뷰를 한꺼번에 하면 같은 편향이 그대로 통과.
3. **암묵적 결정이 코드에만 남는다** — "왜 이렇게 했는지"가 사라져 PR 리뷰가 추측 게임이 됨.

이 워크플로우의 설계 의도는 그 셋에 한 가지씩 답하는 것:

| 문제 | 답 | 어떻게 구현되어 있나 |
|---|---|---|
| 가정이 굳기 전 코드 | **계획과 구현을 슬래시 커맨드로 분리** | `/spec-plan` 종료 → 사용자 확인 → `/impl` 시작 |
| 자기검증 편향 | **역할별 서브에이전트 분리** | implementer / reviewer / integrator는 각자 다른 컨텍스트로 호출됨 |
| 사라지는 결정 | **결정·원문·증거를 artifact로 고정** | `plan.md` / `task-N-*.md` / `result.md` / `manifest.yaml` |

요컨대 **흐름은 빠르게, 결정은 명시적으로**.

---

## 2. 전체 흐름

```
/spec-plan {TICKET 또는 자유 프롬프트}
     │
     ├─ Step 0   5개 read-only 에이전트 병렬 (Jira / Spec / Code / Context / Test)
     ├─ Gate 1   Requirements          ← 사용자 OK 없이 통과 불가
     ├─ Gate 2   Plan + Ambiguities    ← 모든 Ambiguity 해소 전 통과 불가
     ├─ Gate 3   Test Strategy         ← 사용자 OK 없이 통과 불가
     ├─ Cross-review (3 rounds max)
     ├─ Final Review (사용자 최종 OK)
     └─ plan.md 저장 → 종료
                  │
                  ▼
/impl {TICKET}
     │
     ├─ plan.md 로드 → task-N-*.md 생성 (자기완결 task 파일)
     ├─ 작업 브랜치 자동 분기 (feat/{TICKET}-{slug})
     ├─ 각 task 순차 실행:
     │     preamble prepend → implementer → reviewer
     │             │              │
     │             │              └─ approved        → 다음 task
     │             │              └─ needs-fix (p1/p2) → 핑퐁 (max 3 round)
     │             └─ orchestrator가 code commit + artifact commit
     ├─ 모든 task 완료 → integrator (integration tests + quality gates)
     └─ 최종 보고 → 사용자 수동 push / PR
```

각 단계가 만드는 산출물:

| 단계 | 결과물 | 위치 |
|---|---|---|
| `/spec-plan` | `plan.md` (`user_prompt` 원문 포함) | `.claude/plans/{TICKET}/plan.md` |
| `/impl` task 생성 | `task-N-{name}.md` | `.claude/tasks/pending/` |
| implementer / reviewer / integrator | `*-result.md` (role별) | `.claude/tasks/done/` (실패는 `failed/`) |
| integrator | `manifest.yaml`, `diff.patch`, `test-output.log` | `.claude/runs/{TICKET}/` |

---

## 3. `/spec-plan` — 계획 모드

> **계획만**. 코드 작성·구현 트리거 일체 금지. 모든 서브에이전트는 read-only.

### 사용법

```
/spec-plan OVDR-1234
/spec-plan OVDR-1234 우리 결제 모듈에 idempotency key를 도입하려고 해
```

호출 시 텍스트가 비어 있으면 `"이 task를 시작하게 된 한 문장을 입력하세요"` 라고 한 번 묻는다 — **이 원문은 `plan.md` frontmatter와 이후 모든 task 파일 상단에 그대로 복사되어 보존된다**. 요약·정제 금지.

### Step 0 — Context Gathering (병렬 5개)

| 에이전트 | 모델 | 역할 |
|---|---|---|
| Jira Agent | sonnet | 티켓 정보 (`jira-tools get`) |
| Spec Agent | sonnet | `docs_path` yaml 또는 PRD/specs/policies 평문 검색 |
| Code Agent | opus | 코드베이스 임팩트 / 의존성 / 리스크 |
| Context Agent | sonnet | `log_repo`의 과거 유사 작업 로그 |
| Test Agent | sonnet | `test-engineer` Strategy 모드 → `<test-plan>` 반환 |

> Project에 `## Implementation Config`가 없으면 Spec / Context Agent는 생략.

### 3-Gate 구조

핵심: **각 Gate마다 사람이 명시적으로 잠근다.** "진행해" 한마디로 OK 처리되지만 침묵은 승인이 아니다.

| Gate | 출력 | 통과 조건 |
|---|---|---|
| 1. Requirements | P0/P1 + Intentional Exclusions (비용/위험/타이밍 근거 필수) + Open Questions | 사용자 "OK" |
| 2. Plan + Ambiguities | Impact Scope + Task Breakdown (XS~XL) + Risks + **Ambiguities** | 모든 Ambiguity에 명시적 결정 |
| 3. Test Strategy | Unit/Integration/E2E + Quality Gates 체크리스트 | 사용자 "OK" |

> **Open Questions vs Ambiguities** (혼동 자주 발생):
> - Open Questions: "구현 중에 결정해도 됨"
> - Ambiguities: "지금 결정 안 하면 task 분해가 무너짐"

> **Shortcut**: `"건너뛰기"` / `"skip gates"` 라고 명시하면 세 Gate를 한 출력으로 합칠 수 있음. 기본은 분리.

### Cross-review (3 rounds max)

충돌 유형 A~D (Code↔Spec, Code↔Tests, Jira↔Code, Test↔Code)를 자동 검출 → 해당 에이전트 재호출. 3회 후에도 미해결이면 Final Review에 양쪽 의견 그대로 노출.

### Final Review

통합 요약 제시. 사용자 선택: `Revise` / `Investigate more` / `OK` / `Cancel`.
OK 시 `plan.md` 저장 후 종료. **자동으로 `/impl`을 트리거하지 않는다** (의도된 분리).

---

## 4. `/impl` — 구현 모드

> 오케스트레이터. **직접 코드를 쓰지 않는다.** 모든 작업은 서브에이전트 위임.

### 사용법

```
/impl OVDR-1234          # plan.md 로드 후 실행
/impl 로그 포맷 통일하고 싶어  # 자유 텍스트 — spec 토론으로 fallback
/impl                    # 무인자 — 무엇을 구현할지 묻는다
```

티켓이 없으면 `LOCAL-{YYYYMMDD-HHMMSS}`가 자동 부여됨.

### 활성화 시 자동 수행

1. `.claude/runs/{TICKET}`, `.claude/tasks/{pending,done,failed}` 생성.
2. **브랜치 정책**: 현재 브랜치가 `master`/`main`/`develop`이면 `feat/{TICKET}-{slug}` 로 자동 분기. dirty면 멈추고 물어봄.

### Task 파일의 5가지 필수 요소

`templates/workflow-contract/task.schema.md` SSOT를 따른다.

1. **자기완결성** — 이전 대화 없이도 implementer가 단독 실행 가능해야.
2. **사용자 원문 복사** — `plan.md`의 `user_prompt`를 그대로 복사.
3. **AC = 실행 가능 bash** — zero exit = pass. 추상 서술 금지.
4. **주의사항은 X-Y 형식** — "X 하지 마라. 이유: Y". 이유 누락이면 무효.
5. **On completion** — result 파일 경로 + `result.schema.md` 링크 명시.

### Implementer → Reviewer 핑퐁

각 task 처리 흐름:

```
preamble(7 rules) + task → implementer (slice-by-slice TDD)
                              │
                              ▼
                         result 파일 작성
                              │
                              ▼
                          reviewer 호출
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
     approved             needs-fix             [p3]/[p4] only
        │              (p1 or p2 있음)               │
        │                     │                     ▼
        │                     ▼            approved + follow-up TODO
        │            implementer 재호출
        │             (p1/p2만 전달)
        │                     │
        │                     ▼ (Round 2/3, max 3)
        │              여전히 미해결 → 사용자 escalate
        ▼
  orchestrator commit (코드 / artifact 2단)
```

**Priority 라우팅 규칙**:

| 코드 | 의미 | 동작 |
|---|---|---|
| `[p1]` | 차단성 (보안/데이터 손실/계약 위반) | 무조건 핑퐁 |
| `[p2]` | 중요 (버그/커버리지/스펙 미스매치) | 사용자가 명시 defer 안 하면 핑퐁 |
| `[p3]` | 사소 (스타일/네이밍) | 비차단 — `<handoff>`에 TODO |
| `[p4]` | nit/제안 | 비차단 |

> 핑퐁 비용을 줄이려고 **p3/p4는 implementer에 전달하지 않는다**. 즉 reviewer가 보이지 않게 무한 nitpick하는 일이 없도록 설계됨.

### Commit 정책 (orchestrator가 통제)

reviewer가 approved 직후, 2단 커밋:

1. **코드 커밋**: task `## Outputs`에 선언된 경로만 `git add`. 와일드카드 금지 (secret 보호).
2. **아티팩트 커밋**: `.claude/tasks/done/task-N-*.md` + `.claude/runs/{TICKET}/`.

자동 push / PR 생성은 **하지 않음** — 사용자가 수동.

### Integrator

모든 task 완료 후 호출. integration test + Quality Gates 평가 + `manifest.yaml` 작성.
**모든 gate가 pass여야 overall status = success.**

### Runner 옵션 (선택)

기본은 `in-session` (현재 Claude 세션의 서브에이전트). 비용/품질 trade-off에 따라:

```
/impl OVDR-1234 --preset cost-optimized
   → implementer만 headless-codex, reviewer/integrator는 in-session
```

per-role 플래그(`--runner-implementer`, `--runner-reviewer`, `--runner-integrator`)로 세밀 조정 가능. 처음에는 **기본값 그대로** 쓰는 걸 권장.

---

## 5. 사람이 개입하는 페이즈 — 체크리스트

> **이 워크플로우는 사람이 게이트를 지키지 않으면 가치가 절반으로 떨어진다.** 어느 페이즈에서 무엇을 확인해야 하는지 미리 알아두기.

### `/spec-plan` Gate 1 (Requirements) — **가장 중요**

확인할 것:

- [ ] **P0와 P1의 경계가 합리적인가?** "전부 P0"이라는 결과가 나오면 의심.
- [ ] **Intentional Exclusions의 이유가 동어반복은 아닌가?** "우선순위 낮음", "out of scope"는 무효 — 비용/위험/타이밍 중 하나로 명시.
- [ ] **누락된 P0**이 없는가? 도메인을 가장 잘 아는 사람이 마지막 안전망.
- [ ] **Open Questions**가 정말 구현 중 결정 가능한가? 아니면 Ambiguities로 옮겨야 하나?

피드백 패턴:
- `"수정"` — 같은 Gate 내에서 다시 작성
- `"P0의 X를 Intentional Exclusions로"` — 재분류
- `"OK"` — 다음 Gate

### `/spec-plan` Gate 2 (Plan + Ambiguities)

확인할 것:

- [ ] **Task 사이즈**가 합리적인가? 모두 XL이면 분해 부족, 모두 XS면 over-decomposition.
- [ ] **의존성 순서**가 정확한가? task N이 task N-1의 산출물을 쓰는가?
- [ ] **Ambiguities를 모두 결정했는가?** 미결 항목 있으면 절대 Gate 3로 진행 금지.
- [ ] **Impact Scope의 파일 리스트**가 실제로 만질 영역과 일치하는가? 누락된 파일이 있으면 reviewer 단계에서 "선언 외 파일 수정" 경고로 시간 낭비.

### `/spec-plan` Gate 3 (Test Strategy)

확인할 것:

- [ ] **Risk areas**가 실제 위험과 매칭되는가?
- [ ] **Quality Gates** 체크리스트가 명확히 측정 가능한가? ("잘 동작" X, "테스트 통과" O)
- [ ] **수동 테스트가 필요한 부분**은 별도로 메모해 두기 — integrator도 자동 테스트만 본다.

### `/spec-plan` Final Review

- [ ] **전체 그림에서 모순**이 없는가? Cross-review가 잡지 못한 게 있을 수 있음.
- [ ] `plan.md`의 `user_prompt`가 **실제 의도와 일치**하는가? (이후 모든 task가 이걸 인용함)

### `/impl` 중 — task별 reviewer 결과

reviewer가 매번 결과를 보고함. 다음 케이스에 사람이 개입:

| 상황 | 행동 |
|---|---|
| `[p1]` 3 round 끝에도 남음 | 컨텍스트 부족·스펙 누락 가능성. plan.md로 돌아가 update. |
| `[p2]` 인데 deferrable | `"p2 X는 defer"` 명시 — `<decisions>`에 `deferred: ...` 기록됨 |
| `[p3]`/`[p4]` 흥미로움 | follow-up TODO로 충분, 굳이 즉시 고치지 않음 |
| reviewer가 Chesterton's Fence로 질문함 | 코드가 왜 그 자리에 있는지 사람만 아는 경우 — 답변 필수 |

### `/impl` 중 — task 실패 시

`failed/`로 이동된 result 파일을 직접 읽고:

- [ ] **AC가 실현 불가능했나?** → task 파일 수정 후 `pending/`으로 되돌리기
- [ ] **외부 의존성 문제인가?** → 환경 문제는 워크플로우 밖에서 해결
- [ ] **plan.md의 가정이 틀렸나?** → 가장 흔한 케이스. `/spec-plan`으로 돌아가 update (plan-v2.md 생성됨)

### Integrator 보고 직후 (수동 확인)

- [ ] Quality Gates **모든 항목**이 실제로 통과했는가? (gate 평가는 LLM이 함 — 확인 권장)
- [ ] `manifest.yaml`의 runner / model 필드로 **이번 run이 어떤 조합으로 실행되었는지** 확인 (사후 비용 비교용)
- [ ] **수동 테스트** (UI, 외부 시스템) 직접 수행
- [ ] **PR 생성 전 diff 한번 더 훑기** — orchestrator가 자동 push하지 않으므로 마지막 확인 기회

### PR 단계

- [ ] PR 본문에 `plan.md` 링크와 ticket 명시
- [ ] reviewer가 남긴 `<handoff>` follow-up TODO를 issue로 옮기거나 PR description에 명시

---

## 6. 자주 묻는 질문 (FAQ)

**Q. `/spec-plan` 없이 바로 `/impl` 써도 되나?**
A. 가능 (자유 텍스트 모드). 단 task 분해 품질이 떨어지고 reviewer 핑퐁이 늘어남. **첫 도입 1~2주는 무조건 `/spec-plan` 거치는 걸 권장**.

**Q. plan을 수정하고 싶다.**
A. `/spec-plan {TICKET}` 다시 호출하면 `plan-v2.md`로 저장됨. 활성 revision은 `manifest.yaml`에 기록.

**Q. reviewer가 너무 깐깐하다.**
A. p1/p2가 진짜로 필요한지 case-by-case 판단. `[p2] X는 defer` 라고 명시하면 통과. 패턴이 반복되면 `claude-config/agents/reviewer.md`의 priority 정의를 팀 컨벤션에 맞게 조정.

**Q. 어떤 작업에 안 맞는가?**
- **단순 hot-fix / 1-line 변경** — overhead가 더 큼. 그냥 수정 후 commit.
- **탐색적 디버깅** — `/impl`의 `analyzer` / `debugger` 경로를 쓰거나, 그냥 일반 대화로.
- **UI 폴리싱 / 디자인 iteration** — visual 피드백 루프가 우선. `/spec-plan` overkill.

**Q. `templates/workflow-contract/` 파일들은 뭔가?**
A. 모든 artifact 형식의 SSOT. 새 runner를 추가해도 이 contract만 따르면 동일한 audit이 가능. `contract.md`부터 읽으면 됨.

---

## 7. 핵심 파일 빠른 참조

| 파일 | 역할 |
|---|---|
| `claude-config/commands/spec-plan.md` | `/spec-plan` 정의 |
| `claude-config/commands/impl.md` | `/impl` 정의 (orchestrator) |
| `claude-config/agents/implementer.md` | 구현 에이전트 |
| `claude-config/agents/reviewer.md` | 리뷰 에이전트 (5 axes + priority) |
| `claude-config/agents/integrator.md` | integration test + gate 평가 |
| `templates/workflow-contract/contract.md` | artifact 계약 SSOT |
| `templates/workflow-contract/preamble.md` | 매 task 앞에 prepend되는 7 rules |
| `templates/workflow-contract/task.schema.md` | task 파일 형식 |
| `templates/workflow-contract/result.schema.md` | result 파일 형식 |
| `notes/impl-workflow/design.md` | 살아있는 설계 문서 (변경 의도는 plan.md로) |

배포 흐름: `claude-config/` 편집 → `./deploy.sh` → `~/.claude/`에 적용.

---

## 8. 첫 사용 시 권장 시나리오

처음 워크플로우를 시험해 본다면:

1. **작은 티켓** (XS~M 한 개) 으로 시작. 거대 epic은 피하기.
2. `/spec-plan {TICKET}` 호출 → **3 Gate 모두 분리해서** 경험.
3. 각 Gate에서 일부러 `"수정"` 한 번씩 해 보며 피드백 루프 체감.
4. `/impl {TICKET}` → 첫 task에서 reviewer 핑퐁을 한 번 보기 (의도적으로 작은 결함을 두는 것도 학습 효과).
5. 끝나면 `.claude/runs/{TICKET}/manifest.yaml`과 `plan.md`, task/result 파일들을 천천히 다시 읽기 — **artifact가 어떻게 결정의 추적 가능성을 만드는지** 가 이 워크플로우의 진짜 가치.

문제 발견 / 개선 아이디어는 `notes/impl-workflow/future-ideas.md`에 기록해 두면 다음 iteration에 반영.
