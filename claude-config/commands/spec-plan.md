# Spec Plan Mode

Planning only. Never write code or trigger implementation. All subagents are read-only.

**Usage**: `/spec-plan {TICKET} [--no-self-pass] [--grill]`

## Template path resolution

본 prompt 와 sub-agent 는 `templates/workflow-contract/...` 의 SSOT 파일을 인용한다.
**resolution 규칙 (in-project `.claude` 우선 → cwd → `~/.claude` 폴백)**:
다음 순서로 처음 존재하는 파일을 사용한다 —
1. `.claude/templates/workflow-contract/{file}` — 소비 프로젝트에 vendored 된 경우 (`sync-workflow.sh` 배포)
2. `./templates/workflow-contract/{file}` — 워크플로우 레포 안에서 직접 실행
3. `~/.claude/templates/workflow-contract/{file}` — user-level `deploy.sh` 배포
셋 다 없으면 "`sync-workflow.sh` 또는 `./deploy.sh` 미실행 가능성" 경고 후 진행 중단.

이 규칙은 in-session orchestrator / implementer / reviewer / integrator / 헤드리스 러너 모두 동일.

적용 대상: `grill.md` (Pre-search grill · Gate 0 · Gate 2 sequential 엔진 SSOT), `gate-escalation.md` (Gate 2 stuck · SKIP · Spec Preview miss 조건부 기계장치 SSOT), `preamble.md` (§9 텍스트 instruction · §8 위험영역 SSOT), 그 외 본 파일이 `templates/workflow-contract/` 경로로 인용하는 모든 SSOT 파일.

## On activation

1. Parse ticket ID from arguments.
2. Read `## Implementation Config` from CLAUDE.md → get `specs_path`, `prd_path`, `policies_path`, `log_repo`, `glossary_path`.
   - No config: skip Spec Agent and Context Agent, run Jira + Code only.
3. Capture `user_prompt`: the exact natural-language text the user typed when invoking `/spec-plan`, **verbatim — 의례적 입력("진행해줘"/"go"/빈 값)도 그대로 기록**. 요약·의역 금지. 이 필드는 감사 앵커이며, *substantive 할 때만* Step 0 검색 잠금의 키워드 원천이다 (§intent.problem 출처 우선순위 참조).
   - **Mode 판정**: user_prompt가 문제를 담은 substantive 텍스트면 **Mode A**(free-text 주도), 티켓 ID + 의례적 텍스트뿐이면 **Mode B**(티켓 주도).
   - **즉시 1회 질문하지 않는다**: 원문이 비거나 의례적이어도 티켓이 문제를 담고 있을 수 있으므로(Mode B), 여기서 한 줄을 강요하지 않는다. 문제 한 줄의 출처는 Jira Agent 반환 후 §intent.problem 출처 우선순위에서 확정한다.
4. **Readiness Check** — 입력(티켓 / `user_prompt` / PRD) 을 3등급 분류로 진단해 짧은 박스 리포트를 출력. Step 0 진입 *전에* 빵꾸를 발견하는 단계.

   | 등급 | 기준 | 라우팅 |
   |---|---|---|
   | ✅ **필수(must-have)** | 무엇을 해달라는지 — 문제 / 요청. 없으면 시작 불가 | 빠짐 → (a) 갭이 **검색불가 수준**이면 → Pre-search grill(멀티턴 wave)로 라우팅; (b) 갭이 한 줄 보강으로 해소 가능하면 → 사용자에게 한 줄 추가 입력 요청, 응답 전까지 정지 |
   | ⚠️ **산출예정(will-produce)** | 상세 방향성 · 세부 AC. 없어도 정상, spec-plan 이 만들 것 | "이건 우리가 정함" 표시만 |
   | ❓ **이상(odd)** | 설명↔AC 모순, 방향성이 컨벤션과 충돌, 범위가 appetite 대비 과도 | 즉시 사람에게 플래그 |

   출력 형식:
   ```
   ┌─ 준비도 점검 · {TICKET} ──────────────────────
   │ ✅ 문제 정의      {요약 또는 "티켓에 있음"}
   │ ⚠️ 해결 방향성    {명시 안 됨 → Gate 2 에서 결정 / 또는 명시되어 있음}
   │ ✅ 성공 기준(AC)  {N건 있음 또는 없음}
   │ ❓ 이상           {모순 / 컨벤션 충돌 / 과도 — 또는 "없음"}
   └──────────────────────────────────────────────
   ```

   **Mode B 단축**: user_prompt가 의례적이어도 티켓이 문제를 담을 수 있으므로, '필수 빠짐'을 단정하기 전에 Jira Agent의 티켓 본문을 우선 신뢰한다 — Readiness Check 시점엔 `문제 정의`를 `티켓에 있음`(약속어음)으로 통과시키고 §intent.problem 출처 우선순위 finalization point에서 실제 확인. **티켓에도 없을 때만** 아래 갭 판정을 적용한다.

   필수 빠짐 → 갭 수준 판정: **검색불가 수준**(예: 도메인·기능·범위가 모두 불명확)이면 Pre-search grill로 라우팅(아래 §Pre-search grill 참조). **한 줄 보강으로 해소 가능한 수준**이면 한 줄 입력 요청 후 응답을 `user_prompt`에 verbatim 보강. 이상 → 사용자 응답을 기다리되 플래그를 `readiness_flags:` 에 구조체로 기록:

   ```yaml
   readiness_flags:
     - flag: <kebab-id>          # 이상 종류 (예: cache-location-undetermined, ac-mismatch, scope-too-broad)
       detail: "<한 줄 설명>"
       resolution: "<gap이 저장 전에 닫혔으면 그 메모; 미해결 진행이면 빈 값(= 우회 신호)>"   # 진단형/터미널형 공통 의미
       ts: <ISO 8601>
   ```

   resolution 이 비어 있는 채로 진행한 비율은 우회 측정 지표. 사용자가 "그냥 진행" 답하면 resolution 생략하고 plan 계속.

