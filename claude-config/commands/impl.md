# Implementation Mode

Orchestrate implementation via specialist agents. Never write code directly. Pull only result summaries into this context, not full code.

**Usage**: `/impl {TICKET}` | `/impl {description}` | `/impl`

## Template path resolution

본 prompt 와 sub-agent 는 `templates/workflow-contract/...` 의 SSOT 파일을 인용한다.
**resolution 규칙 (cwd 우선, `~/.claude/templates` 폴백)**:
`./templates/workflow-contract/{file}` 가 존재하면 그것, 없으면
`~/.claude/templates/workflow-contract/{file}` 를 사용. 둘 다 없으면 사용자에게
"`./deploy.sh` 미실행 가능성" 경고 후 진행 중단.

이 규칙은 in-session orchestrator / implementer / reviewer / integrator / 헤드리스 러너 모두 동일.

## Runner selection

`--runner ID` 플래그로 runner 선택. 기본값 `in-session`.

- `--runner in-session` (기본) — 현재 Claude Code 세션의 sub-agent 사용
- `--runner headless-claude` — `templates/workflow-contract/runners/claude/impl.sh` 호출 (task-5b
  에서 추가)
- `--runner headless-codex` — `templates/workflow-contract/runners/codex/impl.sh` 호출

선택된 runner 가 종료한 뒤, orchestrator 는 contract.md §Status Machine 의 self-report 검증을
실행:
- 모든 result frontmatter 의 `status` 가 terminal (`success`/`partial`/`failure`) 인지 확인
- `pending` / `in-progress` 가 남아 있으면 해당 result 를 `error` 로 강등하고 body 에
  `auto-demoted` 라인을 한 줄 추가
- per-role 분리 시에도 검증은 result frontmatter 단위 — runner 가 다르더라도 모든 result 의
  status 가 terminal 인지 동일 룰로 점검한다.

headless runner 가 exit 3 (codex 실패 등) 으로 종료하면 **자동 in-session fallback 금지**.
사용자에게 실패 출력을 보여주고 명시적 재실행 요청을 받는다 (예: `/impl --runner in-session`).

Runner enum / Status machine 의 SSOT 는 `templates/workflow-contract/contract.md` 의 §Runners / §Status Machine.
Per-role / preset 매핑의 SSOT 는 본 파일의 §Per-role runner override / §권장 프리셋. runner
스크립트(`templates/workflow-contract/runners/`) 는 task 단위로만 호출되며, role-별 분리는
orchestrator 가 결정.

### Per-role runner override

기본은 `--runner` 가 모든 role 에 적용되지만, role-별로 다른 runner 를 쓰고 싶으면:

- `--runner-implementer ID` — implementer 에이전트만 다른 runner 로 실행
- `--runner-reviewer ID` — reviewer 에이전트만 다른 runner 로 실행
- `--runner-integrator ID` — integrator 에이전트만 다른 runner 로 실행

각 플래그가 받을 수 있는 ID 는 `--runner` 와 동일 (`in-session` / `headless-claude` /
`headless-codex`). 우선순위: per-role > `--runner` > 기본값(`in-session`).

미지정 role 은 `--runner` 또는 기본값을 그대로 사용한다.

### 권장 프리셋

비용 / 품질 trade-off 가 명확한 두 프리셋을 명시 옵션으로 둔다. 기본값은 여전히 `in-session`
일괄 — 사용자가 명시하지 않으면 프리셋 적용 X.

| 프리셋 | implementer | reviewer | integrator | 적용 명령 |
|---|---|---|---|---|
| `--preset cost-optimized` | `headless-codex` | `in-session` | `in-session` | implementer 만 codex 로 cost 절감, 비판적 판단 (review/integration) 은 Claude in-session |
| `--preset claude-only` | `in-session` | `in-session` | `in-session` | 기본값과 동일 — 명시적으로 프리셋 표기를 원할 때 |

프리셋과 per-role 플래그가 동시에 주어지면 **per-role 플래그가 우선**, 프리셋은 그 외 role 에만
적용. 두 프리셋이 동시 지정되면 에러 (인자 오류).

cost / latency 측정은 `runs/{TICKET}/manifest.yaml` 의 model / runner 필드로 사후 비교 가능.
실측 결과 수집은 별도 phase (plan.md §Intentional Exclusions 의 "cache 최적화" 항목 참조).

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

