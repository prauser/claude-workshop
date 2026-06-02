---
title: 승인 게이트 이해도 강화 — 후속 결정 누적
created_at: 2026-05-29
status: planning-followup
parent: approval-clarity-plan.md
branch: claude/workflow-approval-clarity-m6oU9
---

# 승인 게이트 이해도 강화 — 후속 결정 누적

> 이 문서는 [[approval-clarity-plan]] 의 결정/보류 표에 대한 *2차 라운드 결정*을 담는다.
> 원 plan은 건드리지 않고 여기에 누적 → 다음 라운드에서 본 plan에 흡수.

## 1. 신규 결정 (이번 라운드)

### 1.1 효과 측정 — plan.md/task 안에 메타만 박는 식으로 시작

새 인프라(대시보드/DB) 짓지 않고, 기존 산출물에 **telemetry-friendly frontmatter 키** 추가.

```yaml
# plan.md frontmatter
gate_events:                       # 게이트별 결과 자동 기록 (사람 입력 X)
  - {gate: 0, result: ok, turns: 2, ts: 2026-05-29T10:00}
  - {gate: 2, result: revise, turns: 4, ts: ...}
intent_history:                    # Problem/Approach/Why 변경 이력 (append-only)
  - {ts: ..., field: approach, prev_sha: ..., reason: "..."}
risk_acks:                         # [!CAUTION] ack 결과 (Q3 결정)
  - {area: replication, ack: confirmed|needs_check, ts: ...}
```

```yaml
# task-N.yaml frontmatter
plan_sha: abc123                   # 이 task가 본 plan 버전
intent_problem: "..."              # Intent.Problem verbatim echo (Q5)
contributes_to: "..."              # spec-plan이 분해 시 자동 생성
plan_deviations:                   # impl 중 plan에 없는 결정 (Q2)
  - {ts: ..., note: "..."}
```

**잡히는 지표 (자동 집계 가능):**
1. Gate 0 align 평균 turns — 너무 낮으면 무름, 너무 높으면 입력 품질 문제
2. **Gate 1+ OK 이후 intent_history 변경률** ← 핵심 후행 신호 ("이해 못 하고 OK")
3. impl 중 plan_sha rebase 빈도 / plan_deviations 누적
4. risk_acks 중 `needs_check` 비율

### 1.2 임시 fallback — risk_areas baseline 하드코딩

`risk_areas:`가 plan별로 비어 있어도 가이드라인 §3 5종을 **spec-plan/preamble baseline**에 박는다.

- Baseline (하드코딩): 메모리 / 네트워크 리플리케이션 / 동시성 / 아키텍처 결정 / 빌드·배포
- Plan별 `risk_areas:`는 baseline에 **+α** (프로젝트 특수 영역만)
- AI가 baseline 5종 중 어디든 닿으면 `[!CAUTION]` 자동 발동

**근거**: plan에 "이번 작업 위험영역 X" 적어도 변경이 공유 라이브러리/글로벌 상태로 *닿을 수* 있음. 선언적 목록만으로는 부족.

### 1.3 위험영역 건드림 시 — 강제 롤백 아닌 ack 프로세스

3단계:

1. **인지** — `[!CAUTION]` 박스 명시 (어느 영역 / 무엇 확인할 것)
2. **확인** — 사람이 명시적으로 ack: `confirmed` / `needs_check` 둘 중 하나로만 답 가능 (자유 텍스트 X)
3. **기록** — `risk_acks:` 슬롯에 append → 측정/후행 추적

**강제 정지 X.** `needs_check`일 때만 게이트가 멈춤. 우회 비용을 *기록*으로 옮긴다.

### 1.4 Intent Header P/A/W 추상 레벨 = 기능 레벨

PRD 레벨 아님. spec-plan은 PRD를 *입력*으로 받아 *기능 한 건의* TechSpec을 만드는 단계.

```yaml
intent:
  problem: "<기능이 풀려는 사용자/시스템 문제 한 줄>"
  approach: "<이 기능을 어떻게 만들 것인가 — TechSpec BLUF>"
  why: "<왜 이 접근인가 — 기능 레벨 대안 대비 ADR-light>"
  prd_ref: "<PRD 링크>"            # PRD 레벨 P/A/W는 여기로
```

PRD 부실은 *준비도 점검*의 "이상" 등급으로 잡고, Intent Header가 PRD를 *대체*하지 않는다.

### 1.5 Verbatim Confirm — 새 입력 없음

준비도 점검이 받는 **문제 한 줄**(필수 입력)을 Intent.Problem에 **그대로 복사**.
AI 의역 금지, diff 감지 시 경고. impl.md:118 user_prompt verbatim 규칙과 동일 패턴.