5. **GLOSSARY read** — CLAUDE.md `## Implementation Config` 의 `glossary_path:` 가 있으면 해당 파일을 읽고, 본 plan 세션 동안 §Authoring §9 우선순위 1번 (GLOSSARY hit) 에 사용한다.
   - 없거나 파일이 존재하지 않으면 step 진행 (silent skip). 단, 첫 Gate 출력 시 한 줄 `GLOSSARY: 미설정` 로 표시.

6. **flag 파싱** — 두 개의 opt flag을 파싱한다. 본 세션 동안 유지.
   - `--no-self-pass`: opt-out flag. 있으면 `self_pass = OFF`, 없으면 `self_pass = ON` (기본값 ON).
   - `--grill`: opt-in flag. 있으면 `grill_flag = ON`, 없으면 `grill_flag = OFF` (**기본값 OFF** — 명시하지 않으면 Pre-search grill을 수동으로 발동하지 않는다).

7. **idiom-pool 임계 알림** — `~/.claude/idiom-pool.yaml` 이 있으면 읽어 임계(term별 count ≥ 3) 이상이고 `status: open` 인 entries 가 있는지 확인. 있으면 첫 출력 직전 한 줄 알림:
   `idiom-pool: N건 임계 (예: stale ×5, idempotent ×4). \`/idiom-review\` 권장.`
   - 알림은 *정보성* — 자동 트리거 X (사용자가 명시 호출해야 실행됨).
   - 파일 없음 또는 임계 항목 없음 → 조용히 skip.

## intent.problem 출처 우선순위 (Mode A/B)

`intent.problem`("문제 한 줄")의 출처는 호출 모드에 따라 다르다. 다음 우선순위로 **Jira Agent 반환 직후, Gate 0 진입 전**에 확정한다 (= finalization point).

1. **substantive `user_prompt`** (Mode A) → 그것을 충실히 요약해 intent.problem 으로 (user_prompt 원문은 덮어쓰지 않음 — 아래 verbatim 잠금 참조).
2. **티켓 description / AC** (Mode B) → user_prompt가 의례적이면 Jira Agent가 가져온 티켓 본문을 충실히 요약해 intent.problem 으로.
3. **둘 다 없음** → 1회 질문: "문제 정의가 티켓·원문 어디에도 없습니다 — 이 task를 시작하게 된 한 문장을 입력하세요." 응답을 `user_prompt`에 verbatim 보강 후 1번으로.

- **`user_prompt` verbatim 잠금 유지**: 출처가 티켓이어도 user_prompt 원문은 절대 덮어쓰지 않는다(감사 앵커).
- **검색 잠금 정합**: Step 0 검색 키워드도 같은 우선순위 — substantive user_prompt 없으면(Mode B) 티켓 키워드로 잠근다. `refined_user_prompt`가 있으면 그것이 최우선(기존 규칙 유지).
- **Readiness Check 시점 한계**: Readiness Check(step 4)는 Jira Agent *전*에 돈다. 따라서 Mode B에서 "문제 정의"는 그 시점엔 `티켓에 있음`(미확정 약속어음)으로 두고, 위 finalization point에서 실제 한 줄로 굳힌다.

## Pre-search grill (Step 0 이전 — prompt 정련)

> **실행 위치**: Readiness Check 완료 직후, Step 0 진입 직전.

### 트리거 조건 (OR — 둘 중 하나라도 해당하면 실행)

| 트리거 | 조건 |
|---|---|
| **자동** | Readiness Check의 "필수 빠짐" 등급 판정에서 갭이 **검색불가 수준**으로 라우팅된 경우 (별도 2차 모호도 판정 신설 금지 — Readiness Check 판정 재사용) |
| **수동** | 사용자가 `--grill` 플래그를 명시한 경우 (`grill_flag = ON`). `--grill` 기본값은 OFF(opt-in) — 명시하지 않으면 수동 트리거 발동 안 함 |

### 실행 규칙

grill 엔진을 `refine` mode로 호출한다 (SSOT: `templates/workflow-contract/grill.md` §2.2, §4):

```
grill(
  mode:   refine
  seed:   <user_prompt>
  cap:    3  (웨이브당 1~2질문, 정렬 달성 시 캡 소진 전 자연종료)
  output: refined_user_prompt
)
→ 수렴 시: refined_user_prompt 반환 (user_prompt 원문은 변경하지 않고 verbatim 유지)
→ 미수렴(3웨이브 후 미완):
    readiness_flags += {flag: presearch-grill-incomplete, detail: "3웨이브 후 미수렴", ts: <ISO 8601>}
```

### 주의사항