5. **idiom-pool 임계 알림** — `~/.claude/idiom-pool.yaml` 이 있으면 읽어 임계(term별 count ≥ 3) 이상이고 `status: open` 인 entries 가 있는지 확인. 있으면 첫 출력 직전 한 줄 알림:
   `idiom-pool: N건 임계 (예: stale ×5, idempotent ×4). \`/idiom-review\` 권장.`
   - 알림은 *정보성* — 자동 트리거 X (사용자가 명시 호출해야 실행됨).
   - 파일 없음 또는 임계 항목 없음 → 조용히 skip.

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
   - Required elements:
     1. **자기완결성**: implementer가 이전 대화 없이 독립 실행 가능해야 함.
     2. **YAML frontmatter telemetry 3종 채우기** (`task.schema.md` §YAML frontmatter 참조):
        - `plan_sha` = `git hash-object .claude/plans/{TICKET}/plan.md` 결과 (working tree 의 blob SHA — tracking 무관, gitignored 레포에서도 동작).
        - `intent_problem` = plan.md frontmatter `intent.problem` 값 verbatim.
        - `contributes_to` = 본 task 가 plan.md `intent.approach` 의 어느 단계인지 한 줄. *impl 이 task 분해 시 자동 생성*.
        - task 분해 시 CLAUDE.md `glossary_path` 가 있으면 task 본문 §사전 준비에 해당 GLOSSARY 경로를 자동 포함.
        - task 위임 직전 GLOSSARY 파일 본문을 implementer 컨텍스트에 prepend (path 만 전달이 아닌 본문 자체).
        - (참고) plan deviation 은 *런타임 발견* 만 추적 — implementer 가 result frontmatter `plan_deviations:` 에 append. pending task 에는 두지 않음.
     3. **사용자 원문 복사**: `plan.md` 최상단 YAML frontmatter의 `user_prompt` 값을 task 파일 §"사용자 최초 프롬프트 원문" 블록에 그대로 복사. 요약·정제 금지.
     4. **AC = 실행 가능 bash**: §Acceptance Criteria는 zero exit = pass인 bash 커맨드로만 작성. 추상적 서술 금지.
     5. **주의사항 X-Y 형식**: "X 하지 마라. 이유: Y" 형식. 이유 누락 시 무효.
     6. **On completion**: result 파일 경로와 result.schema.md 링크 명시.
3. **Execute sequentially** — For each task:
   - Before delegating to `implementer`, prepend `templates/workflow-contract/preamble.md` content verbatim to the implementer prompt.
   - Delegate to `implementer` → then `reviewer`
   - If reviewer returns `needs-fix`:
     - Filter reviewer issues to priority `p1` / `p2` only and pass those to `implementer` (p3/p4 are not forwarded — ping-pong cost avoidance).
     - `implementer` fixes only p1·p2 issues and writes a new result. Do not overwrite the same task's review file — append a Round 2/3 section instead.
     - max 3 rounds. If p1 / p2 issues remain after round 3, escalate to user with both implementation and review context.
     - User deferral is recorded as `deferred: [issue summary]` in the result `<decisions>` block, or an explicit user message to the orchestrator acknowledging the issue.
   - If reviewer returns `approved` but `[p3]` / `[p4]` issues remain: proceed. Record as follow-up TODO in result `<handoff>` (one line per item).
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

reviewer output format SSOT: `claude-config/agents/reviewer.md` §Output format. impl routing consumes the priority tags from that schema directly.

## Plan drift detection

매 task 위임 직전 `git hash-object .claude/plans/{TICKET}/plan.md` 결과를 task frontmatter `plan_sha` 와 비교한다.

- 일치 → 정상 진행.
- 불일치 → plan.md 가 변경된 상태. orchestrator 는:
  1. plan.md `intent_history` 마지막 엔트리를 읽어 무엇이 바뀌었는지 확인.
  2. pending task 들의 `contributes_to` / `plan_sha` 를 새 plan 기준으로 갱신.
  3. 사용자에게 한 줄 알림: "plan 이 갱신됨 ({field} 변경). 영향 task: N건. 이대로 진행?"
  4. 사용자가 "OK" → 갱신 후 진행. "정지" → halt.

`plan_deviations` 누적 → plan 으로 되돌릴 신호. 한 task 에서 3 건 이상 쌓이면 사용자에게 plan 갱신 권유 (강제 X).

## PR body injection

`/commit-push-pr` 호출 시 (별도 스킬) orchestrator 는 plan.md frontmatter 에서 다음을 추출해 PR body 에 박는다 (plan.md 본문은 push 하지 않음 — `.claude/*` gitignored 유지):

- `intent` 블록 전체 (Problem / Approach / Why / PRD)
- `gate_events` 요약 (각 gate 의 turns / result)
- `skip_grill_count`
- `risk_acks` 중 `needs_check` 항목 (있으면)

이게 팀 가시성 채널. plan.md 본문은 로컬에만 남음.

## Rules
- Never write code. Always delegate.
- If spec changes, update affected pending task files.
- Branch / commit / push 정책의 SSOT 는 이 파일의 §Branch policy / §Commit policy. preamble.md 7번과 정합.
