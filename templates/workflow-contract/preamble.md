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