- **`user_prompt` 원문 verbatim 잠금** — `refined_user_prompt`는 별도 필드. `user_prompt`에 덮어쓰지 않는다.
- **모호도 판정 재사용** — 자동 트리거는 Readiness Check가 이미 진단한 결과를 재사용한다. 새 판정 로직을 신설하지 않는다.
- **기본 off** — `--grill`이 없으면 수동 트리거는 발동하지 않는다.

**게이트 실행 순서**: Pre-search grill (해당 시) → Step 0 (Context gathering) → **Gate 0** (align, 의도 정렬) → Gate 1 (Requirements) → Gate 2 (Plan + Ambiguities) → Gate 3 (Test Strategy) → Step 2 (Cross-review) → Final Review → Step 4 (Save plan).

## Authoring rules (apply to all Gate outputs)

이 규칙들은 Gate 1 / 2 / 3 / Final Review 출력 *전부* 에 적용된다. 한 군데도 예외 없음.

1. **BLUF (Bottom Line Up Front)** — 각 섹션 첫 줄에 결론 한 문장. 그 후 표 / 리스트 / 근거.
2. **`[!WARNING]`** — breaking change, 위험한 가정, 비가역 결정은 박스로 띄운다. 본문에 묻지 마라.
3. **`[!CAUTION]` 위험영역 회피 금지** — `preamble.md` §8 baseline slug 또는 `risk_areas:` 에 실제로 닿으면 박스로 (영역 + 확인할 것) 명시. SSOT: preamble.md §8.
4. **`<details>`** — 깊은 근거 / 대안 비교 / 긴 인용은 접어둔다. 평소 view 는 BLUF + 표.
5. **작업분해 = 체크리스트** — Task Breakdown / Quality Gates 는 `- [ ]` 체크박스. 줄글 금지.
6. **`file:line` 구체** — Impact Scope 의 "Files to modify" 는 추상명 ("the Weapon class") 금지. **`Source/Combat/Weapon.cpp:128`** 형태로, 가능하면 GitHub permalink markdown link 로 작성 (`[Source/Combat/Weapon.cpp:128](https://github.com/{org}/{repo}/blob/{SHA}/Source/Combat/Weapon.cpp#L128)`).
7. **40 단어 이상 문장 분리** — 한 문장이 40 단어 넘으면 표 / 리스트로 재구성.
8. **첫 등장 약어 한 줄 풀이** — CS / 도메인 약어가 plan.md 안에서 처음 등장할 때만 한 줄 풀이 추가. 같은 문서 내 재등장은 생략.
9. **글로벌 순화 가이드 (SSOT)** — GLOSSARY > preamble §9 텍스트 instruction > LLM 자율 휴리스틱

   본 출력(Gate 1 / 2 / 3 / Final Review 전부)에 등장하는 어휘는 아래 우선순위 순서로 처리한다.

   1. **GLOSSARY 우선**: 본 출력에 등장하는 어휘는 *먼저* `glossary_path` (CLAUDE.md 의 키) 가 가리키는 GLOSSARY 에서 찾는다. hit 시 GLOSSARY 의 풀이/링크 사용.
   2. **preamble §9 텍스트 instruction**: miss 시 `templates/workflow-contract/preamble.md` §9 텍스트 instruction (한글표기/주니어/자연 한글) 을 적용.
   3. **LLM 자율 휴리스틱 + 슬롯 append**: instruction 으로도 자연 한글 대응이 없으면 LLM 자율 휴리스틱을 사용하고, result frontmatter `idiom_candidates:` 슬롯에 append 한다(`{term, ctx, ts}` 형태).

   **§8 박스 비적용**: §8 의 `[!CAUTION]` 박스 내부(영역명·확인 항목)는 짧은 영어 키워드 보존이 가독성에 유리하므로 본 룰의 적용 대상이 아니다. preamble §9 와 동일.

   **위임 시점**: Gate 1 / 2 / 3 / Final Review 출력 *모두* 에 적용. §Authoring rules 전체 prefix 와 정합.

## Approval response rules (Gate 0 / 1 / 2 / 3)

각 게이트의 사용자 승인을 검증한다. **이해(comprehension) 마찰은 게이트마다 흩뿌리지 않고 Gate 2 Spec Preview 한 곳에 집중**한다 — 나머지 게이트는 내용 확인만(bare OK). 형식만 강제하면 화면의 텍스트를 복사해 통과하므로(구문 검사 ≠ 인지 검사), 복사 불가 마찰을 한 지점에 모은다.

승인 형식:

| 게이트 | 허용 형식 | 비고 |
|---|---|---|
| **Gate 0** (align) | **bare OK** | 내용 정렬은 grill `align` diff가 수행 (real-fork, 유도 금지) |
| **Gate 1** (Requirements) | **bare OK** (`"OK"`/`"진행해"`) — 또는 `"수정"`/`"투자·제외 재분류"` | 의도 승인. 분기 상세는 §Gate 1 |
| **Gate 3** (Test Strategy) | **bare OK** | 파생 게이트 — 완전성은 Test Agent + Step 2 cross-review(Type D)가 검증 |
| **Gate 2 Spec Preview** | **단일 프로브** | 유일한 복사 불가 이해 검증 지점 (§Spec Preview: why-not/mechanism/boundary, recall 금지) |

