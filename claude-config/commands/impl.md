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

## On debug/analysis request
1. **Classify** — debugging (bug/symptom) or analysis (understanding).
2. **Write task file** — `.claude/tasks/pending/task-{N}-{name}.md`
3. **Delegate** — `debugger` for bugs, `analyzer` for understanding.
4. **Report** — Present diagnosis/analysis to user.
5. **If fix needed** — Proceed to implementation with diagnosis as context.

## On implementation request
1. **Decompose** — Feature-level tasks (not file-level). Order by dependencies. If plan.md was loaded (spec already approved), skip approval and proceed. Only ask for approval when no plan.md exists (free-text/no-arg path).
2. **Write task files** — `.claude/tasks/pending/task-{N}-{name}.md`:
   ```
   ## Context
   {spec summary, self-contained}
   ## Goal
   {what to implement}
   ## Inputs
   - Ref files: {paths}
   - Prior task results: {.claude/tasks/done/ paths if any}
   ## Outputs
   - Create: {paths}
   - Modify: {paths}
   ## Reference Guidelines
   - {paths from CLAUDE.md guidelines: list, if configured}
   ## Verification
   - [ ] Write tests ({path})
   - [ ] All tests pass
   - [ ] {feature-specific checks}
   ## On completion
   Write `.claude/tasks/done/task-{N}-{name}-result.md`:
   ---
   ticket: {TICKET}
   workflow: impl
   task: task-{N}-{name}
   role: implementer
   runner: claude-code
   model: sonnet
   status: success | failure | partial
   started_at: {ISO 8601 with timezone}
   ended_at: {ISO 8601 with timezone}
   ---
   <result>
     <status>success | failure</status>
     <files><file path="{path}">{description}</file></files>
     <tests passed="{N}" failed="{N}"><failure>{name}</failure></tests>
     <decisions>{decisions made}</decisions>
     <handoff>{for next task}</handoff>
   </result>
   ```
3. **Execute sequentially** — For each task:
   - Delegate to `implementer` → then `reviewer`
   - If `needs-fix`: re-delegate to `implementer` with review (max 3 rounds)
   - After 3 rounds still `needs-fix`: escalate to user with both implementation and review context
   - On failure: move to `.claude/tasks/failed/`, ask user
4. **Integration** — After all tasks, delegate to `integrator` with Quality Gates from plan.md's `### Quality Gates`
5. **Final report** — Features, test results, failures, next steps

## On completion
1. `rm .claude/current-ticket`
2. If `log_repo` is configured in CLAUDE.md, remind user to run `sync-logs.sh {TICKET}`.

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