→ 사람 추가 입력 0. 기존 입력의 *흐름*만 잠금.

### 1.6 impl ↔ plan 정합성

**Task 단위:**
- task 파일 생성 시 `intent_problem` verbatim echo + `contributes_to` 자동 생성 (Approach의 몇 단계인지)
- task 종료 시 self-check: "결과가 contributes_to를 만족하나" 한 줄 (Yes/No/Suspect)

**Reviewer 단계 (light):**
- diff ↔ task.contributes_to 정합성 1줄 판정 (Yes / No / Suspect)
- 위험영역 태그 있을 때만 Intent.Problem까지 거슬러 heavy 정합성 체크

**Plan 변경 감지:**
- impl 중 plan에 없는 결정 발생 → `plan_deviations:` append
- 누적 N개 초과 시 *plan으로 되돌려 갱신* 권유 (강제 X)

### 1.7 우회 패턴 처방

| 우회 | 처방 |
|---|---|
| 한 단어 OK ("ok", "go") | Gate 0만 허용. Gate 2/3는 "맞다 / 틀린 곳: …" 형태 필수, 한 단어 시 재질문 |
| AI 출력 복붙 OK | Intent.Problem verbatim 잠금 — AI가 재진술 시 diff 경고 |
| teach-back에서 plan 인용 | 자기 말로만, 인용 토큰 비율 휴리스틱 |
| risk 태그 하향 | 상향 쉽고 하향 어렵게 (§4) |
| --skip-grill 남용 | 스킵 카운터를 plan.md에 박고 PR 본문에 노출 (사회적 비용화) |

**원리**: 우회를 막을 수 없으면 *비싸게* 만든다 (강제 X, 기록 O). 측정(1.1)이 우회 처방의 *집행 도구*.

### 1.8 자기-순화 패스 — 휴리스틱 우선

별 에이전트 안 띄움. 라이트 2단계:

1. **휴리스틱** (모델 호출 0회): 문장 ≥40단어 경고 / 금칙어 사전(stale, idempotent 등 → 한 줄 풀이 누락 시 플래그) / Flesch-Kincaid 임계
2. **인라인 셀프 패스** (휴리스틱 부족 시): 메인 에이전트가 출력 직전 격리 프롬프트로 한 턴 ("비원어민 주니어 시점에서 막힌 곳만 표시")

휴리스틱 먼저, 효과 지표(1.1) 보고 부족하면 인라인 추가.

### 1.9 데이터 집계 경로 — 형식만 잠금, 인프라는 후속

3단계 점진:

| 단계 | 저장 | 모음 | 시점 |
|---|---|---|---|
| **L0 (지금)** | plan.md / task yaml frontmatter | 수동 (`glob \| yq`) | Phase 1과 함께 |
| **L1** | `~/.claude/telemetry/*.jsonl` | SessionEnd hook이 메타 append | 데이터 1-2개월 쌓인 후 |
| **L2** | 중앙 sink (sqlite/BQ/syncthing) | GitHub Action 또는 nightly ship | 팀 합의 + 프라이버시 정책 후 |

**지금 잠글 것**: L0 키 이름(`gate_events` / `intent_history` / `risk_acks` / `plan_sha` / `contributes_to` / `plan_deviations`) + **PII 분리 규칙** (메타는 frontmatter, 본문은 본문 — L2에서 메타만 ship).

**plan.md push 정책**: plan.md는 현재 `.gitignore`로 *로컬 작업물* 유지. 강제 push 안 함. 대신 두 채널로 흐름:
- **L1 hook**: SessionEnd hook이 로컬 plan.md frontmatter 메타만 읽어 `~/.claude/telemetry/*.jsonl`에 append. 본문은 안 나감.
- **PR 본문 주입**: `/commit-push-pr`이 Intent Header + gate 통계 요약만 PR description에 박음 (팀 가시성). plan.md 본문은 안 올라감.

### 1.9.1 메타 → 원본 plan/task 식별자

메타만으로는 *원인 가설*까지 못 감 — 사례 회고가 필요할 때 **메타에서 해당 plan/task를 찾아갈 수 있는 anchor**만 항상 같이 ship.

```yaml
# 메타 record 마다 anchor 포함
{repo: "...", plan_id: "OVDR-2231", plan_sha: "abc123", task_id: "task-3", ts: ...}
```

