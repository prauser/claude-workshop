#!/bin/bash
# PreToolUse(git commit) — 커밋 전 포맷 체크
# 빠른 포맷터만. 무거운 정적분석 넣지 않음.
FORMAT_CMD=$(grep -A1 "format_command" "$CLAUDE_PROJECT_DIR/CLAUDE.md" 2>/dev/null | tail -1 | tr -d '| ')
if [ -n "$FORMAT_CMD" ]; then
  eval "$FORMAT_CMD"
  if [ $? -ne 0 ]; then
    echo "포맷 체크 실패" >&2
    exit 2
  fi
fi
