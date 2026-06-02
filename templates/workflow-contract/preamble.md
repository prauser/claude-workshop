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
9. **출력 직전 자기-순화 휴리스틱** (모델 호출 0회):
   - 한 문장이 ≥ 40 단어면 분리하거나 표/리스트로 재구성.
   - 처음 등장하는 CS/도메인 약어(예: `stale`, `idempotent`, `eventual consistency`)는 한 줄 풀이를 함께 적는다. 같은 문서 내 재등장은 생략. CONTEXT.md 에 등록된 용어는 링크로 대체.
   - "out of scope" / "not now" / "TBD" 단독 사용 금지. 비용·위험·타이밍 중 하나의 근거를 붙인다.
