---
title: 승인 게이트 이해도 강화 — spec-plan/impl 개선 플래닝
created_at: 2026-05-27
status: planning
branch: claude/workflow-approval-clarity-m6oU9
---

# 승인 게이트 이해도 강화 플래닝

> **TL;DR** — spec-plan/impl 워크플로우에 "사람이 *제대로 이해하고* 승인"하도록 돕는 레이어를 추가한다.
> 90%는 *에이전트가 마크다운을 쓰는 방식*을 바꾸는 상시(light) 처방이고, teach-back 같은 무거운 처방은
> **위험영역에서만** 발동한다(friction dial). 새 명령은 만들지 않고 기존 게이트에 흡수한다.

## Intent Header (이 문서 자체가 적용 예시)

- **Feature**: 승인 게이트 이해도 강화 (Approval Comprehension Layer)
- **Problem/Job**: 워크플로우 사용자가 게이트에서 *OK는 누르지만* 무엇을·왜 승인하는지 모른 채 통과한다 — "이해 못 하면 내 코드가 아니다" 원칙이 구조적으로 안 지켜짐.
- **Goal / Non-Goals**: 게이트를 *컴플라이언스 체크 → 이해 체크*로 전환한다. / 게이트를 전부 무겁게 만들지 않는다(우회 유발), 새 별도 명령을 만들지 않는다.
- **Approach**: 상시 쓰기 규율(Intent Header·구조화·용어집·file:line) + 위험영역 한정 무거운 이해 확인(teach-back·diagram·design note)을 기존 spec-plan/impl 게이트에 흡수.
- **Why (vs alternatives)**: `/grill-with-docs`를 별도 명령으로 붙이는 안은 게이트 풍부한 `/spec-plan`과 경쟁·중복되어 기각. 전 게이트 무겁게 하는 안은 우회(skip) 유발로 기각.
- **PRD/근거**: 본 문서 + 팀 "AI 기반 개발 가이드라인" + 5건 리서치(STE100/teach-back/DDD/PR-FAQ/RFC/ADR/Shape Up/OSC8/Mermaid).

---

## 1. 배경 — 핵심 진단

현재 게이트의 승인 조건은 **"사용자가 OK라고 입력했는가"**(spec-plan.md:53, 76-81)다. 그러나 가이드라인의
척추는 **"이해 못 하면 내가 한 일이 아니다"**. 즉 게이트가 *컴플라이언스*(승인 눌렀나)는 검사하지만
*이해도*(무엇을·왜 승인하나)는 검사하지 않는다. 여기가 최대 레버리지 지점이다.

메타 발견(표현형식 리서치 결론): **"문제는 포맷이 아니라 줄글이다. 해법의 90%는 새 툴이 아니라
에이전트가 마크다운을 쓰는 방식을 바꾸는 것이고 비용은 거의 0이다."** HTML은 장수 문서용 export 타깃으로만.

## 2. spec-plan / impl 의 역할 정의 (사이클 위에서)

```
기본니즈/문제정의 → PRD → TechSpec → 구현/테스트 → QA → Ship
   [사람]          [사람/PM]  [spec-plan]  [impl]      [impl+사람] [사람]
```

- **spec-plan = "PRD/티켓이라는 *의도*를 검증 가능한 *TechSpec*으로 번역하고, 사람의 승인으로 그 번역을
  확정하는 다리."** 코드는 한 줄도 안 씀. 본질은 *의도↔실행 사이의 이해·합의 게이트*.
- **impl = "확정된 TechSpec(plan.md)을 코드+테스트로 실현하고 quality gate로 1차 QA까지 미는 실행 엔진."**
  Ship 직전에서 멈춤(preamble rule 7 — 자동 commit/push 금지).

> [!NOTE]
> 통증의 구조적 원인: 이 워크플로우는 "문제정의·PRD는 이미 됐다"고 가정하고 **TechSpec부터** 시작한다.
> 그래서 출력이 *What/How*에 최적화되고 *Why/Problem*은 `user_prompt` 한 줄에만 남는다 →
> 카테고리 5(문제·의도 보존)의 근본 원인. → **Intent Header**로 구조적 처방.

## 3. 어려움 5 카테고리 → 해법

