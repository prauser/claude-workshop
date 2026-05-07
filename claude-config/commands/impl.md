# Implementation Mode

Orchestrate implementation via specialist agents. Never write code directly. Pull only result summaries into this context, not full code.

**Usage**: `/impl {TICKET}` | `/impl {description}` | `/impl`

## On activation

1. Parse argument:
   - **Ticket pattern** (e.g. `OVDR-1234`): load `.claude/plans/{TICKET}/plan.md`.
     - Found: summarize as bullet points, confirm with user, proceed.
     - Not found: proceed to spec discussion.
   - **Free text**: use as initial context for spec discussion.
   - **No argument**: ask user what to implement.
2. **Spec discussion** (when no plan.md): elicit requirements, summarize as bullets, confirm.
3. Record ticket if applicable: `echo "{TICKET}" > .claude/current-ticket`. If no external ticket exists, after confirmation assign `LOCAL-{YYYYMMDD-HHMMSS}` and record it the same way.
4. Create run artifact directories before delegating:
   ```bash
   mkdir -p .claude/runs/{TICKET} .claude/tasks/pending .claude/tasks/done .claude/tasks/failed
   ```
   Do not continue until `.claude/runs/{TICKET}/` exists. Agents write all run artifacts there:
   - `diff.patch` — final run diff for validation
   - `test-output.log` — command and quality gate evidence
   - `manifest.yaml` — final run manifest written by the integrator

## Branch policy

`/impl` 진입 시 현재 브랜치를 확인한다.

- 현재 브랜치가 `master` / `main` / `develop` 중 하나면, **자동으로 작업 브랜치를 분기**:
  ```bash
  SLUG="{plan.md 제목에서 추출한 kebab-slug, 최대 32자}"
  git checkout -b "feat/{TICKET}-${SLUG}"
  ```
  분기 직전에 `git status`가 clean 이 아니면 사용자에게 멈추고 묻는다 (uncommitted 변경 보호).
- 현재 브랜치가 이미 `feat/{TICKET}-*` 또는 사용자가 명시 지정한 브랜치면 **그대로 사용** (resume 시나리오).
- 기타 브랜치(예: 다른 feat 브랜치 위) 면 사용자에게 한 번 확인하고 진행 여부 결정.

PR 생성은 자동화하지 않는다 (plan.md Intentional Exclusions). 사용자가 수동으로 만든다.

## On debug/analysis request
1. **Classify** — debugging (bug/symptom) or analysis (understanding).
2. **Write task file** — `.claude/tasks/pending/task-{N}-{name}.md`
3. **Delegate** — `debugger` for bugs, `analyzer` for understanding.
4. **Report** — Present diagnosis/analysis to user.
5. **If fix needed** — Proceed to implementation with diagnosis as context.

## On implementation request
1. **Decompose** — Feature-level tasks (not file-level). Order by dependencies. If plan.md was loaded (spec already approved), skip approval and proceed. Only ask for approval when no plan.md exists (free-text/no-arg path).
2. **Write task files** — `.claude/tasks/pending/task-{N}-{name}.md`:
   - Task format follows `templates/workflow-contract/task.schema.md` exactly.
   - Five required elements:
     1. **자기완결성**: implementer가 이전 대화 없이 독립 실행 가능해야 함.
     2. **사용자 원문 복사**: `plan.md` 최상단 YAML frontmatter의 `user_prompt` 값을 task 파일 §"사용자 최초 프롬프트 원문" 블록에 그대로 복사. 요약·정제 금지.
     3. **AC = 실행 가능 bash**: §Acceptance Criteria는 zero exit = pass인 bash 커맨드로만 작성. 추상적 서술 금지.
     4. **주의사항 X-Y 형식**: "X 하지 마라. 이유: Y" 형식. 이유 누락 시 무효.
     5. **On completion**: result 파일 경로와 result.schema.md 링크 명시.
3. **Execute sequentially** — For each task:
   - Before delegating to `implementer`, prepend `templates/workflow-contract/preamble.md` content verbatim to the implementer prompt.
   - Delegate to `implementer` → then `reviewer`
   - If `needs-fix`: re-delegate to `implementer` with review (max 3 rounds)
   - After 3 rounds still `needs-fix`: escalate to user with both implementation and review context
   - On failure: move to `.claude/tasks/failed/`, ask user
4. **Integration** — After all tasks, delegate to `integrator` with Quality Gates from plan.md's `### Quality Gates`
5. **Final report** — Features, test results, failures, next steps

## Commit policy

reviewer 가 approved 를 반환한 직후, orchestrator(`/impl`)는 다음 2단 커밋을 순서대로 수행한다.
이 commit 들은 preamble 규칙 7과 충돌하지 않는다 — 7번은 implementer 에이전트의 자동 commit 을
금지할 뿐, orchestrator 의 통제된 commit 은 허용된다.

1. **Code commit (`feat` / `fix` / `refactor` / `docs` 중 변경 성격에 맞는 type)**:
   ```bash
   git add {task.outputs 에 명시된 코드/문서 경로}
   git commit -m "{type}({scope}): {task 한 줄 요약}

   Refs: .claude/plans/{TICKET}/plan.md task-{N}"
   ```
   `git add` 는 **task `## Outputs` 에 선언된 경로만** 사용.
   와일드카드 전체 추가(`-A` 플래그 또는 현재 디렉토리 `.` 인수) 금지
   (선언되지 않은 secret/대용량 파일 보호).

2. **Artifact commit (`chore`)**:
   ```bash
   ARTIFACT_TASK=".claude/tasks/done/task-{N}-*.md"
   ARTIFACT_RUN=".claude/runs/{TICKET}/"
   git add "${ARTIFACT_TASK}" "${ARTIFACT_RUN}"
   git commit -m "chore({TICKET}): task-{N} artifacts"
   ```
   .claude/ 가 .gitignore 에 의해 무시되는 레포라면 이 단계는 스킵하고 result 파일에
   `<decisions>` 한 줄로 기록한다.

자동 push 는 하지 않는다. 자동 PR 도 만들지 않는다 (Intentional Exclusions).
실패 시(예: pre-commit hook 거부) 양쪽 commit 모두 롤백하지 말고 — 첫 commit 은 유지하고
두 번째 실패만 사용자에게 보고. 절대 `--no-verify` 로 hook 우회 금지.

## On completion
1. `rm .claude/current-ticket`
2. If `log_repo` is configured in CLAUDE.md, remind user to run `sync-logs.sh {TICKET}`.
3. 모든 task 완료 후, 사용자에게 작업 브랜치 이름과 push 명령(`git push -u origin feat/...`)을 안내. push / PR 생성은 사용자가 수동.

## Agents
- `debugger` — 6-step triage protocol (read-only, opus)
- `analyzer` — code structure/flow analysis (read-only, opus)
- `implementer` — incremental slice + TDD + atomic commits (sonnet)
- `reviewer` — code quality, bugs, edge cases (read-only, sonnet)
- `integrator` — integration tests across all tasks (sonnet)
- `test-engineer` — test strategy/coverage analysis (read-only, sonnet)

## Rules
- Never write code. Always delegate.
- If spec changes, update affected pending task files.
- Branch / commit / push 정책의 SSOT 는 이 파일의 §Branch policy / §Commit policy. preamble.md 7번과 정합.
