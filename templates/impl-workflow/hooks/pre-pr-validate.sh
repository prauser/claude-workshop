#!/bin/bash
# PreToolUse(gh pr create) — PR 생성 전 빌드+테스트
BUILD_CMD=$(grep -A1 "build_command" "$CLAUDE_PROJECT_DIR/CLAUDE.md" 2>/dev/null | tail -1 | tr -d '| ')
TEST_CMD=$(grep -A1 "test_command" "$CLAUDE_PROJECT_DIR/CLAUDE.md" 2>/dev/null | tail -1 | tr -d '| ')
FAILED=0
[ -n "$BUILD_CMD" ] && { eval "$BUILD_CMD" || FAILED=1; }
[ -n "$TEST_CMD" ] && [ $FAILED -eq 0 ] && { eval "$TEST_CMD" || FAILED=1; }
if [ $FAILED -ne 0 ]; then
  echo "빌드/테스트 실패" >&2
  exit 2
fi