| # | 카테고리 | 증상 | 클래식 | 최신 |
|---|---|---|---|---|
| 1 | 언어·전문용어 | ad-hoc/stale/superseded, "first-fit greedy bin packing" | ASD-STE100 통제영어, Flesch-Kincaid, DDD Ubiquitous Language | LLM 자기-순화 패스(CLEF SimpleText) |
| 2 | 코드 스코프 | 어느 파일/클래스/부분이 어떻게 바뀌나 | `file:line` 규약, ctags/LSP | Mermaid classDiagram+`click`, C4, GitHub permalink |
| 3 | 도메인 어휘 | 로드맵 기능명 정확 인지 | Ubiquitous Language 용어집 | (1과 동일 메커니즘) |
| 4 | 표현 형식 | 줄글이라 안 읽힘 | BLUF/역피라미드, 표/체크리스트 | `<details>` 점진공개, `[!WARNING]`, Mermaid |
| 5 | 문제·의도 보존 | 무슨 문제·이름·왜 이 방향인지 증발 | PR/FAQ, Google RFC(Goals/Non-Goals + Alternatives), ADR | Shape Up Pitch(Appetite/No-gos), JTBD |

## 4. Friction Dial — 상시(light) vs 위험영역(heavy)

모든 이해 보조가 **"위험영역만 무겁게"** 다이얼에 둘로 갈린다.

| 강도 | 성격 | 항목 |
|---|---|---|
| **상시 (light)** | 쓰기 규율 | Intent Header · BLUF/표/체크리스트 · 용어집+인라인 풀이 · 구체 `file:line` 링크 · 관용구 자동 순화 · 자기-순화 패스 · **위험영역 회피 금지(`[!CAUTION]` 명시)** |
| **무겁게 (heavy)** | 상호작용 확인 | Mermaid 클래스/호출 다이어그램 + before/after diff · teach-back(스코프 본인 말로 재진술) · Ambiguity 항목별 read-back(sequential grill) · 사람이 쓴 설계노트 · analyzer/reviewer 항상 · 위험유형별 quality gate |

> [!IMPORTANT]
> **위험영역 *관리 방식*(태깅 메커니즘·teach-back·설계노트·heavy 처방)은 판단 보류(TBD).**
> 아래 정의/태깅은 참고안일 뿐 미확정. 단, 관리 방식과 **무관하게 지금 적용하는 상시 규칙 1건은 결정됨**(↓).

### 위험영역 회피 금지 (상시·결정됨)

> **AI는 자기가 실제로 건드리는 위험영역을 "범위 밖"으로 밀어낼 수 없다.**
> 건드리면 반드시 `[!CAUTION]`로 (a) 어느 영역을 건드리는지 (b) 무엇을 확인해야 하는지 명시한다.
> "범위 밖"은 *정말 안 닿을 때만*.

- **진짜 범위 밖** (정말 안 닿음, 예: 자동 판매) → `[!NOTE]` 경계 메모로 OK.
- **위험영역을 실제로 건드림** (변경이 그 경로와 상호작용) → `[!CAUTION]` "건드린다 + 확인할 것". **제외 불가.**
- 회피("범위 밖"으로 밀기)는 *부정직*이고, 권한/리플리케이션처럼 기능 필수 상호작용이면 *작동 불가*를 낳음.
- 근거: 가이드라인 §3 "AI가 자신 있게 틀리는 곳" — 무거운 다이얼 없이도 "조심해야 함"을 사람에게 전달하는 인지 바닥.

### 위험영역 정의 (가이드라인 §3) — *참고, 관리 방식 보류*

메모리(UPROPERTY/GC/포인터 수명) · 네트워크 리플리케이션(권한/조건/호출주체) · 동시성(GameThread vs 비동기)
· 아키텍처 결정(모듈 의존성/서브시스템) · 빌드/배포 파이프라인.

### 위험영역 태깅 = 하이브리드 (d) — *관리 방식, 보류(TBD)*

1. **CLAUDE.md `## Implementation Config`에 위험 경로/모듈 선언**(`risk_areas:`)을 baseline으로.
2. AI(Code Agent/reviewer)가 후보를 **추가 플래그**.
3. **사람은 위로(상향)만 쉽게**, 하향은 어렵게 → false-negative 쪽으로 안전하게 기움.

## 5. 이해(comprehension) = 2층 모델

| 층 | 확인 대상 | 언제 | 강도 |
|---|---|---|---|
| **Gate 0 align** | 문제 의도 일치 | 상시 (grill 스킵 여부 무관) | light |
| **위험영역 teach-back** | 기술 계획·스코프 이해 | Gate 2/3, 위험영역만 | heavy |