- **Gate 2 Spec Preview — 단일 프로브로 검증**: 옵션 선택형 단답은 정상 흐름. 단 Spec Preview에서는 §Spec Preview의 단일 프로브(why-not / mechanism-predict / boundary-recognition 중 상황별 하나)로 이해를 확인한다. recall("적어봐")이 아니라 recognition·반사실로 — 답이 화면에 없어 복사가 안 되게.
- **disagreement-first**: bare OK 게이트도 "맞나?"보다 "어긋난 데 있나?"로 물어 확증편향을 줄인다.
- **skip 카운터 (mode 별 분리)** — skip 요청 유형에 따라 카운터를 분리한다:
  - **pre-search skip**: Pre-search grill이 자동(검색불가 갭) 또는 수동(`--grill`)으로 발동된 후 사용자가 명시적 skip(`--skip-grill` / "grill 빼고" / "skip") 요청 시 → plan.md frontmatter `skip_presearch` +1. Pre-search grill을 건너뛴 횟수.
  - **Gate 2 ambiguity skip**: 사용자가 Gate 2 Ambiguity에 대해 §SKIP behavior 경로(Turn 7+ "skip" 또는 명시 `--skip-grill` / "건너뛰기")를 쓰면 → plan.md frontmatter `skip_gate2` +1. Gate 2 Ambiguity를 건너뛴 횟수.
  - 일반 "일괄 결정"(각 Ambiguity 에 explicit 응답을 모아 한 번에)은 정상 흐름이므로 카운트 X.
  - 두 카운터 모두 PR 본문 주입 시 노출.

## Self-pass turn

매 Gate (1 / 2 / 3 / Final) 출력 직후, `self_pass` 가 ON 이면 *internal* 한 턴을 추가로 돌린다. 사용자에게 노출되지 않는 reasoning.

**내부 turn 의 체크 항목:**

1. `preamble.md` §9 텍스트 instruction (한글표기 / 주니어 가정 / 자연 한글) 위반 어휘 검색.
2. spec-plan Authoring §9 우선순위 (GLOSSARY > preamble §9 텍스트 instruction > LLM 자율 휴리스틱) 적용 여부.
3. 위반 발견 시 revised 출력을 *사용자에게 노출되는 turn* 으로 다시 내보낸다. revised 가 unchanged 이면 그대로 진행 (no-op).

`self_pass = OFF` 면 step 전체 skip.

## Gate event recording

매 게이트 (0 / 1 / 2 / 3) 가 종료(OK / revise / skip)할 때마다 plan.md frontmatter `gate_events:` 에 한 줄 append:

```yaml
- {gate: 0, result: ok|revise|skip, turns: <int>, self_pass: <bool>, ts: <ISO 8601>}
- {gate: 2, result: ok|revise|skip, turns: <int>, self_pass: <bool>, ts: <ISO 8601>}
```

`gate` 필드 허용 값: `0` (align), `1` (Requirements), `2` (Plan + Ambiguities), `3` (Test Strategy).

Gate 2 Spec Preview 프로브가 발동하면 별도 한 줄 append:
```yaml
- {gate: 2, probe: why-not|mechanism|boundary, result: pass|revised-plan|proceed-flagged, turns: <int>, ts: <ISO 8601>}
```
`result` 의미: `pass`(이해 확인) / `revised-plan`(프로브가 plan 결함을 잡아 revise) / `proceed-flagged`(2회 후 미align — `gate2-comprehension-incomplete` 달고 진행).
프로브가 조건부 발동 skip된 경우(사용자가 Ambiguity real-fork에서 직접 선택)에는 probe 행을 append하지 않는다.

`self_pass`: 본 gate 의 출력 직후 self-pass turn 이 발동했는지 (ON + revised or unchanged) / OFF 면 false.
Gate 0 (align) 는 light gate 이므로 self-pass 는 "생략 가능" — 미결(Open Question).

**`turns` 정의**: gate 첫 출력부터 최종 OK 까지의 **사용자 응답 메시지 수** (AI 출력 카운트 X, revise 응답 포함). 예: AI 출력 → "ok" 거부 → "맞다 X" = turns 2.

자동 기록은 spec-plan 이 처리. Final Review 직전 점검.

## Gate 2 stuck detection — 5턴 힌트 + turn 6+ 형식 강제

Gate 2 는 *상시 이해 게이트* (Plan / Ambiguity 결정). 5턴 힌트는 *별도 게이트 아님* — Gate 2 안의 stuck detection 안전판.

### Gate 2 sequential 휴리스틱 (grill mode)

Gate 2 Ambiguity 표를 제시하기 *전에*, LLM 이 각 항목을 자동 판정한다:

> **판정 기준**: "이 Ambiguity 가 미결이면 작업 방향이 크게 바뀐다" — 예) 아키텍처 결정, 데이터 흐름 분기, 인터페이스 계약 변경 등.

- **방향을 크게 바꾸는 항목** → grill 엔진 `grill` mode 로 sequential 처리 (one-at-a-time) (SSOT: `templates/workflow-contract/grill.md` §2.4, §4):

  ```
  grill(
    mode:   grill
    seed:   <해당 Ambiguity 항목>
    cap:    3
    output: ambiguity_decision
  )
  → 수렴 시: 항목 결정 기록.
  → 미수렴(3웨이브) 시: readiness_flags += {flag: gate2-grill-incomplete, detail: "3웨이브 후 미수렴", ts: <ISO 8601>}
  ```

