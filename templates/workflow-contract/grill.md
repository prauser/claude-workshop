# Grill 엔진 SSOT

> 이 파일은 공유 SSOT(단일 진실 공급원, Single Source of Truth)이다.
> spec-plan.md 와 impl.md 가 인용한다.
> 배포 위치: `templates/workflow-contract/grill.md` → `~/.claude/templates/workflow-contract/grill.md` (deploy.sh 경유).
>
> **[!CAUTION] 위험영역: `architecture` (모듈 의존성·서브시스템 경계)**
> 이 파일이 없으면 호출자(spec-plan/impl)는 "deploy.sh 미실행" 경고를 출력하고 즉시 중단한다.
> 배포 전 반드시 `./deploy.sh`를 실행해 `~/.claude/` 경로에 동기화하라.

---

## 1. 엔진 개요

Grill 엔진은 **one-at-a-time(한 번에 한 질문) 멀티턴 인터뷰 루프**이다.

핵심 원칙:
- 질문 1건을 던지고 사용자 답을 기다린 뒤 다음으로 넘어간다. 배치(batch) 표로 여러 질문을 한꺼번에 나열하지 않는다.
- 호출자(caller)가 `mode`·씨앗 입력·종료 산출물·캡(cap, 최대 라운드 수)을 파라미터로 넘긴다.
- 엔진은 그 파라미터를 받아 동일한 인터뷰 루프를 실행하고 구조화된 산출물을 반환한다.

설계 근거: `.claude/runs/PRA-66/grill-ritual-notes.md` §1~§7 (T1 추출 노트) + `notes/impl-workflow/approval-clarity-followup.md` §6.1.

---

## 2. 4가지 mode

같은 one-at-a-time 엔진을 호출하는 위치에 따라 mode와 산출물이 다르다.

| mode | 호출 위치 | 씨앗 입력 | 종료 산출물 | 강도 |
|---|---|---|---|---|
| `align` | Gate 0 (spec-plan) | 문제 한 줄 ↔ Step 0 탐색 결과 | 일치 확인 + (필요 시) intent.problem 갱신 | light |
| `refine` | Pre-search 정련 (spec-plan) | 모호한 raw prompt | `refined_user_prompt` | wave(캡) |
| `elicit` | impl 자유 텍스트 경로 | 자유 텍스트 (plan 없음) | 요구 목록 + mini-Intent(problem/approach) | 조건부 |
| `grill` | Gate 2 순차(sequential) (spec-plan) | 방향을 좌우하는 Ambiguity 항목 | 항목 결정 | 복잡도 휴리스틱 |

### 2.1 `align` mode

- **씨앗**: 사용자가 입력한 "문제 한 줄"과 Step 0 탐색이 발견한 내용.
- **목표**: 사용자 의도와 AI 이해가 일치하는지 확인. 불일치 발견 시 diff를 사용자에게 제시하고 확정받는다.
- **산출물**: 일치 확인 기록. 사용자가 직접 확정한 경우에만 `intent.problem` 갱신 + `intent_history` 항목 추가.
- **강도**: light — 1~2질문으로 짧게 닫는다. Gate 0는 Gate 2보다 관문이 낮다. Gate 0 승인 형식은 "맞다+한줄" — bare OK 불가 (Gate 1=bare OK < Gate 0=맞다+한줄 < Gate 2/3=맞다+근거).
- **갱신 3조건** (모두 충족해야 갱신 가능):
  1. Gate 0 대화에서 사용자가 "문제 한 줄을 X로" 직접 확정.
  2. `intent_history`에 `{ts, field: problem, prev_value, reason}` 추가(변경 이력 보존).
  3. AI 단독 변경 금지 — 사용자 확정 없이 갱신 불가.

### 2.2 `refine` mode

- **씨앗**: 검색에 쓰기에 모호한 raw prompt.
- **목표**: 멀티턴 wave 인터뷰로 prompt를 검색 가능하도록 구체화한다.
- **산출물**: 사용자가 확인(confirm)한 `refined_user_prompt`. `user_prompt` 원문은 변경하지 않고 verbatim으로 유지한다.
- **강도**: wave 캡 적용 (§3 공통 캡 참조).
- **미수렴 처리**: 캡 도달까지 정련이 완료되지 않으면 `readiness_flags`에 `presearch-grill-incomplete` 슬러그를 기록한다.

### 2.3 `elicit` mode

- **씨앗**: plan 없이 들어온 자유 텍스트 입력.
- **목표**: 요구사항을 발굴하고 의도를 구조화한다.
- **산출물**: 요구 목록(bullet) + mini-Intent — `problem`/`approach` 두 필드로 구성. plan이 없는 경로에서 의도를 보존하는 최소 구조.
- **강도**: 조건부 — 입력이 이미 충분히 명확하면 인터뷰 없이 직접 산출물을 생성한다.

### 2.4 `grill` mode

- **씨앗**: 방향을 좌우하는 Ambiguity 항목. Gate 2에서 LLM이 "미결 시 작업 방향이 크게 바뀐다"고 판정한 항목만 이 mode를 사용한다. 나머지는 기존 배치 표를 그대로 쓴다.
- **목표**: 하나씩 질문해 항목을 결정한다. 설계 트리의 각 분기를 의존성 순서대로 하나씩 해소한다.
- **산출물**: 각 Ambiguity 항목의 결정 기록.
- **강도**: 복잡도 휴리스틱 — 방향을 크게 바꾸는 항목에 한해 적용하므로 우회 유발이 낮다.
- **선택 기준(복잡도 휴리스틱)**: LLM이 자동 판정 — 'Ambiguity 미결 시 작업 방향이 크게 바뀐다'고 판단한 항목에만 이 mode를 적용, 나머지는 기존 배치 표.

