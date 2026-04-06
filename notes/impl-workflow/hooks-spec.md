# Hook 스크립트 스펙

> 상위 문서: [design.md](design.md)
> 배포 위치: 각 프로젝트 레포의 `.claude/hooks/`

## 설계 원칙

```
1. 에이전트는 구현에 집중, 로깅은 Hook이 담당
2. Hook은 자동 — 에이전트가 깜빡해도 실행됨
3. 품질 게이트는 건너뛸 수 없음
4. orchestrate.md 수정 없이 로깅 추가/변경 가능
```

---

## settings.json 구조

```jsonc
// {repo}/.claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": { "tool": "Agent" },
        "command": "bash .claude/hooks/log-agent-usage.sh"
      },
      {
        "matcher": { "tool": ["Edit", "Write"] },
        "command": "bash .claude/hooks/log-file-change.sh"
      },
      {
        "matcher": { "tool": ["Edit", "Write"] },
        "command": "bash .claude/hooks/run-related-tests.sh"
      }
    ],
    "PreToolUse": [
      {
        "matcher": { "tool": "Bash", "command_pattern": "git commit" },
        "command": "bash .claude/hooks/pre-commit-lint.sh"
      }
    ]
  }
}
```

> 주의: matcher 문법과 환경변수는 Claude Code 버전에 따라 다를 수 있음.
> experiments/ 단계에서 실제 동작 검증 필수.

---

## Hook 스크립트 상세

### log-agent-usage.sh — 에이전트 토큰 기록

```bash
#!/bin/bash
# PostToolUse(Agent) 시 실행
# Agent 호출의 토큰 사용량을 metrics.jsonl에 기록

# TODO: Claude Code가 Hook에 전달하는 환경변수 확인 필요
# 예상: $TOOL_NAME, $TOOL_RESULT 또는 stdin으로 전달

TICKET_FILE=".claude/current-ticket"
TICKET=$(cat "$TICKET_FILE" 2>/dev/null || echo "unknown")
LOG_REPO=$(grep -A1 "log_repo" CLAUDE.md 2>/dev/null | tail -1 | tr -d '| ' || echo "../impl-logs")
REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" || echo "unknown")

LOG_DIR="${LOG_REPO}/${REPO_NAME}/${TICKET}"
mkdir -p "$LOG_DIR"

# usage 데이터 파싱 후 append
# 실제 구현은 experiments 단계에서 Hook 환경변수 확인 후 결정
echo "{\"ts\":\"$(date -Iseconds)\",\"type\":\"agent\",\"ticket\":\"${TICKET}\"}" \
  >> "$LOG_DIR/metrics.jsonl"
```

### log-file-change.sh — 코드 변경 기록

```bash
#!/bin/bash
# PostToolUse(Edit/Write) 시 실행
# 어떤 파일이 변경되었는지 changes.jsonl에 기록

# TODO: $FILE 환경변수 전달 방식 확인 필요

TICKET_FILE=".claude/current-ticket"
TICKET=$(cat "$TICKET_FILE" 2>/dev/null || echo "unknown")
LOG_REPO=$(grep -A1 "log_repo" CLAUDE.md 2>/dev/null | tail -1 | tr -d '| ' || echo "../impl-logs")
REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" || echo "unknown")

LOG_DIR="${LOG_REPO}/${REPO_NAME}/${TICKET}"
mkdir -p "$LOG_DIR"

echo "{\"ts\":\"$(date -Iseconds)\",\"type\":\"file_change\",\"ticket\":\"${TICKET}\"}" \
  >> "$LOG_DIR/changes.jsonl"
```

### run-related-tests.sh — 편집 후 관련 테스트 실행

```bash
#!/bin/bash
# PostToolUse(Edit/Write) 시 실행
# 변경된 파일과 관련된 테스트를 자동 실행

# TODO: 프로젝트별 테스트 명령은 CLAUDE.md Implementation Config에서 읽기
# TODO: "관련 테스트" 판별 로직 (파일명 기반, 디렉토리 기반 등)

TEST_CMD=$(grep -A1 "test_command" CLAUDE.md 2>/dev/null | tail -1 | tr -d '| ')

if [ -n "$TEST_CMD" ]; then
  # 관련 테스트만 실행 (전체 테스트 스위트가 아님)
  # 실제 구현은 프로젝트별 테스트 구조에 따라 다름
  echo "[Hook] 관련 테스트 실행: $TEST_CMD"
  # eval "$TEST_CMD" -- 실제 적용 시 활성화
fi
```

### pre-commit-lint.sh — 커밋 전 린트

```bash
#!/bin/bash
# PreToolUse(Bash: git commit) 시 실행
# staged 파일에 대해 린트 실행, 실패 시 커밋 차단

LINT_CMD=$(grep -A1 "lint_command" CLAUDE.md 2>/dev/null | tail -1 | tr -d '| ')

if [ -n "$LINT_CMD" ]; then
  echo "[Hook] 린트 실행: $LINT_CMD"
  # eval "$LINT_CMD" -- 실제 적용 시 활성화
  # 실패 시 exit 1 → 커밋 차단
fi
```

### sync-logs.sh — 완료 후 로그 동기화

```bash
#!/bin/bash
# orchestrate 완료 후 수동 호출 또는 Hook으로 트리거
# .claude/tasks/done/ → impl-logs/{repo}/{ticket}/ 복사 + git push

TICKET=$1
REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" || echo "unknown")
LOG_REPO=$(grep -A1 "log_repo" CLAUDE.md 2>/dev/null | tail -1 | tr -d '| ' || echo "../impl-logs")

LOG_DIR="${LOG_REPO}/${REPO_NAME}/${TICKET}"
mkdir -p "$LOG_DIR/steps"

# 태스크 결과 복사
cp .claude/tasks/done/* "$LOG_DIR/steps/" 2>/dev/null

# 커밋 & 푸시
cd "$LOG_REPO" || exit 1
git add -A
git commit -m "log: ${REPO_NAME}/${TICKET}" 2>/dev/null
git push 2>/dev/null

echo "[Hook] 로그 동기화 완료: ${REPO_NAME}/${TICKET}"
```

---

## current-ticket 관리

`/implement`가 시작할 때 `.claude/current-ticket`에 티켓 번호를 기록.
모든 Hook 스크립트가 이 파일을 읽어서 로그 경로를 결정.

```
/implement OVDR-1234 시작
  → echo "OVDR-1234" > .claude/current-ticket

orchestrate 완료
  → sync-logs.sh OVDR-1234
  → rm .claude/current-ticket
```

---

## 검증 항목 (experiments 단계)

| 항목 | 확인할 것 |
|------|---------|
| Hook 환경변수 | Claude Code가 PostToolUse Hook에 어떤 변수를 전달하는가 |
| matcher 문법 | `tool`, `command_pattern` 등의 정확한 문법 |
| 실행 컨텍스트 | Hook 스크립트의 cwd, PATH, 권한 |
| 에러 처리 | Hook 실패 시 본 작업이 차단되는가, 무시되는가 |
| 성능 영향 | 매 Edit마다 Hook 실행 시 체감 지연 |