- `repo` + `plan_id` (= 티켓 ID 또는 plan 디렉토리명) + `plan_sha` 3개로 *내 로컬*에서 해당 plan.md 위치 가능
- task 단위 메타는 `task_id` 추가
- 본문은 안 나가도 *드릴다운 경로*는 열려 있음 — 비정상 수치 발견 시 본인이 자기 로컬에서 plan.md 열어 회고 가능

이걸로 *개인 개선 루프*는 닫힘. 조직 단위 코퍼스 분석(본문 기반)은 L2 진입 시 별도 결정.

## 2. 작업 방향 변경 영향 판단

| 질문 | 작업 방향 영향 | 후속 가능 여부 |
|---|---|---|
| Q1. align/grill 미이해 OK 잡힘 | 영향 X — 1.1 측정으로 *진단*만, 예방은 부분적이라는 한계 명시 | — |
| Q2. impl 중 plan 변경 가능? | **소폭 영향** — task yaml에 `plan_deviations:` 슬롯 추가 필요 (Phase 1 작업 범위 안) | — |
| Q3. baseline 하드코딩 + ack 프로세스 | **소폭 영향** — Phase 1에 baseline 5종 하드코딩 작업 추가 (원 plan §4와 정합) | — |
| Q4. P/A/W 추상 레벨 | 영향 X — Intent Header 정의 명료화만, 6필드 변화 없음 | — |
| Q5. task.contributes_to + reviewer 정합성 | **중간 영향** — Phase 1에 task 템플릿 키 추가, reviewer 1줄 정합성 판정 추가 (reviewer.md 편집) | — |
| Q6. 자기-순화 휴리스틱 우선 | 영향 X — Phase 2 처방 옵션을 휴리스틱 → 인라인 순으로 명시 | — |
| 데이터 집계 (이번 질문) | **영향 X** — L0 키 이름만 Phase 1에 잠그면 L1/L2는 비파괴적 후속 | ✅ 후속 |

**종합 판단**: 원 plan의 **방향은 변하지 않음**. 4개 항목이 Phase 1 *작업 범위에 슬롯 추가* 형태로 흡수됨 — 새 Phase 신설 불필요.

## 3. Phase 1 작업 항목 추가분 (원 plan §9에 흡수)

원 plan Phase 1 체크리스트에 다음만 추가:

- [ ] **Telemetry-friendly frontmatter 스키마** 정의 — plan.md/task yaml 키 이름 잠금 (1.1). L0 단계, 인프라 없음.
- [ ] **risk_areas baseline 하드코딩** — spec-plan/preamble에 §3 5종 박음 (1.2).
- [ ] **`[!CAUTION]` ack 프로세스** — `confirmed`/`needs_check` 응답 강제 + `risk_acks:` 기록 (1.3).
- [ ] **task 템플릿에 `intent_problem` verbatim + `contributes_to` 자동 생성** (1.6).
- [ ] **reviewer light 정합성 판정** — diff ↔ task.contributes_to Yes/No/Suspect 1줄 (1.6).
- [ ] **자기-순화 휴리스틱** — 문장 길이/금칙어/Flesch-Kincaid 임계, 모델 호출 0회 (1.8).
- [ ] **우회 패턴 가드** — 한 단어 OK 재질문, --skip-grill 카운터 PR 노출 (1.7).

## 4. 후속(별도 라운드 결정 필요)

- 데이터 집계 L1/L2 — 1-2개월 데이터 쌓인 후 SessionEnd hook 형태 결정
- 위험영역 *관리 방식* heavy 처방 (원 plan Phase 4) — 변경 없음, 여전히 TBD
- L2 진입 시 PII/프라이버시 정책 — 팀 합의 필요

## 5. 결정/보류 갱신

**이번 라운드 결정됨:**
- 효과 측정 = plan.md/task frontmatter 메타 키 (1.1)
- risk_areas baseline 하드코딩 = §3 5종 (1.2)
- 위험영역 건드림 시 = 인지 → ack(`confirmed`/`needs_check`) → 기록 (1.3)
- Intent Header P/A/W = 기능 레벨 (1.4)
- Verbatim Confirm = 준비도 점검 입력의 Intent.Problem 복사 (1.5)
- impl↔plan 정합성 = `contributes_to` + reviewer 1줄 판정 + `plan_deviations:` (1.6)
- 우회 패턴 = 강제 X, 기록 O — 측정과 짝 (1.7)
- 자기-순화 = 휴리스틱 우선 (1.8)
- 데이터 집계 = L0 형식만 잠금, L1/L2 후속 (1.9)

**여전히 보류:**
- 위험영역 heavy 처방 전체 (원 plan Phase 4) — teach-back / 사람 설계노트 / heavy quality gate
- 데이터 집계 L1/L2 인프라 — 데이터 누적 후