---

## 3. 공통 규칙

### 3.1 one-at-a-time (한 번에 한 질문)

질문 1건 → 사용자 답 대기 → 다음 질문으로 이동하는 순서를 반드시 지킨다. 배치 표 또는 번호 목록으로 여러 질문을 한꺼번에 제시하는 것은 금지한다.

### 3.2 양방향 확인 (bi-directional confirmation)

매 라운드 또는 종료 직전, AI가 "지금까지 이해한 것"을 되읽어(read-back) 사용자가 정정할 수 있도록 한다.

흐름:
```
사용자 답변
  → AI: "제가 이해한 것은 … 맞나요?"   ← AI 이해 되읽기
  → 사용자: 정정 또는 확인              ← 사용자 정정
  → 다음 질문 또는 종료
```

단순 OK/PASS가 아니라 이해 확인(comprehension check)이 목적이다. 원형: `spec-plan.md:122–136` turn 5 양방향 루프.

### 3.3 캡 + 자연종료 (wave cap + early exit)

| 항목 | 기본값 | override |
|---|---|---|
| 최대 웨이브(wave) 수 | **3웨이브** | 호출자가 캡을 파라미터로 override 가능 |
| 웨이브당 질문 수 | 1~2질문 | — |
| 조기 종료 조건 | 정렬(align) 달성 시 캡 소진 전 자연종료 | — |

웨이브 순서: **목표 → 엣지 케이스(edge case, 경계 상황) → 가정(assumption)**

- Wave 1 — 목표: "무엇을 달성하려 하나?" (문제·의도의 핵심 확인)
- Wave 2 — 엣지 케이스: "경계 상황은 어떻게 처리하나?" (예외·비정상 경로 탐색)
- Wave 3 — 가정: "어떤 전제를 깔고 있나?" (암묵적 가정 노출)

### 3.4 미수렴 처리

캡 도달까지 수렴하지 못하면 호출자가 기록 슬롯에 남기도록 엔진이 신호를 보낸다.

| mode | 미수렴 플래그 슬러그 | 기록 위치 |
|---|---|---|
| `refine` | `presearch-grill-incomplete` | `readiness_flags` |
| `grill` | `gate2-grill-incomplete` | `readiness_flags` |
| `align`, `elicit` | (호출자 자체 판단) | (호출자 슬롯 지정) |

슬러그 형식은 kebab-case(소문자 단어를 하이픈으로 연결)이다.

---

## 4. 호출 규약

호출자(spec-plan.md 또는 impl.md)가 본 엔진을 인용할 때 다음 파라미터를 명시한다.

```
grill(
  mode:    align | refine | elicit | grill
  seed:    씨앗 입력 (문자열 또는 항목 목록)
  cap:     웨이브 최대 수 (기본 3, override 가능)
  output:  종료 산출물 슬롯 이름 (예: refined_user_prompt, intent_history 등)
)
```

호출 예시 (spec-plan pre-search):
```
grill(mode: refine, seed: <user_prompt>, cap: 3, output: refined_user_prompt)
→ 수렴 시: refined_user_prompt 반환
→ 미수렴 시: readiness_flags += presearch-grill-incomplete
```

호출 예시 (impl free-text):
```
grill(mode: elicit, seed: <free_text_input>, cap: 3, output: mini_intent)
→ 수렴 시: {problem, approach} 반환
→ 미수렴 시: 호출자 자체 슬롯에 미수렴 사실 기록 (슬롯 이름은 호출자 결정)
```

호출 예시 (Gate 0 align):
```
grill(mode: align, seed: "문제 한 줄 ↔ Step 0 findings", cap: small, output: intent_history)
→ 수렴 시: 일치 확인 기록. 사용자가 직접 확정 시에만 intent_history += {ts, field: problem, prev_value, reason}
→ 미수렴 시: 호출자 자체 판단
```

**경로 해석(template path resolution)**: 호출자는 cwd의 `templates/workflow-contract/grill.md`를 우선 확인하고, 없으면 `~/.claude/templates/workflow-contract/grill.md`로 폴백한다. 파일이 두 경로 모두에 없으면 "deploy.sh 미실행" 경고를 출력하고 중단한다 (`impl.md:7-15` 동형 규칙).

---

## 5. 상호 참조

| 파일 | 관계 |
|---|---|
| `templates/workflow-contract/preamble.md` | 공통 preamble SSOT — 이 파일과 동일 계층의 공유 규칙 |
| `templates/workflow-contract/contract.md` | 워크플로 아티팩트(artifact) 계약 — SSOT 상호참조 관례 정의 |
| `claude-config/commands/spec-plan.md` | Gate 0 align / pre-search refine / Gate 2 grill 호출자 |
| `claude-config/commands/impl.md` | free-text elicit 호출자 |
| `.claude/runs/PRA-66/grill-ritual-notes.md` | 본 엔진의 설계 근거 — T1이 추출한 인터뷰 리추얼 노트 |
