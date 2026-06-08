# Gate Escalation SSOT — stuck / skip / comprehension-miss

> 공유 SSOT(단일 진실 공급원). `spec-plan.md` 가 인용한다.
> 배포 위치: `templates/workflow-contract/gate-escalation.md` → `~/.claude/templates/workflow-contract/gate-escalation.md` (deploy.sh 경유).
>
> **[!CAUTION] 위험영역: `architecture`** — 이 파일이 없으면 호출자(spec-plan)는 "sync-workflow.sh / deploy.sh 미실행" 경고를 출력하고 해당 분기를 중단한다.
> **경로 해석**: `.claude/templates/workflow-contract/gate-escalation.md` → cwd `./templates/workflow-contract/gate-escalation.md` → `~/.claude/templates/workflow-contract/gate-escalation.md` 순으로 처음 존재하는 것 사용 (`impl.md` §Template path resolution 동형).

이 파일은 **게이트가 정상 수렴하지 않을 때만** 타는 조건부 기계장치를 모은다. 정상 흐름(Gate 2 sequential 휴리스틱 · Turn 1-4 · 옵션 선택)은 spec-plan.md 본문에 남아 있다.

3개 진입점:
1. **Gate 2 stuck** — Ambiguity 결정이 5턴 넘게 안 잡힐 때 (§1)
2. **SKIP** — 사용자가 Ambiguity를 건너뛸 때 (§2)
3. **Spec Preview miss** — 이해 프로브 답이 어긋날 때 (§3)

---

## 1. Gate 2 stuck detection — Turn 5 힌트 + turn 6+ 형식 강제

> **진입**: Gate 2 Ambiguity 결정의 `turns` 가 5에 도달.
> 정상 게이트(Turn 1-4)는 spec-plan.md §Gate 2 stuck detection 에 남아 있다.

### Turn 5 — Stuck 진단 + bi-directional check

`turns` 가 5 에 도달하면 AI 가 자기 이해를 박스로 노출:

```
> [!NOTE] Gate {N} 진행 5턴 도달 — Stuck 진단
> - 지금까지 이해한 것 (AI 시점): {합의됐다고 본 결정 한 줄}
> - 막힌 곳: {어떤 결정 / 정보가 안 잡혔나}
> - 필요한 입력: {사용자가 어떤 형태로 답하면 풀리나 — 예시 응답 포함}
>
> 위 "지금까지 이해한 것" 이 사용자 의도와 일치합니까?
> 일치하지 않는 부분 먼저 지적해주세요 (그 후 옵션 선택).
```

→ bi-directional check: AI 가 잘못 이해한 채 옵션만 정하는 걸 막음. 사용자가 "그게 아니라 X 야" 라고 정정하면 정상 응답 (turn 6 으로 카운트, plan 재정렬).

### Turn 6+ — 응답 형식 강제

힌트 직후 응답은 *셋 중 하나* 형태여야 통과:

| 형태 | 예시 | 의미 |
|---|---|---|
| (a) 힌트의 "필요한 입력" 옵션 선택 | "GET 만 abort" (박스의 옵션 그대로) | AI 분류에 동의 |
| (b) 제3안 + 이유 | "둘 다 keep, 이유: 부분 abort 가 더 위험" | AI 분류 거부 + 사용자 판단 |
| (c) 메타 액션 | "정지" / "skip" / "분석 더" | 의사결정 보류 명시 |
| (d) AI 이해 정정 | "지금까지 이해한 것이 틀림 — 실제로는 X" | bi-directional check 응답 |

어디에도 안 맞으면 (예: "OK" / "마음대로 해줘") 재질문.

### Turn 7+ — 최종 분기

힌트 + 형식 강제 후에도 막히면 사용자에게 명시 분기 질문:
- **정지** → Gate 2 미완 상태로 종료. plan 저장 안 함.
- **계속** → 한 번 더 시도 (turn 카운터 계속).
- **skip** → 해당 Ambiguity SKIP 처리 (§2 참조).