- **나머지 항목** → 기존 batch 표를 그대로 유지 (일괄 결정 허용).

**주의**: 모든 Ambiguity 를 sequential 로 만들지 않는다. 방향을 좌우하는 항목 한정이므로 우회 유발이 낮다 (plan §4 다이얼).

---

### Turn 1-4 (평시, 자유 응답)

- Ambiguity 옵션 명시 선택 강제 (bare "ok" 거부 — 각 결정은 explicit, Gate 2 STOP 규칙) = *간접* 이해 검증.
- 자유 응답 허용, 마찰 최소화.

### Turn 5+ — Stuck escalation (조건부, SSOT)

`turns`가 5에 도달하면 stuck escalation 진입 — Turn 5 진단 + bi-directional check → Turn 6+ 응답 형식 강제(셋 중 하나) → Turn 7+ 최종 분기(정지/계속/skip). 상세: `templates/workflow-contract/gate-escalation.md` §1 (경로 해석: §Template path resolution).

## SKIP behavior

사용자가 Gate 2 Ambiguity를 SKIP하면(Turn 7+ 분기 또는 명시 `--skip-grill` / "건너뛰기") → 분류 강등(Ambiguities→Open Questions) + task 분해 영향 검증 + `skip_gate2` +1 + Open Question 마킹. implementer는 SKIP된 Open Question을 자기 판단으로 결정·기록(일반 Open Question 흐름). 상세: `templates/workflow-contract/gate-escalation.md` §2.

## Iterative search protocol (max 3 cycles)

Used by Spec Agent and Code Agent:
1. DISPATCH: search target paths with feature keywords — **검색 잠금**: `refined_user_prompt` > substantive `user_prompt` > 티켓 키워드 순 (§intent.problem 출처 우선순위)
2. EVALUATE: score results 0.0–1.0 for relevance, identify gaps
3. REFINE: use discovered terms to broaden search (codebase may use different terminology)
4. LOOP: repeat until sufficient coverage or 3 cycles reached

## Step 0 — Context gathering (parallel)

> **검색 잠금**: 모든 에이전트의 키워드 검색은 **`refined_user_prompt` > substantive `user_prompt`(Mode A) > 티켓 키워드(Mode B)** 우선순위로 잠근다(§intent.problem 출처 우선순위와 동일). user_prompt가 의례적이면 그것으로 검색하지 않는다. Iterative search protocol도 동일하게 적용. 이 규칙은 이하 5개 에이전트 전부에 공통으로 적용된다.

Spawn 5 read-only subagents in parallel:

**[Jira Agent]** (sonnet)
- `jira-tools get {TICKET}` via Bash (returns JSON)
- Collect: description, acceptance criteria, related issues, epic context
- If fails: ask user to paste ticket details
**[Spec Agent]** (sonnet) — skip if no config

- If `docs_path` is set in CLAUDE.md `## Implementation Config` AND `${docs_path}/adr.yaml` or
  `${docs_path}/conventions.yaml` exists: read those yaml files. Filter entries by `stacks:` tag
  matching ticket keywords. Cite each surfaced item by its `id` (e.g., `ADR-014`, `CONV-007`).
- Else (yaml absent): fall back to **plain-text search** of `prd_path`, `specs_path`,
  `policies_path` using the iterative search protocol (existing behavior). No regression.
- Return: requirements, priorities (P0/P1), open questions, **and a list of cited doc IDs (or
  none)**.
**[Code Agent]** (opus)
- Search codebase files matching ticket keywords using iterative search protocol
- Return: affected files, dependency map, risk areas, test coverage
**[Context Agent]** (sonnet) — skip if no config
- Search `log_repo` for past similar work logs
- Return: related knowledge, past learnings
**[Test Agent]** (sonnet) — spawn `test-engineer` in Strategy mode; return its `<test-plan>` output
## Gate 0 — Align (의도 정렬)

> **실행 위치**: Step 0 완료 직후, Gate 1 진입 직전.
> **강도**: light — 1~2질문으로 짧게 닫는다. 수렴되면 바로 Gate 1로 진행.

### Gate 0 목적

`user_prompt`·`intent.problem`의 "문제 한 줄"과 Step 0 탐색 결과를 대조해 사용자 의도와 AI 이해가 일치하는지 확인한다. 어긋남이 있으면 짧은 정렬 대화를 거쳐 일치를 확정받는다. 복잡하면 grill 엔진으로 자연 승격.

### Gate 0 실행

grill 엔진을 `align` mode로 호출한다 (SSOT: `templates/workflow-contract/grill.md` §2.1, §4):

```
grill(
  mode:   align
  seed:   "문제 한 줄 ↔ Step 0 findings"
  cap:    small (light gate — 1~2웨이브)
  output: intent_history
)
→ 수렴 시: 일치 확인 기록.
  사용자가 직접 확정한 경우에만 intent_history += {ts, field: problem, prev_value, reason}
→ 미수렴 시: 호출자 자체 판단 (readiness_flags에 기록 권장)
```

**diff 노출**: "당신 문제 한 줄 ↔ 내가 찾은 것"을 대조해 어긋남이 있으면 짧은 정렬 대화를 먼저 시도. 어긋남이 없으면 바로 Gate 1로 진행.

