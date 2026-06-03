# Common Task Preamble

> Source of truth. Runner는 이 파일 본문을 task 본문 앞에 prepend한다.
> 정의 위치: `templates/workflow-contract/contract.md` §Common Preamble.

1. 작업 전에 task 파일과 §사전 준비에 명시된 모든 파일을 읽고 설계 의도를 이해하라.
2. 이전 task의 result 파일(`.claude/tasks/done/`)을 읽고 일관성을 유지하라.
3. task에 명시된 §Outputs(또는 §작업 내용에 적힌 파일) 외에는 수정·삭제하지 마라.
4. §Acceptance Criteria의 bash를 실제로 실행하고, 결과를 `.claude/runs/{TICKET}/test-output.log`에 append하라.
5. 실패한 테스트를 비활성화·skip·삭제하지 마라. 원인을 고치거나 result에 partial로 기록하라.
6. 모호한 결정은 result 파일 `<decisions>`에 한 줄로 기록하라.
7. 자동 commit / push / PR을 만들지 마라. 변경 후 `git status`만 보고하고 멈춘다 (commit은 사용자/orchestrator가 처리).
8. **위험영역 회피 금지**. 변경이 아래 baseline 5종 또는 plan.md `risk_areas:` 중 하나라도 *실제로 닿으면* result 본문 상단에 `[!CAUTION]` 박스로 (a) 어느 영역을 건드리는지 (b) 확인할 것 한 줄을 명시한다. "범위 밖" 처리는 *정말 안 닿을 때만*. 회피 금지.
   - **Baseline 5종 slug** (override 없으면 항상 적용):
     - `memory` — 수명·소유권·GC·UPROPERTY·포인터
     - `replication` — 네트워크 권한·조건·호출주체
     - `concurrency` — GameThread vs 비동기·락·인터리빙
     - `architecture` — 모듈 의존성·서브시스템 경계
     - `build-deploy` — 빌드·배포 파이프라인
   - plan.md `risk_areas:` 의 +α 도 같은 kebab slug 형식 (예: `auth-session`, `payment-flow`). baseline 5종과 중복 X — 그건 자동 적용.
   - ack 는 result frontmatter `risk_acks:` 슬롯에 한 줄 기록: `{area: <slug>, ack: confirmed|needs_check, ts: ...}`. `needs_check` 면 status 를 `partial` 로 내리고 사용자 확인을 기다린다.
9. **출력 직전 자기-순화 가이드** — 글로벌 한글 표기 룰 (모델 호출 0회). §8 박스 본문(영역명·확인 항목)은 본 룰의 적용 대상 아님 — 짧은 영어 keyword 보존이 가독성에 유리.

   **룰 1 — 한글표기 우선**: 영어 단어가 한국어 자연 대응어를 가지면 한글로 옮긴다.

   | 영어 원어 | 한글 표기 | 비고 |
   |---|---|---|
   | stale (오래된·낡은 데이터) | 오래된 | 예: "stale 캐시" → "오래된 캐시" |
   | ad-hoc (즉흥·임시) | 임시방편 | 예: "ad-hoc 수정" → "임시방편 수정" |
   | superseded (대체됨) | 폐기됨 | 예: "superseded 설정" → "폐기된 설정" |
   | idempotent (멱등성) | 멱등(idempotent) | 한글 단독 대응어 없음 → 괄호 병기 |
   | eventual consistency (최종 일관성) | 최종 일관성(eventual consistency) | 동일 |
   | deprecated (지원 중단) | 폐기(deprecated) | 동일 |
   | rollback (되돌리기) | 롤백 또는 되돌리기 | 문맥에 따라 선택 |

   **룰 2 — 주니어 가정**: CS/도메인 약어가 *본 출력 안에서 처음 등장*하면 한 줄 풀이를 함께 적는다. 같은 문서 내 재등장은 생략. 풀이 없는 영어 약어 단독 사용 금지.

   **룰 3 — 자연 한글 우선**: 한영 혼용(예: "이걸 deprecate 해야") 보다 한글 표기 + 괄호 영어(예: "이걸 폐기(deprecate) 해야")를 쓴다.

   **룰 4 — `idiom_candidates:` 슬롯 + idiom-pool 카운터 룰**: 위 1-3 규칙을 *어쩔 수 없이* 어겼을 때(자연 한글 대응어가 없거나 confidence가 낮을 때) result frontmatter `idiom_candidates:` 슬롯에 한 줄 append한다(`{term, ctx, ts}`). 동시에 `~/.claude/idiom-pool.yaml`의 해당 term 카운터를 +1한다(스키마는 task-9에서 정의 — 본 룰은 카운터 +1 지침만).

   **추가 룰 — 문장 길이·TBD 금지**: 한 문장이 ≥ 40 단어면 분리하거나 표/리스트로 재구성. "out of scope" / "not now" / "TBD" 단독 사용 금지 — 비용·위험·타이밍 중 하나의 근거를 붙인다.
