#!/bin/bash
# impl 완료 후 수동 호출 — 프로젝트 레포 → impl-logs 동기화
TICKET=$1
REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")
LOG_REPO=$(grep -A1 "log_repo" CLAUDE.md 2>/dev/null | tail -1 | tr -d '| ' || echo "../impl-logs")
LOG_DIR="${LOG_REPO}/${REPO_NAME}/${TICKET}"
mkdir -p "$LOG_DIR/steps"
cp .claude/plans/${TICKET}/plan*.md "$LOG_DIR/" 2>/dev/null
cp .claude/tasks/done/* "$LOG_DIR/steps/" 2>/dev/null
cd "$LOG_REPO" && git add -A && git commit -m "log: ${REPO_NAME}/${TICKET}" 2>/dev/null && git push 2>/dev/null