### intent.problem 갱신 경로 (3조건 — 모두 충족해야 갱신 가능)

Gate 0 대화 중 문제 한 줄을 바꿔야 하는 경우:

1. **(명시적 확정)** 사용자가 "문제 한 줄을 X로" 직접 확정한 경우에만 갱신한다.
2. **(기록 강제)** `intent_history`에 `{ts, field: problem, prev_value: <원문 그대로>, reason}` 항목을 추가한다. 변경 전 텍스트를 verbatim(원문 그대로)으로 보존한다.
3. **(AI 단독 변경 금지)** diff를 사용자에게 제시할 수만 있고, 사용자 확정 없이는 갱신 불가.

> **verbatim 원칙**: 동결 대상은 **앵커 `user_prompt`**다. `intent.problem`은 그 앵커의 충실한 요약(Mode A/B)이라 의미 보존 하에 한 줄로 정리될 수 있고, 사용자가 직접 확정하면 갱신된다 — AI의 조용한 의역만 금지.

### Gate 0 승인 형식

**bare OK 허용** ("OK"/"진행"/"맞다"). 별도 형식 강제 없음.

> 근거: Gate 0의 본업은 *내용 정렬*(명시 문제 ↔ 발견된 실제)이고 grill `align` 메커니즘이 수행한다. 이해 검증의 'Spec Preview 집중' 원칙은 §Approval response rules 참조.

> **diff는 real-fork로 — leading 금지**: 어긋남을 제시할 때 "코드는 Y로 보입니다, Y 맞죠?"(유도형)는 rubber-stamp를 부른다. **양쪽을 다 깔고 AI lean을 보류**해 사용자가 직접 고르게 한다: "티켓은 X, 코드 실제는 Y — 어느 쪽이 이 작업의 문제죠? 고른 쪽이 왜 맞는지 한 줄." (불일치 없으면 바로 Gate 1)

### Gate 0 기록

Gate 0 종료 시 `gate_events:`에 한 줄 append:
```yaml
- {gate: 0, result: ok|revise|skip, turns: <int>, self_pass: <bool>, ts: <ISO 8601>}
```
self_pass: Gate 0 는 light gate 이므로 생략 가능 (미결 — Open Question).

---

## Gate 1 — Requirements

> **STOP**: Do not proceed to Gate 2 without explicit user approval ("OK", "수정", or scope reclassification).
> Saying "진행해" alone is sufficient approval; silence is not.

Synthesize Step 0 output into **Requirements only** (no Impact scope, no Task breakdown, no Test Strategy yet):

```markdown
### Requirements
- P0: [items]
- P1: [items]

### Intentional Exclusions

| 제외 항목 | 이유 |
|---|---|
| {item} | {비용 X / 위험 Y / 타이밍 Z 중 하나를 명시 — "우선순위 낮음", "out of scope", "not now" 같은 동어반복 금지} |

> 운영 규칙: 이유 컬럼이 비어 있거나 동어반복("out of scope", "not now", "우선순위 낮음" 등)이면
> Gate 2로 진행하지 않는다. 각 항목에 비용/위험/타이밍 근거를 반드시 명시한다.

### Open Questions
- [decisions needed — items that can be decided during implementation without breaking task decomposition]
```

Present Gate 1 output. Wait for user decision:
- **"OK"** → proceed to Gate 2
- **"수정"** → revise in-place, re-present Gate 1, wait again
- **"투자/제외 재분류"** → move item between P0/P1/Intentional Exclusions, re-present Gate 1, wait again

**사용자 승인 없이는 Gate 2로 진행하지 않는다.**

## Gate 2 — Plan + Ambiguities

> **STOP**: Do not proceed to Gate 3 until the user has explicitly resolved every item in the Ambiguities table.
> Items may be resolved all at once ("일괄 결정") but each decision must be stated explicitly.

Using the Gate 1 approved Requirements, synthesize Impact Scope, Task Breakdown, Risks, and Ambiguities:

```markdown
### Impact Scope
- Files to modify: [list]
- Dependencies: [modules]
- Risks: [areas]

### Task Breakdown
1. {task} — size: {XS/S/M/L/XL}, depends: {none or task N}

Sizing: XS: 1 file | S: 2-3 files | M: module-level | L: cross-module | XL: must split

### Ambiguities (require decision before tasks freeze)

> Ambiguities는 "지금 결정하지 않으면 task 분해가 무너진다".
> Open Questions(Gate 1)는 "구현 중 결정해도 무방"한 항목.
> Ambiguities와 Open Questions를 혼용하지 말 것.

| # | 논의점 | 옵션 A | 옵션 B | 결정자가 알아야 할 trade-off |
|---|---|---|---|---|
| 1 | {모호한 결정 지점} | {A안 + 한줄 결과} | {B안 + 한줄 결과} | {둘 중 어느 쪽이 비용/시간/위험에 어떻게 영향} |
```

Present Gate 2 output. Each Ambiguity must be decided before proceeding:
- User resolves Ambiguities (one by one or all at once, but each decision must be explicit)
- After all Ambiguities resolved: AI 가 **Spec Preview** (아래) 출력 → 사용자 최종 확인 → Gate 3

**사용자 승인 없이는, 그리고 Ambiguities가 하나라도 미결인 상태에서는 Gate 3으로 진행하지 않는다.**