> **멀티턴.** Gate 0 align의 "한 문장"은 *시작 씨앗*이지 상한이 아니다. diff가 어긋남을 여러 건 띄우면
> 정렬을 **여러 턴** 이어가고, 복잡하면 grill로 자연 승격한다 — Gate 0 align과 grill은 *같은 one-at-a-time
> 엔진*이고 복잡도에 따라 가벼운 정렬 ↔ 본격 grill로 연속적으로 변한다.

> [!IMPORTANT]
> **grill 스킵 ≠ 인지 스킵.** pre-search grill은 *입력 품질* 장치이지 *인지 확인* 장치가 아니다.
> 트리거(prompt 명료도)는 prompt를 재지 사람의 이해를 재지 않는다. 인지 바닥(Gate 0 align)은
> 스킵과 독립적으로 무조건 작동한다.

## 6. grill 통합 지도 (어디에 박히나)

`/grill-with-docs`(Matt Pocock)는 별도 명령으로 얹지 않고 **두 알맹이만 흡수**: ① `CONTEXT.md` 용어집 포맷,
② grill 인터뷰 리추얼을 위험영역 heavy 경로에.

| 위치 | 무엇 | 강도 | 근거 |
|---|---|---|---|
| Pre-Gate 0 (조건부·희귀) | grill-me로 vague prompt 정련 → `refined_user_prompt` (**멀티턴 wave: 목표→edge→가정, 캡 있음**) | 트리거 발동 시만 | 입력 품질 ★★★★★ |
| Gate 0 (상시) | 한 문장 ↔ Step 0 findings align 대화 | light | 의도 일치 |
| Gate 2 ambiguities | 위험영역 항목만 sequential grill, 나머지 batch 표 | heavy(위험영역) | 다이얼 |
| /impl free-text (impl.md:79) | 약한 "bullet 확인"을 grill로 업그레이드 | 조건부 | 최약 지점 |
| 용어 등장 전역 | "충돌 즉시 지적 + canonical + CONTEXT.md 인라인" | light | grill-with-docs |

흐름:
```
1. ticket fetch + 입력 수집 (Jira / prompt / PRD)
1.5 준비도 점검 → 리포트 (필수 / 산출예정 / 이상)   ← 필수 빠짐→grill·정지, 이상→즉시 플래그
2. [조건부] Pre-search grill     ← prompt가 검색 불가할 만큼 모호 / --grill 일 때만 → refined_user_prompt
3. Step 0 (5-agent, refined로 검색)
4. Gate 0 align (상시)          ← "당신 문제 한 줄 ↔ 내가 찾은 것" diff + 짧은 대화
5. Gate 1/2/3 → Save
```

`refined_user_prompt`는 plan.md frontmatter `user_prompt`로, 다시 task 파일로 verbatim 전파(impl.md:118 규칙과 정합).

### 준비도 점검 (Readiness Check) — 맨 앞 진단 (상시·light)

일감을 받자마자, 일 시작 *전에* 최소 가이드라인이 갖춰졌는지·이상한 게 없는지 진단해 짧은 리포트로 뽑는다.
grill로 *고치기* 전에 빵꾸를 *발견*하는 단계 — 결과가 "grill 켤지 / 플래그하고 진행할지"를 라우팅한다.

3등급 분류 (전부 요구하지 않음 — 티켓 완벽 spec 요구는 도구를 짜증나게 함):
- **필수(must-have)** — 없으면 시작 불가: *무엇을 해달라는지(문제/요청)*. → pre-search grill 또는 정지.
- **산출예정(will-produce)** — 없어도 정상, spec-plan이 *만들 것*: 상세 방향성·세부 AC. → "이건 우리가 정함" 표시만.
- **이상/모순(odd)** — 즉시 사람에게: 설명↔AC 모순, 방향성이 컨벤션과 충돌, 범위가 appetite 대비 과도 등.

> 분별: "해결 방향성 없음"은 보통 *필수 아님*(spec-plan이 정하는 일). 단 *틀린/모순된* 방향성은 odd로 잡는다.

