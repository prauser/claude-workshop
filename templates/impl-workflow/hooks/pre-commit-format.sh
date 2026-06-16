#!/bin/bash
# PreToolUse(git commit) — 커밋 전 포맷 체크
# 빠른 포맷터만. 무거운 정적분석 넣지 않음.
# CLAUDE.md `## Implementation Config` 의 `format_command: <cmd>` 한 줄을 읽는다 (key: value 포맷).
FORMAT_CMD=$(grep -E "^[[:space:]]*format_command[[:space:]]*:" "$CLAUDE_PROJECT_DIR/CLAUDE.md" 2>/dev/null | head -1 | sed -E 's/^[^:]*:[[:space:]]*//; s/[[:space:]]*#.*$//; s/[[:space:]]*$//')
if [ -n "$FORMAT_CMD" ]; then
  eval "$FORMAT_CMD"
  if [ $? -ne 0 ]; then
    echo "포맷 체크 실패" >&2
    exit 2
  fi
fi