### Spec Preview — 이해 검증 (Gate 2 마지막 단계, 유일한 복사 불가 마찰 지점)

Ambiguity 가 전부 결정된 후, **사용자가 직접 안 고른 핵심 결정**(AI가 Task Breakdown에서 단독으로 정한 것)이 있으면 단일 프로브로 이해를 검증한다. 목적: form-matching(옵션은 골랐지만 조합 결과는 안 그려본) self-catch. 형식 강제(맞다+한줄/근거)는 화면 텍스트 복사로 뚫리므로 쓰지 않는다 — **사용자가 화면에 없는 정보를 생성/판단하게** 한다.

**조건부 발동 (불필요한 마찰 차단)**:
- 사용자가 Ambiguity real-fork에서 *직접 고른* 결정 → 그 선택이 곧 이해 증명 → 프로브 **skip**.
- AI가 단독으로 정한 결정만 → 프로브 발동 (그 결정의 trade-off는 화면에 없으니 복사 불가).
- 단독 결정이 없으면 Spec Preview는 결과 한 줄 확인으로 닫고 Gate 3 진행.

**단일 프로브 — 상황별 하나만 1회** (recall 금지·recognition/반사실 원칙):

| 상황 | 프로브 | 검증 |
|---|---|---|
| 진짜 대안이 있던 AI 단독 결정 | **why-not**: "B 대신 A로 가는데, B면 이 문제에서 뭐가 틀어지지? 한 줄" | 문제해결방안 + 구현방법 + 선택의도 동시 |
| 대안 없던 강제 구현 | **mechanism-predict**: "이 구현에 [구체 입력 X] 들어오면 결과가 뭐지?" (답 보류) | 구현 방법 이해 |
| 범위까지 확인 | **boundary-recognition**: "[구체 엣지 Y] — 이 계획 안이야 밖이야?" | 경계 = 방법 이해의 역증명 |

- **recall 금지**: "안 다루는 케이스 적어봐"(빈칸 생성)는 화면의 Intentional Exclusions에서 복사되거나 불공정하게 어렵다. 반드시 **recognition**(AI가 구체 인스턴스를 던지고 사용자는 in/out·예측만).
- **why-not은 forked 결정엔 쓰지 않는다**: trade-off가 Ambiguity 표에 노출돼 복사 가능. AI 단독 결정에만.

**miss 플로우** (프로브 답 어긋날 때): (0) 계획버그냐 이해miss냐 먼저 분기 → 1차 align-hint → 2차 teach+rotate → 3차 명시분기(진행+플래그 `gate2-comprehension-incomplete` / 정지 / impl 위임). **2회에서 끊고 계측.** 상세: `templates/workflow-contract/gate-escalation.md` §3.

> Spec Preview ≠ Final Review: Preview = Gate 2 결정 조합 이해 검증, Final Review = 모든 게이트 + cross-review. (Final Review에서 미align gap이 닫히면 해당 readiness_flag의 resolution 채움 — §Step 4 readiness_flags)

## Gate 3 — Test Strategy

> **STOP**: Do not proceed to Step 2 (Cross-review) without explicit user approval.

Using Gate 2's task-level AC and risk areas, incorporate the Test Agent's `<test-plan>` output:

```markdown
### Test Strategy
- Unit: [targets from Test Agent]
- Integration: [targets from Test Agent]
- E2E: [critical user flows from Test Agent]
- Risk areas: [high-priority test targets]

### Quality Gates
- [ ] All tests pass
- [ ] No regressions in affected modules
- [ ] Coverage maintained or improved on changed files
- [ ] Build succeeds
```

Present Gate 3 output. Wait for user (disagreement-first — "맞나?"보다 "어긋난 데 있나?"로 물음):
- **"OK" / "진행"** (bare OK) → proceed to Step 2 (Cross-review)
- **"수정" / "틀린 곳: …"** → revise Test Strategy, re-present Gate 3, wait again

> Gate 3은 파생 게이트 — 테스트 완전성 검증은 사용자 근거가 아니라 Test Agent + Step 2 cross-review(Type D)가 담당. bare OK로 충분.

**사용자 승인 없이는 Step 2(Cross-review)로 진행하지 않는다.**

> **Shortcut**: If the user explicitly requests "건너뛰기" or "skip gates", all three gates may be combined into a single output. Default behavior is 3 separate gates.

## Step 2 — Cross-review (3 rounds max)

Conflict types:

| Type | Pair | Trigger |
|------|------|---------|
| A | Code vs Spec | Code Agent flags high risk on a Spec Agent P0 item |
| B | Code vs Tests | edit order conflicts with existing test dependencies |
| C | Jira vs Code | deadline vs prerequisite refactoring |
| D | Test vs Code | Test Agent recommended level conflicts with Code Agent's identified coverage or risk assessment |

On conflict: pass opposing result to each agent → re-analyze. Max 3 rounds.
Unresolved after 3 rounds → present both opinions in Final Review.

## Final Review (post cross-review)

Present consolidated plan summary (all gates + cross-review results). User can:
- Revise → update plan → re-confirm
- "Investigate more" → re-spawn relevant agent
- "OK" → Step 4
- "Cancel" → exit without saving