```
┌─ 준비도 점검 · OVDR-2231 ──────────────────────────┐
│ ✅ 문제 정의      티켓에 있음 ("인벤토리 꽉 차면 정리")
│ ⚠️ 해결 방향성    명시 안 됨 → spec-plan이 Gate 2에서 결정 (정상)
│ ✅ 성공 기준(AC)  티켓 AC 3건 있음
│ ❓ 이상           AC "안정 정렬"이 설명에 없음 — 의도된 추가 요구인가?
└────────────────────────────────────────────────────┘
```

`[!CAUTION]` 회피 금지가 **출력 쪽** 인지 바닥이라면, 준비도 점검은 **입력 쪽** 인지 바닥
(가이드라인 §2 "설계는 사람이 먼저"의 기계적 점검).

## 7. Artifact 결정 — 빈도 기반 분리

레포 원칙: **에이전트가 필터·ID인용하면 yaml, 사람이 읽고 인라인 편집하면 md.**
(근거: adr.yaml/conventions.yaml 헤더 "surface/cite entries **by ID**", design.md:30 "`stacks:` 태그 필터 ... 평문 fallback")

| 아티팩트 | 포맷 | 이유 | 위치 |
|---|---|---|---|
| 도메인 용어집 (`CONTEXT.md`) | **md** (신규) | 빈번·사람이 읽음·grill 인라인 append, ID 인용 불필요 | `glossary_path` (신규 config) |
| ADR (`adr.yaml`) | **yaml** (기존) | 드묾·에이전트가 `stacks:` 필터 + ID 인용 | `docs_path` (기존) |
| Intent Header | plan.md frontmatter + 본문 헤더 | 6필드, 타협불가 3 = Problem/Approach/Why | `.claude/plans/{T}/plan.md` |

> grill이 ADR을 만들 땐(hard-to-reverse 3조건일 때만) freeform이 아니라 **`adr.yaml` 엔트리로** append.
> 빈번한 용어는 md로 가볍게, 드문 결정은 yaml로 구조화.

## 8. IDE / 터미널 결정 (이기종 IDE: Rider · VS Code · Cursor · VS Pro)

- **기본 링크 = GitHub permalink** (`#L128-L140`, SHA 고정) — 4종 IDE 전원 동일 작동.
- **표시 텍스트 = `상대경로:라인`** — VS Code/Cursor/Rider 통합 터미널에서 마크업 0으로 Ctrl/Cmd-클릭 점프.
- **`editor://` 딥링크는 기본 채택 안 함** (4종 혼재 + OS 등록 필요, VS Pro는 깔끔한 스킴 없음). opt-in만.
- **터미널 추천(Windows)**: Windows Terminal(≥1.4, OSC 8) 기본 → 더 원하면 Warp / WezTerm.

## 9. 작업 분해 (Phase별)

> 규칙: 명령/에이전트 편집은 `claude-config/`에 하고, 후 `./deploy.sh` 안내(.claude/rules/claude-config.md).

### Phase 1 — 상시 쓰기 규율 (ROI 최고, 다이얼 무관) ★ 1순위
- [ ] **Intent Header** 도입 — `spec-plan.md` Step 4 plan.md frontmatter + Gate 1 상단 제시. 6필드, 타협불가 3.
- [ ] **출력 구조화** — `spec-plan.md` 게이트 출력 템플릿에 섹션별 BLUF(Bottom Line Up Front, 결론 먼저) 1줄, breaking change `[!WARNING]`, 깊은 근거 `<details>`, 작업분해 체크리스트.
- [ ] **구체 file:line** — Impact Scope(Gate 2)를 "the Weapon class"가 아니라 `Source/Combat/Weapon.cpp:128`(→GitHub permalink 마크다운 링크)로 강제.
- [ ] **위험영역 회피 금지 규칙** — `spec-plan.md`/`preamble.md`에 "실제로 건드리는 위험영역은 `[!CAUTION]`로 (영역+확인할 것) 명시, '범위 밖' 처리 금지" 규칙 추가 (§4 상시 결정 규칙).
- [ ] **준비도 점검(Readiness Check)** — `spec-plan.md` On activation 직후, 입력(티켓/prompt/PRD)을 최소 가이드라인 체크리스트에 대조해 3등급(필수/산출예정/이상) 리포트 출력. 필수 빠짐→grill·정지, 이상→즉시 플래그 (§6).
- 파일: `claude-config/commands/spec-plan.md`, `templates/workflow-contract/preamble.md`

