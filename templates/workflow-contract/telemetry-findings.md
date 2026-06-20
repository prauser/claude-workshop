# Telemetry Findings 해석 문서

> **역할**: 이 문서는 `claude-workshop`이 소유하는 SSOT(Single Source of Truth)다. 번들 스키마 필드가 어떤 finding으로 해석되는지를 정의하며, `agentlens`(Phase B)가 이 문서를 vendoring해 finding 계산 계약으로 삼는다.
>
> **번들 스키마 버전**: `BUNDLE_SCHEMA_VERSION = "1.0"` (`templates/workflow-contract/runners/telemetry/bundle.py` SSOT)
>
> **vendoring 경로**: `deploy.sh`가 `templates/workflow-contract/` 트리 전체를 `~/.claude/templates/workflow-contract/`로 동기화한다. `agentlens`는 이 파일을 `~/.claude/templates/workflow-contract/telemetry-findings.md` 경로로 읽는다. (`sync-workflow.sh`는 현재 미존재 — `deploy.sh`가 실제 동기화 수단임.)
>
> **deidentification 경계**: 이 문서에 raw 유저 입력 원문을 포함하지 않는다. 예시는 추상화된 특성 형태(예: "질문형 단문 2건")로만 기술한다.

---

## 목차

1. [3목표 Finding 카탈로그](#3목표-finding-카탈로그)
   - [#1 에이전트 비효율](#1-에이전트-비효율)
   - [#2 사용자 행동](#2-사용자-행동)
   - [#3 입력 품질](#3-입력-품질)
2. [필드→Finding 매핑 표](#필드finding-매핑-표)
3. [저표본(low-sample) 규약](#저표본low-sample-규약)
4. [evidence_ref 규약](#evidence_ref-규약)
5. [버전·드리프트 처리 방향](#버전드리프트-처리-방향)
6. [Open Questions — Placeholder + 권고](#open-questions--placeholder--권고)

---

## 3목표 Finding 카탈로그

### #1 에이전트 비효율

**목표**: 세션 이벤트 스트림에서 에이전트(agent) 도구 사용의 낭비·반복 패턴을 탐지한다.

**계산 위치**: `agentlens` (번들 평문 이벤트 스트림에서 직접 계산)

#### 재사용 Detector

`agentlens.analyze.detect_tool_inefficiency`(`analyze.py:179`)를 평문 이벤트 스트림에 어댑트해 사용한다.
원본 detector는 `SessionDetail`(파싱된 객체)을 입력으로 받는다.
번들 이벤트 스트림은 평문 텍스트이므로 어댑터 레이어가 필요하다.

| 원본 패턴 | 번들 이벤트 스트림 어댑트 방법 |
|---|---|
| `repeated-read`: 동일 파일을 중간 Edit 없이 3회 이상 Read | 이벤트 스트림에서 `tool_name=Read, file_path=X` 이벤트를 순서대로 추출. 중간 `tool_name=Edit, file_path=X` 부재 조건으로 카운트. |
| `edit-retry`: Edit 연속 실패 2회 이상 후 성공 | 이벤트 스트림에서 `tool_name=Edit, is_error=True`가 연속 2건 이상 발생 후 `is_error=False`로 전환된 패턴 탐지. |
| `search-then-discard`: 동일 조건 검색(Grep/Glob) 재실행 | 이벤트 스트림에서 연속된 Grep/Glob 이벤트가 동일 path·pattern을 가지는 경우 탐지. refinement(경로·패턴 변경)는 정상으로 간주. |

어댑트 시 주의: `extract_workflow_segments`(`analyze.py:95`)와 `_extract_ticket`(`analyze.py:57`)도 재사용 가능하다.
이벤트 스트림의 ticket 복원은 `plan.intent` 또는 `sessions[].session_id`의 slug로 수행한다.

#### Finding 필드

```
kind:       "tool-inefficiency"
pattern:    "repeated-read" | "edit-retry" | "search-then-discard"
source:     "session"
ticket:     <티켓 ID>
session_id: <세션 ID>
n:          <해당 finding이 관찰된 세션 수 (저표본 규약 적용)>
waste_tokens: <추정 낭비 토큰>   # repeated-read에서만 유효
confidence: "high" | "low"
evidence_ref: <로컬 세션 포인터>
```

---

### #2 사용자 행동

**목표**: 사용자가 워크플로 품질 게이트(gate)를 어떻게 처리하는지 — 형식적 승인·우회·이해 부족 — 를 측정한다.

**A4 경계 (동결 결정)**: raw 의존 finding은 `collector`가 신호를 제공하고, 평문(plaintext) derivable finding은 `agentlens`가 계산한다.

#### Finding 목록

| Finding ID | 설명 | 입력 필드 | 계산 위치 |
|---|---|---|---|
| `rubber-stamp` | 게이트 승인 시 유저 검토 없이 0~1턴만에 통과 | `plan.gate_events[].turns` | **agentlens** |
| `bypass` | `readiness_flags`에 resolution 없는 채로 진행 | `plan.readiness_flags[].resolution` (빈 문자열 또는 누락) | **agentlens** |
| `skip` | `skip_presearch` 또는 `skip_gate2`가 1(비-0) | `plan.skip_presearch`, `plan.skip_gate2` | **agentlens** |
| `drift` | `intent_history_len > 0` (문제 정의 재정의 발생) | `plan.intent_history_len` | **agentlens** |
| `ceremonial` | 게이트 이벤트가 형식적 통과 패턴임을 의미하는 원시 신호 | raw 세션 콘텐츠 의존 | **collector 신호 제공** |
| `gate2-comprehension` | Gate 2 이해 미달 (이해도 검증 실패 패턴) | raw 세션 콘텐츠 의존 | **collector 신호 제공** |

**`ceremonial`·`gate2-comprehension` 처리**: 이 두 finding은 raw 세션 텍스트에 의존하므로, `collector`가 번들에 집계 신호(예: `plan.gate_events[].self_pass`, `plan.gate_events[].turns`)를 포함하고, `agentlens`는 이 신호를 조합해 간접 추정한다. raw 콘텐츠 자체는 번들에 포함되지 않는다.

#### Finding 필드 (`rubber-stamp` 예시)

```
kind:       "user-behavior"
pattern:    "rubber-stamp" | "bypass" | "skip" | "drift" | "ceremonial" | "gate2-comprehension"
source:     "bundle"
ticket:     <티켓 ID>
gate:       <0|1|2|3>     # gate_events 기반
turns:      <승인 턴 수>  # rubber-stamp: 0 또는 1
n:          <해당 패턴이 관찰된 티켓 수 (저표본 규약 적용)>
confidence: "high" | "medium" | "low"
evidence_ref: <로컬 아티팩트 포인터>
```

#### 임계 후보 (Phase B 데이터 축적 후 확정 예정)

- `rubber-stamp`: `plan.gate_events[].turns <= 1` — 임계값 tunable
- `skip`: `plan.skip_presearch == 1` OR `plan.skip_gate2 == 1`
- `drift`: `plan.intent_history_len >= 1`
- `bypass`: `len([f for f in plan.readiness_flags if not f.get("resolution")]) > 0`

---

### #3 입력 품질

**목표**: spec-plan 입력 단계에서 준비도(readiness)·설정(config) 결손·스키마 드리프트를 감지한다.

**계산 위치**: `agentlens` (번들 필드에서 직접 계산)

#### Finding 목록

| Finding ID | 설명 | 입력 필드 | 신호 종류 |
|---|---|---|---|
| `readiness-anomaly` | `readiness_flags`에 진단형(미해결) 항목 존재 | `plan.readiness_flags[].resolution` 부재 또는 빈값 | 구조화 메트릭 |
| `config-gap` | 필수 번들 필드 누락 또는 기본값 잔존 | `plan.*`, `manifest.*`, `tasks[].*` 필수 키 부재 | 스키마 검증 |
| `schema-drift` | `plan_sha` 변경 빈도 증가 (문제 정의 불안정) | `plan.plan_sha` 변경 이력 + `intent_history_len` | 추세 스토어 |
| `legacy-skip-grill` | 구식(legacy) `skip_grill_count` 필드 출현 | `plan.skip_grill_count` 필드 존재 여부 | 필드 존재 확인 |
| `ticket-fetch-failure` | Jira/Linear 티켓 fetch 실패 | `parse_errors[]` 에서 ticket-fetch 오류 패턴 | 파싱 오류 |

#### Finding 필드 (`readiness-anomaly` 예시)

```
kind:          "input-quality"
pattern:       "readiness-anomaly" | "config-gap" | "schema-drift" | "legacy-skip-grill" | "ticket-fetch-failure"
source:        "bundle"
ticket:        <티켓 ID>
n:             <해당 패턴이 관찰된 티켓 수 (저표본 규약 적용)>
flag_count:    <진단형 readiness_flags 개수>
confidence:    "high"
evidence_ref:  <로컬 아티팩트 포인터>
```

---

## 필드→Finding 매핑 표

> 모든 finding의 `n`은 저표본 규약(아래 §저표본 규약)에 따라 표시한다.

| 번들 필드 | 목표 | Finding | 계산 위치 | 임계 후보 |
|---|---|---|---|---|
| `sessions[].events` (평문 이벤트 스트림) | #1 에이전트 비효율 | `repeated-read`, `edit-retry`, `search-then-discard` | agentlens (`detect_tool_inefficiency` 어댑트) | read ≥ 3회 / edit 실패 연속 ≥ 2회 |
| `plan.gate_events[].turns` | #2 사용자 행동 | `rubber-stamp` | agentlens | turns ≤ 1 (tunable) |
| `plan.gate_events[].self_pass` | #2 사용자 행동 | `ceremonial` (간접 신호) | collector 신호 → agentlens 추정 | self_pass=true 비율 (tunable) |
| `plan.readiness_flags[].resolution` | #2 사용자 행동, #3 입력 품질 | `bypass`, `readiness-anomaly` | agentlens | resolution 부재 또는 빈값 |
| `plan.skip_presearch` | #2 사용자 행동 | `skip` | agentlens | 값 = 1 |
| `plan.skip_gate2` | #2 사용자 행동 | `skip` | agentlens | 값 = 1 |
| `plan.intent_history_len` | #2 사용자 행동, #3 입력 품질 | `drift`, `schema-drift` | agentlens | ≥ 1 (tunable) |
| `plan.plan_sha` | #3 입력 품질 | `schema-drift` (추세 스토어 비교) | agentlens (추세 스토어) | 변경 횟수 ≥ 2 (tunable) |
| `plan.risk_acks[].ack` | #3 입력 품질 | `config-gap` | agentlens | `needs_check` 잔존 |
| `manifest.status` | #3 입력 품질 | `config-gap` | agentlens | `partial` 또는 누락 |
| `tasks[].plan_deviations` | #1, #3 | `drift`, `config-gap` | agentlens | ≥ 3 (P0 기준) |
| `parse_errors[]` | #3 입력 품질 | `ticket-fetch-failure` | agentlens | 1건 이상 |
| `user_input_characteristics` | #2, #3 | (T4 추상화 산출 — 구조 미확정) | agentlens | 별도 설계 |
| `evidence_ref` | 모든 목표 | Tier-2 드릴다운 | agentlens (로컬 포인터 resolve) | 로컬 존재 여부 |
| `plan.skip_grill_count` (legacy) | #3 입력 품질 | `legacy-skip-grill` | agentlens | 필드 존재 시 |

---

## 저표본(low-sample) 규약

모든 finding은 관찰 표본 수 `n`을 함께 표시한다. 표본이 충분하지 않을 때 finding을 억제하거나 silent truncation(무음 잘라내기)하지 않는다.

### 규칙

1. **`n` 표기 필수**: finding 출력 시 반드시 `n=<표본 수>`를 포함한다.
2. **`n < 임계값` → 회색 표시**: 기본 임계값 `n_min = 3` (tunable). 임계 미만 finding은 "데이터 부족(low-confidence)" 상태로 표시하되 삭제하지 않는다.
3. **silent truncation 금지**: 표본 부족을 이유로 finding을 출력에서 제외하거나 0으로 대체하지 않는다. 부족 상태를 명시적으로 노출한다.
4. **임계값 tunable**: `n_min`은 하드코딩하지 않는다. Phase B 데이터 축적 후 조정 예정 (§Open Questions 참조).

### 표시 예시 (추상화)

```json
{
  "finding": "rubber-stamp",
  "n": 2,
  "low_sample": true,
  "note": "n=2 < n_min=3: 데이터 부족, 참고용"
}
```

---

## evidence_ref 규약

번들의 `evidence_ref` 필드는 Tier-2 드릴다운을 위한 로컬 포인터를 담는다. 원격에서는 resolve되지 않는다.

### 필드 구조

```json
"evidence_ref": {
  "session_paths": ["<세션 ID 또는 로컬 세션 파일 경로>"],
  "artifact_paths": ["<plan.md 로컬 경로>", "<task-N-result.md 로컬 경로>", "..."]
}
```

### Tier 정의

| Tier | 데이터 범위 | resolve 위치 |
|---|---|---|
| Tier-1 | 번들만 (메트릭 + 평문 이벤트 + 추상화 특성) | 원격 가능 (공유 git repo) |
| Tier-2 | `evidence_ref`가 가리키는 로컬 raw 산출물 | 로컬만 (raw 머신 밖 금지) |

### 사용 규칙

- `session_paths`: `sessions[].session_id` 기준. agentlens는 이 ID로 로컬 세션 파일을 resolve해 raw 이벤트 드릴다운을 제공한다.
- `artifact_paths`: plan.md, task-N-result.md, manifest.yaml 로컬 경로. agentlens는 로컬에 해당 파일이 있을 때만 Tier-2 뷰를 활성화한다. 원격 머신에서는 비활성(무crash).
- **원격 미해결**: `evidence_ref` 포인터는 번들에 포함돼 업로드되지만, 원격 agentlens는 포인터만 저장하고 파일을 fetch하지 않는다. 프라이버시 경계 유지.

---

## 버전·드리프트 처리 방향

> **대상 task**: Phase B T7(번들 ingest + 스키마 검증)에서 구현한다.

번들의 `bundle_schema_version`이 agentlens의 기대 버전과 다를 때의 처리 방향:

### version-mismatch 시나리오

| 시나리오 | 처리 방향 |
|---|---|
| `bundle_schema_version == "1.0"` (현재 계약 버전) | 정상 ingest |
| `bundle_schema_version`이 기대 버전보다 낮음 (구버전 번들) | `parse_errors`에 version-mismatch 레코드 추가. 가능한 필드는 방어적 파싱(field-presence)으로 수집. finding 계산 시 `low_confidence=true` 플래그. |
| `bundle_schema_version`이 기대 버전보다 높음 (신버전 번들) | 경고 로그 후 알려진 필드만 추출. 미지 필드는 무시. hard-fail 금지. |
| `bundle_schema_version` 필드 자체 누락 | `validate_bundle()` 실패 → `parse_errors` 기록. finding 계산 스킵(skip). |

### T7 구현 지침

- `bundle.validate_bundle()` (`bundle.py`)을 vendoring해 동일한 검증을 실행한다.
- version-mismatch는 hard-fail이 아니라 degraded-mode로 처리한다. 완전히 거부하면 구버전 번들 분석 기회를 잃는다.
- 추세 스토어(T8)에 version 필드를 키로 포함시켜, 버전별 추세를 분리 추적할 수 있게 한다.

---

## Open Questions — Placeholder + 권고

> 아래 항목은 결정이 아닌 placeholder다. Phase B 데이터 축적 후 실측 기반으로 확정한다. 지금 확정하면 데이터 없는 임의 튜닝이 된다 (타이밍 근거: 실코퍼스 n이 n_min을 넘기기 전).

### OQ-1 Finding Severity 루브릭

**현황**: finding의 중요도(critical/important/suggestion)를 어떤 기준으로 분류할지 미정.

**권고**: Phase B T9(finding 발견) 구현 시, agentlens 기존 `Finding.confidence`("high"/"low") 필드를 출발점으로 삼는다. severity 루브릭은 실 finding 분포 확인 후 별도 설계한다.

### OQ-2 저표본 임계값(n_min)

**현황**: `n < 3` 회색 처리를 예시로 제시했으나 3은 임의값.

**권고**: 첫 10개 티켓 번들 ingest 후 finding 분포를 보고 결정한다. 3을 초기값으로 사용하되 설정값(config value)으로 외부화한다.

### OQ-3 `intent.*` 평문 여부

**현황**: `plan.intent` (problem/approach/why)는 spec-plan이 생성한 AI 의역 내러티브이며 유저 raw NL이 아니다.
`bundle.py`의 `intent.*` 평문 처리 및 `plaintext_subtrees` 제외 결정은 T5에서 동결됐다.

**권고**: 현재 결정(평문 유지)을 Phase B에도 그대로 적용한다. `agentlens`에서 intent 필드를 분석에 활용할 경우 `plaintext_subtrees=["tickets.plan.intent"]` 예외 처리를 유지한다. 재논의 트리거: intent 필드가 예상치 못한 식별 정보를 포함하는 사례 발견 시.