> **readiness_flags resolution 점검** (저장 전 필수): resolution이 빈 항목(터미널형 `gate2-comprehension-incomplete` / `*-grill-incomplete` 포함)을 훑어, Final Review 시점에 gap이 닫혔으면 resolution을 채운다. 닫히지 않았으면 빈 값 유지(= 우회 신호). 이 점검이 빈 resolution의 유일한 fill 지점이다.

## Step 4 — Save plan

1. Save to `.claude/plans/{TICKET}/plan.md` in the project repo. If exists, save as `plan-v{N}.md`.
2. The plan.md file must begin with the following YAML frontmatter:

```markdown
---
ticket: {TICKET}
created_at: {ISO 8601 with timezone}
user_prompt: |
  {사용자가 /spec-plan을 호출하며 입력한 최초 프롬프트 전문 — indent 보존. 요약·정제 금지. verbatim 잠금.}
refined_user_prompt: |
  {Pre-search grill이 실행된 경우 — grill(mode: refine) 결과물. 사용자가 confirm한 정련된 prompt. user_prompt 원문은 변경하지 않고 이 필드에 별도 보존. grill 미실행 시 이 필드 생략(emit 금지).}
intent:
  problem: |
    {§intent.problem 출처 우선순위로 확정한 "문제 한 줄". user_prompt(Mode A) 또는 티켓 본문(Mode B)의 **충실한 요약 허용 — 의미 왜곡 금지**. 기능 레벨. 원문 자체는 user_prompt 필드에 verbatim 보존.}
  approach: |
    {이 기능을 어떻게 만들 것인가 — TechSpec BLUF 한 줄. spec-plan 이 생성.}
  why: |
    {왜 이 접근인가 — 대안 대비 한두 줄. ADR-light. spec-plan 이 생성.}
  prd_ref: {PRD / 티켓 / pitch 링크 — PRD 레벨 P/A/W 는 여기로}
risk_areas: []        # +α slug 만 (baseline 5종 — memory/replication/concurrency/architecture/build-deploy — 은 preamble.md §8 하드코딩, 본 필드에 중복 X). 자유 추가 영역도 같은 kebab slug 형식.
docs_cited: [ADR-014, CONV-007]   # omit 가능 — yaml docs 없을 때는 필드 자체 제거 (빈 배열 emit 금지)
readiness_flags: []   # 진단형(Readiness Check "이상") + 터미널형(presearch-grill-incomplete / gate2-grill-incomplete / gate2-comprehension-incomplete). 각 {flag, detail, resolution, ts}. resolution = 저장 전에 gap이 닫혔으면 메모, 아니면 빈 값(= 우회) — 진단형/터미널형 공통.
skip_presearch: 0     # pre-search grill 명시적 skip 시 +1 (Approval response rules)
skip_gate2: 0         # Gate 2 Ambiguity 명시적 skip 시 +1 (SKIP behavior)
gate_events:          # 게이트 별 결과 자동 기록. {gate, result, turns, self_pass, ts}. Spec Preview 프로브는 {gate:2, probe, result: pass|revised-plan|proceed-flagged, turns, ts}. turns = 사용자 응답 메시지 수. gate 허용값: 0(align)/1/2/3.
  - {gate: 0, result: ok, turns: 1, self_pass: false, ts: ...}
  - {gate: 1, result: ok, turns: 1, self_pass: true, ts: ...}
intent_history: []    # intent.{problem,approach,why} 변경 이력. append-only. 각 {ts, field, prev_value, reason}. prev_value = 변경 전 텍스트 그대로 (hash 아님).
risk_acks: []         # [!CAUTION] ack 결과. 각 {area, ack: confirmed|needs_check, ts}. area = baseline slug 또는 risk_areas: 의 +α slug.
---

# Plan — {TICKET}: {feature name}

## Intent (BLUF)

- **Problem**: {intent.problem 본문 — 한 단락. PRD 레벨이 아니라 *기능 한 건* 레벨.}
- **Approach**: {intent.approach 본문}
- **Why (vs alternatives)**: {intent.why 본문, 대안 1-2 개 비교}
- **PRD**: {intent.prd_ref 링크}

(이후 본문은 Gate 1 / 2 / 3 결과를 BLUF + 표 + `<details>` 로 정리)
```

3. **Verbatim 잠금 (분리)**: `user_prompt` = On activation step 3 의 원문 — **verbatim 동결**(감사 앵커, 의례적 입력 포함). `intent.problem` = §intent.problem 출처 우선순위 결과 — **충실한 요약 허용, 의미 왜곡 금지**(앵커는 user_prompt가 보존). `intent.approach` / `intent.why` 는 Gate 2 결과로 spec-plan 이 생성.
4. `docs_cited`: yaml docs 없으면 필드 자체 제거 (빈 배열 emit 금지).
5. Telemetry 메타(`gate_events` / `intent_history` / `risk_acks` / `skip_presearch` / `skip_gate2`)는 spec-plan 이 자동 append.
6. `/impl` 가 task 생성 시 `user_prompt` + `intent.problem` 을 task frontmatter (`intent_problem`) 로 복사, `plan_sha` 는 `git hash-object` 결과, `contributes_to` 는 분해 시점 자동 생성.
7. Tell user: "Plan saved. Run `/impl {TICKET}` when ready."

## Error handling

Missing config or PRD → skip the relevant agent and proceed with remaining data.