### Phase 2 — 용어집 & 언어 순화
- [ ] **CONTEXT.md 포맷** + `glossary_path` config 추가. 스켈레톤: `templates/project-setup/docs/CONTEXT.md`.
- [ ] **부트스트랩 패스** — 코드/PRD에서 용어 후보 추출 → 사람 confirm(1회).
- [ ] **인라인 풀이 + 관용구 순화** 규칙 — `preamble.md` / spec-plan 프롬프트. CS 용어 첫 등장 시 한 줄 풀이, `stale→오래된` 등 순화 맵.
  - 풀이 범위 = **문서(plan.md) 단위 첫 등장 1회**(세션 단위 초기화 아님). 같은 문서 내 재등장은 생략, 문서가 바뀌면 다시 풀이. CONTEXT.md 등록어는 인라인 풀이 대신 **링크로 대체**.
- [ ] **자기-순화 패스** — 출력 직전 "비원어민 주니어로 다시 읽고 불명확 문장 재작성".
- 파일: `templates/workflow-contract/preamble.md`, `claude-config/commands/init-docs.md`, `templates/project-setup/`

### Phase 3 — grill 통합 (Gate 0 + free-text)
- [ ] **Gate 0 align** (상시·light) — 한 문장 ↔ Step 0 findings diff 대화. `spec-plan.md`.
- [ ] **Pre-search grill** (조건부) — prompt 모호/`--grill` 시 grill-me wave, ticket 슬롯 스킵 → `refined_user_prompt`.
- [ ] **/impl free-text 업그레이드** — impl.md:79 "bullet 확인"을 grill로.
- [ ] (선택) `references/`에 grill-with-docs 클론해 문구 정렬 (분석용, rules/references.md).
- 파일: `claude-config/commands/spec-plan.md`, `claude-config/commands/impl.md`

### Phase 4 — 위험영역 다이얼 (heavy 경로) — *보류(TBD)*

> 관리 방식 미정(태깅 메커니즘·heavy 처방). **단 "위험영역 회피 금지 + `[!CAUTION]` 명시"(§4)는 Phase 1에 포함되는
> 상시 규칙으로, 이 보류와 무관하게 먼저 적용된다.** 아래 항목은 관리 방식 확정 후 착수.

- [ ] **risk_areas 선언** — `CLAUDE-skeleton.md` `## Implementation Config`에 `risk_areas:` 추가.
- [ ] **태깅** — Code Agent/reviewer가 task/diff에 위험 태그, 사람 상향 가능.
- [ ] **heavy 처방 발동** — 위험 태그 시: teach-back + 사람 설계노트 + Gate 2 sequential grill + analyzer/reviewer 항상 + 위험유형별 quality gate.
- [ ] **Mermaid 다이어그램** — `analyzer.md`가 위험영역에서 닿는 클래스 classDiagram + before/after diff 출력.
- 파일: `claude-config/agents/analyzer.md`, `reviewer.md`, `templates/project-setup/CLAUDE-skeleton.md`, `quality-gates-*.md`

### Phase 5 — (선택) 보너스
- [ ] **debugger 게이트** — 가설 나열(2단계) 후 멈추고 사람이 가설 선택 (`debugger.md`).
- [ ] **PR 본문 스캐폴드** — AI 생성문 대신 "의도/리뷰포인트" 빈칸.
- [ ] **HTML export** — 장수 문서만 pandoc/MkDocs (매 PR 산출물엔 미적용).

## 10. 결정됨 / 보류

**결정됨 (이번 논의):**
- Gate 0 align ↔ grill = 같은 멀티턴 엔진. 한 문장은 씨앗, 복잡 시 grill로 승격. pre-search grill = 멀티턴 wave(캡).
- 인라인 풀이 = **문서 단위 첫 등장** + CONTEXT.md 영속/링크 (세션 초기화 아님).
- **위험영역 회피 금지 + `[!CAUTION]` 명시** (상시 규칙, Phase 1).
- **준비도 점검(Readiness Check)** = 맨 앞 입력 진단, 3등급(필수/산출예정/이상). 상시 규칙, Phase 1.
- 용어=md / ADR=yaml **빈도 기반 분리**.

**보류 (TBD):**
- 위험영역 *관리 방식* 전체 — 태깅 메커니즘 / teach-back / 설계노트 / heavy 다이얼 (Phase 4). 판단 보류.
- UE 코드베이스에서 ctags/LSP로 `file:line` 해석이 Rider/VS 환경에서 도는지.
