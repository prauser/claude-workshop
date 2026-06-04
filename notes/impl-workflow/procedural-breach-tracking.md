# 절차 위반 누적 트래킹 + 에스컬레이션 (follow-up 후보)

> 상태: idea / 미설계. WORKFLOW-GLOSSARY-P2 회고에서 도출.

## 문제

implementer / reviewer / integrator 가 *코드는 맞지만 절차/형식 룰* 을 어기는 케이스가 산발적으로 발생. 매번 reviewer 가 p2 로 잡아도 "이번 건은 코드 정확 → deferred" 로 흘러가서 *룰 자체* 가 강화되지 않음.

### 관찰된 위반 유형 (2026-06-04 시점)

| ID | 위반 | 빈도 (체감) | 현재 처리 |
|---|---|---|---|
| `auto-commit` | implementer 가 preamble §7 어기고 `git commit` 직접 실행 | 가끔 (task-4 발생) | reviewer p2 → orchestrator deferred. 다음 task 프롬프트에 "**git commit 금지**" 강조 문구 수동 추가 |
| `test-history-hidden` | result.md 가 AC retry 이력 (1차 FAIL → 수정 → 2차 PASS) 누락하고 "전부 PASS" 만 기록 | 가끔 (task-8 발생) | reviewer p2 → deferred. follow-up 없음 |
| `risk-ack-noise` | 실제 영향 없는데도 risk_acks 에 `confirmed` 적음 | 자주 (task-4, 그 외) | reviewer p4. 무시됨 |
| `pending-file-stale` | 성공한 task 파일이 `.claude/tasks/pending/` 에 그대로 남음 | 매번 | reviewer p3. 컨벤션 미정으로 처리 |

## 아이디어

각 위반 유형을 *카운터* 로 누적하고 임계 도달 시 *룰 SSOT 강화* 를 자동 권유. idiom-pool 패턴 (`~/.claude/idiom-pool.yaml` + `/idiom-review`) 의 재사용.

### 스키마 (초안)

```yaml
# ~/.claude/breach-pool.yaml
version: 1
entries:
  - id: auto-commit
    count: 3
    last_ctx: "task-4 WORKFLOW-GLOSSARY-P2 — 07c24d0 commit by implementer"
    first_seen: 2026-06-04T...
    last_seen: 2026-06-04T...
    status: open       # open | escalated | resolved
    rule_ref: "preamble.md §7"
  - id: test-history-hidden
    count: 1
    rule_ref: "result.schema.md (미정의 — 강화 후보)"
```

### 흐름

1. reviewer 가 p2 / p3 위반을 발견 → `<breach>` 태그로 위반 ID 명시 (`<breach id="auto-commit" task="task-4"/>`).
2. orchestrator 가 review 파일 파싱 → `~/.claude/breach-pool.yaml` 카운터 +1.
3. 임계값 (예: count ≥ 3) 도달 시 spec-plan/impl 시작 시 한 줄 알림:
   ```
   breach-pool: auto-commit ×3 임계 도달. /breach-review 권장 (룰 SSOT 강화 검토).
   ```
4. `/breach-review` 슬래시 커맨드:
   - 각 임계 항목에 대해 사용자에게 분기 제시:
     - **s** = SSOT 강화 (preamble / schema 본문 룰 추가) → patch draft 제시 → y/n
     - **t** = 검증 자동화 (예: pre-commit hook for auto-commit, AC 자동 history scan)
     - **a** = archive (룰 SSOT 는 충분, 위반은 인적 실수로 수용)
     - **k** = keep open (더 데이터 누적 필요)
5. 처리 후 entry archive 또는 reset.

## 위반 ID 분류 (초안)

| 카테고리 | 예 |
|---|---|
| **Process** | auto-commit, pending-file-stale, deploy.sh skip |
| **Audit** | test-history-hidden, risk-ack-noise, plan_deviations 미기록 |
| **Schema** | result frontmatter 필드 누락, runner alias 오용 (`claude-code` vs `in-session`) |
| **Scope** | task §Outputs 외 파일 수정, scope-lock 위반 |

## 미해결 / 결정 필요

- **임계값**: 일관성 위해 idiom-pool 과 같은 ≥3 사용? 아니면 위반 심각도별 차등 (process=3, audit=5, schema=2)?
- **자동화 vs 수동**: process 위반은 hook 으로 *차단* 가능 (예: `pre-commit` 이 `task_id` 파싱 → implementer 호출 차단). hook 까지 갈지, 알림만 할지.
- **수집 채널**: reviewer 가 `<breach>` 태그를 박는 강제 룰을 reviewer.md output schema 에 박을지, orchestrator 가 review 본문 휴리스틱 파싱할지.
- **plan.md 와의 관계**: plan §Risks 의 `R-...` 와 별개 채널인지, 통합 인지. (현재로선 별개 — Risks 는 *plan 시점 예측*, breach 는 *runtime 관찰*).

## 참조

- idiom-pool 패턴: `claude-config/commands/idiom-review.md`, `templates/workflow-contract/preamble.md` §9 룰 4
- approval-clarity Phase 1 (telemetry baseline): `notes/impl-workflow/approval-clarity-plan.md`
- WORKFLOW-GLOSSARY-P2 회고 (test-history-hidden, auto-commit 실제 발생): commit 07c24d0, `.claude/tasks/done/task-4-config-infrastructure-review.md`, `.claude/tasks/done/task-8-l2b-self-pass-review.md`