---

## 2. SKIP behavior

> **진입**: 사용자가 Gate 2 의 Ambiguity 에 대해 SKIP 을 선택 (Turn 7+ 분기 또는 명시 `--skip-grill` / "건너뛰기").

1. **분류 변경** — 해당 항목을 Ambiguities → Open Questions 로 강등. plan.md 의 해당 섹션에서 이동.
2. **task 분해 영향 검증** — AI 가 SKIP 직전 검증:
   > "이 Ambiguity 는 Task {N} 분해에 *영향* — SKIP 시 {구체 항목}이 미정 상태로 implementer 에게 위임됨. 진짜 SKIP 하시겠습니까?"
   - 영향 없음 → 즉시 SKIP 처리
   - 영향 있음 → 사용자가 "응" 응답 필요. "아 그럼 결정" 응답 시 Ambiguity 로 복귀
3. **카운터 +1** — `skip_gate2` 1 증가. PR 본문 주입 시 노출.
4. **Open Question 마킹** — Open Questions 항목 끝에 `(skipped from Ambiguity #{N} at gate-2 turn {T})` 표시.

implementer 가 SKIP 된 Open Question 을 만나면 자기 판단으로 결정하고 result `<decisions>` 에 한 줄 기록 — 일반 Open Question 처리 흐름과 동일.

---

## 3. Spec Preview miss 플로우

> **진입**: Spec Preview 단일 프로브(§spec-plan.md §Spec Preview) 답이 어긋남. 2회에서 끊고 계측.

0. **정체 먼저 분기** (teach로 점프 금지): "어긋나는데 — 내 *계획이 틀린* 거야, *이해가 안 맞은* 거야?"
   - 계획 틀림 → 해당 Ambiguity/Impact Scope로 revise (프로브가 plan 결함을 잡은 것). `gate_events` result: `revised-plan`.
   - 이해 miss → 아래 사다리.
1. **1차 — align-hint**: 정답 말고 *포인터*만. "힌트: race는 Task Breakdown 어디에도 안 들어가 있어 — 안일까 밖일까?" 답 미노출이라 같은 인스턴스 재질문 OK.
2. **2차 — teach + rotate**: 개념 설명(답 노출됨) + **새 인스턴스/형태로 재테스트**(같은 문항 재사용 금지 — 복사 방지). recognition 프로브는 엣지케이스 무한 공급이라 인스턴스 교체가 쉽다.
3. **3차 — 그만 갈고 명시 분기** (무한 align 금지):
   - **진행+플래그**: `readiness_flags += {flag: gate2-comprehension-incomplete, detail, resolution: "", ts}`. `gate_events` result: `proceed-flagged`.
   - **정지**: plan 미저장 종료.
   - **impl 위임**: 해당 결정 → Open Question 강등, implementer가 `<decisions>`에 기록 (§2 SKIP behavior 동형).

> **2회에서 끊는 이유**: 이해 align을 3턴 넘게 가는 것 자체가 신호다(계획이 불명확하거나 사용자 checked-out) → 그라인딩이 아니라 사람이 분기 결정.
> **재시도 카운트**: step 1 = 1차, step 2 = 2차. step 0의 정체 판단은 재시도 카운트에 포함하지 않는다.

---

## 4. 상호 참조

| 파일 | 관계 |
|---|---|
| `claude-config/commands/spec-plan.md` | 본 SSOT 호출자 — Gate 2 stuck(§1) · SKIP(§2) · Spec Preview miss(§3) 진입점 |
| `templates/workflow-contract/grill.md` | 동일 계층 SSOT — Ambiguity grill mode(sequential). stuck/skip 는 grill 수렴 실패 이후 경로 |
| `templates/workflow-contract/preamble.md` | 공통 preamble SSOT — §8 위험영역 |
