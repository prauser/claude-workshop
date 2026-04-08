# Hook 스크립트 스펙

> 상위 문서: [design.md](design.md)
> 배포 위치: 각 프로젝트 레포의 `.claude/hooks/`
> 실험 결과 반영: 2026-04-07

## 설계 원칙

1. Hook은 품질 게이트만 담당 (포맷, 빌드, 테스트)
2. 로깅은 session jsonl 후처리로 — Hook으로 쌓지 않음
3. 무거운 체크는 Hook에 넣지 않음 → PR 생성 시점으로

---

## Hook 기본 동작

### 데이터 전달

**stdin JSON**으로 전달. 환경변수 아님.

```json
{
  "hook_event_name": "PostToolUse",
  "tool_name": "Edit",
  "tool_input": { "file_path": "...", "old_string": "...", "new_string": "..." },
  "tool_response": { "filePath": "...", "structuredPatch": [...] }
}
```

유용한 환경변수: `$CLAUDE_PROJECT_DIR`만.

### 차단 (PreToolUse)

| exit code | 동작 |
|-----------|------|
| 0 | 통과 |
| **2** | **차단**, stderr → Claude 피드백 |
| 그 외 | 통과 (에러 로깅만) |

### matcher

- 도구 이름 문자열: `"Bash"`, `"Edit|Write"`, `"Agent"`
- `if` 필드로 명령 패턴: `"Bash(git commit*)"`, `"Bash(gh pr create*)"`

### settings.json 구조

```
hooks → [{ matcher, hooks: [{ type, command, if? }] }]
```

---

## settings.json

```jsonc
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "if": "Bash(git commit*)", "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-commit-format.sh" }]
      },
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "if": "Bash(gh pr create*)", "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-pr-validate.sh" }]
      }
    ]
  }
}
```

---

## Hook 스크립트

### pre-commit-format.sh

```bash
#!/bin/bash
FORMAT_CMD=$(grep -A1 "format_command" "$CLAUDE_PROJECT_DIR/CLAUDE.md" 2>/dev/null | tail -1 | tr -d '| ')
if [ -n "$FORMAT_CMD" ]; then
  eval "$FORMAT_CMD"
  if [ $? -ne 0 ]; then
    echo "포맷 체크 실패" >&2
    exit 2
  fi
fi
```

### pre-pr-validate.sh

```bash
#!/bin/bash
BUILD_CMD=$(grep -A1 "build_command" "$CLAUDE_PROJECT_DIR/CLAUDE.md" 2>/dev/null | tail -1 | tr -d '| ')
TEST_CMD=$(grep -A1 "test_command" "$CLAUDE_PROJECT_DIR/CLAUDE.md" 2>/dev/null | tail -1 | tr -d '| ')
FAILED=0
[ -n "$BUILD_CMD" ] && { eval "$BUILD_CMD" || FAILED=1; }
[ -n "$TEST_CMD" ] && [ $FAILED -eq 0 ] && { eval "$TEST_CMD" || FAILED=1; }
if [ $FAILED -ne 0 ]; then
  echo "빌드/테스트 실패" >&2
  exit 2
fi
```

### sync-logs.sh

```bash
#!/bin/bash
# impl 완료 후 수동 호출
# 프로젝트 레포의 플랜 + 태스크 결과 + session jsonl을 impl-logs로 동기화
TICKET=$1
REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")
LOG_REPO=$(grep -A1 "log_repo" CLAUDE.md 2>/dev/null | tail -1 | tr -d '| ' || echo "../impl-logs")
LOG_DIR="${LOG_REPO}/${REPO_NAME}/${TICKET}"
mkdir -p "$LOG_DIR/steps"
cp .claude/plans/${TICKET}/plan*.md "$LOG_DIR/" 2>/dev/null
cp .claude/tasks/done/* "$LOG_DIR/steps/" 2>/dev/null
cd "$LOG_REPO" && git add -A && git commit -m "log: ${REPO_NAME}/${TICKET}" 2>/dev/null && git push 2>/dev/null
```

---

## current-ticket 관리

소유권: `/impl`. spec-plan은 plan.md에 티켓 포함 후 종료.

```
/spec-plan OVDR-1234 → .claude/plans/OVDR-1234/plan.md 저장 → 종료
/impl OVDR-1234 → echo "OVDR-1234" > .claude/current-ticket
impl 완료 → sync-logs.sh → rm .claude/current-ticket
```

`.claude/current-ticket`은 `.gitignore` 필수. worktree 사용 시 자동 격리.

---

## 로깅 전략

Hook으로 실시간 로깅하지 않음. session jsonl에 모든 tool call이 기록되므로:
- changes (파일 변경): session jsonl에서 Edit/Write tool call 추출
- metrics (에이전트 호출): session jsonl에서 Agent tool call 추출
- 후처리 스크립트로 impl 완료 후 추출 → impl-logs에 저장

session jsonl 경로: `~/.claude/projects/{project}/{session-id}.jsonl`

---

## 실험 결과 (2026-04-07)

| # | 항목 | 핵심 발견 |
|---|------|----------|
| 1 | 데이터 전달 | stdin JSON. `jq` 파싱 필요 |
| 2 | 차단 | exit 2 = 차단. stderr → Claude 피드백 |
| 3 | matcher | 도구 이름 문자열 + `if` 필드 패턴 |
| 4 | 서브에이전트 | 병렬 스폰 동작 확인 |
| 5 | UE 성능 | [experiment-5-ue-hooks.md](../../experiments/impl-workflow/experiment-5-ue-hooks.md) |

기타: Hook 설정은 세션 중 추가해도 즉시 반영. stdin에 `tool_response` 전체 포함.
