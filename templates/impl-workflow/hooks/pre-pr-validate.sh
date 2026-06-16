#!/bin/bash
# PreToolUse(gh pr create) — PR 생성 전 빌드+테스트
# CLAUDE.md `## Implementation Config` 의 build_command / test_command 한 줄을 읽는다 (key: value 포맷).
BUILD_CMD=$(grep -E "^[[:space:]]*build_command[[:space:]]*:" "$CLAUDE_PROJECT_DIR/CLAUDE.md" 2>/dev/null | head -1 | sed -E 's/^[^:]*:[[:space:]]*//; s/[[:space:]]*#.*$//; s/[[:space:]]*$//')
TEST_CMD=$(grep -E "^[[:space:]]*test_command[[:space:]]*:" "$CLAUDE_PROJECT_DIR/CLAUDE.md" 2>/dev/null | head -1 | sed -E 's/^[^:]*:[[:space:]]*//; s/[[:space:]]*#.*$//; s/[[:space:]]*$//')
FAILED=0
[ -n "$BUILD_CMD" ] && { eval "$BUILD_CMD" || FAILED=1; }
[ -n "$TEST_CMD" ] && [ $FAILED -eq 0 ] && { eval "$TEST_CMD" || FAILED=1; }
if [ $FAILED -ne 0 ]; then
  echo "빌드/테스트 실패" >&2
  exit 2
fi
