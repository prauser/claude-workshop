# Codex Parity Validation: Phase 0

> Date: 2026-04-28
> Tickets: LOCAL-20260427-101500 (claude-code), LOCAL-20260427-102000 (codex)
> Branch: codex/phase0-validation

## Contract Sufficiency

**Claude-native: pass.**
**Codex: blocked — network (not a contract failure).**

The artifact contract is sufficient for Claude-native. A single auditor evaluated the claude-code run with exit 0. The Codex runner prototype is mechanically correct but requires a live `chatgpt.com` WebSocket connection that was unavailable in this environment.

## Artifact Completeness

### Claude-native (LOCAL-20260427-101500)

| Artifact | Status |
|---|---|
| plan | `.claude/plans/LOCAL-20260427-101500/plan.md` — present |
| task | `.claude/tasks/pending/task-1-greet.md` — present |
| implementer result | `.claude/tasks/done/task-1-greet-result.md` — present, frontmatter valid |
| reviewer result | `.claude/tasks/done/task-1-greet-review.md` — present, frontmatter valid |
| integration result | `.claude/runs/LOCAL-20260427-101500/integration-result.md` — present |
| manifest | `.claude/runs/LOCAL-20260427-101500/manifest.yaml` — present, gates matched |
| diff | `.claude/runs/LOCAL-20260427-101500/diff.patch` — 35 lines, 2 files |
| test output | `.claude/runs/LOCAL-20260427-101500/test-output.log` — 2 commands, both exit 0 |

### Codex (LOCAL-20260427-102000)

| Artifact | Status |
|---|---|
| plan | `.claude/plans/LOCAL-20260427-102000/plan.md` — present |
| task | `.claude/tasks/pending/task-1-greet.md` — shared with claude-code run |
| stub manifest | `.claude/runs/LOCAL-20260427-102000/manifest.yaml` — stub created, status: pending |
| codex prompts | all 3 role prompts generated correctly under `.claude/runs/LOCAL-20260427-102000/codex/` |
| codex events | implementer events.jsonl — 24 events (5 file reads succeeded, then network failure) |
| diff | `.claude/runs/LOCAL-20260427-102000/diff.patch` — empty (implementer never wrote files) |
| test output | `.claude/runs/LOCAL-20260427-102000/test-output.log` — empty |
| implementer result | missing — turn.failed before model could write `sandbox/hello.py` |
| reviewer result | missing — implementer step never completed |
| integration result | missing — integrator never ran |

## Artifact-Only Audit

### Claude-native audit

```
Exit: 0 (pass)
Findings: none
```

Auditor confirmed:
- All three quality gates in manifest matched plan bullets exactly
- Evidence paths (test-output.log) exist and are non-empty
- Result frontmatter present with valid role/status enums
- diff.patch references files in task `## Outputs`

### Codex audit

```
Exit: 1 (fail)
Findings:
  warning: diff.patch contains no changed file entries
  fail: manifest missing plan quality gates (3 gates)
```

These findings are expected for a failed/incomplete run. The auditor correctly identified the incomplete state.

## Result Quality Notes

**Claude-native**: Task implemented correctly. `greet(name)` returns `"Hello, {name}!"` using f-string. Three unit tests pass (`test_greet_world`, `test_greet_empty_string`, `test_greet_name`). Reviewer approved with one non-blocking suggestion (no annotation import needed since `str` is builtin).

**Codex**: Model started correctly — it read `implementer.md`, `task-1-greet.md`, `result.schema.md`, and `task.schema.md` (items 1-5 in events.jsonl) then hit WebSocket disconnection before generating implementation. The Codex agent understood the role prompt structure and executed the right read sequence.

**Reviewer observation**: The implementer prompt in the Codex runner correctly references `claude-config/agents/implementer.md` — the same canonical prompt used in the claude-code run. Provider-neutral contract confirmed.

## Cost And Latency

### Claude-native

- Runtime: ~2.5 minutes (estimated, orchestrated within this session)
- Roles: implementer + reviewer + integrator (3 agents)
- Model: claude-opus-4-7
- Notable overhead: sandbox/ gitignore required force-staging to generate real diff

### Codex

- Runtime: approximately 53 minutes before failure (23:16 UTC → 00:09 UTC)
- Codex exec calls: 1 attempted (implementer only), 2 not reached (reviewer, integrator)
- Token usage: unknown — turn.failed before turn.completed event
- Failure mode: WebSocket stream to `chatgpt.com` disconnected after 5 file reads; 10 reconnect attempts (2×5) failed
- Estimated cost: negligible (model never generated output tokens; turn.failed early)

## Findings And Notes

### F1 — Codex network access required

The Codex CLI at `0.125.0-alpha.3` connects to `wss://chatgpt.com/backend-api/codex/responses`. This environment has no route to that endpoint. The runner prototype is correct; the environment does not have Codex API access.

**Action**: Codex exec validation must run in an environment with ChatGPT/Codex API access.

### F2 — Plan gate name format

The original plan used `- \`gate name\` — description` bullet format. The auditor's `extract_plan_quality_gates` strips the leading backtick only from the left edge, leaving the full `name — description` string as the gate key. The manifest expects just the short `name`.

**Fix applied**: Plan bullets changed to `- \`gate name\`` (short names only). Auditor passed after this change. This is a contract documentation gap: the README should note that gate names must be the short backtick-wrapped name, without a description suffix.

### F3 — sandbox/ in gitignore

The synthetic task wrote files to `sandbox/` which is gitignored. Real diff required `git add -f` (force-stage) followed by immediate unstage. For validation runs, tasks should target non-gitignored paths. Alternatively the auditor can be taught to accept empty diff.patch for new-file-only tasks in gitignored dirs.

**Action**: Prefer `experiments/` paths for future synthetic tasks; or document the force-stage workaround in the runner README.

## Recommendation

**contract-progress** (Claude-native) + **codex-adapter-progress pending network access**

The Phase 0 artifact contract is sufficient for Claude-native. The same auditor script evaluates both runs correctly: passing for a complete run, failing with precise findings for an incomplete run. The Codex runner prototype generates the correct prompt structure and calls codex exec with the right arguments (confirmed via dry run and events.jsonl inspection).

Phase 0 contract goals are met for Claude-native. Codex exec validation is blocked on API access, not contract design. Proceed to Phase 0 close for Claude-native side; schedule a Codex API exec re-run for when the environment has `chatgpt.com` access.

## Phase 0 Contract Acceptance Assessment

| Acceptance criterion | Status |
|---|---|
| Claude-native and Codex can produce the same artifact set | Partial — claude-code confirmed, codex blocked on network |
| Same artifact-only auditor evaluates both runs | Confirmed — auditor ran on both, correct exit codes |
| Validation report separates contract, quality, cost, latency | Present in this document |

Phase 0 contract is **accepted for Claude-native**. Codex acceptance deferred until network access is available.

## Codex Direct Rerun — 2026-05-03

Ticket: `LOCAL-20260503-225201`

Result: **Codex accepted for Phase 0 artifact contract.**

The direct Codex runner completed all three role/process steps:

- implementer wrote `experiments/workflow-improvement/fixtures/codex-direct-greet/hello.py`
- implementer wrote `experiments/workflow-improvement/fixtures/codex-direct-greet/test_hello.py`
- reviewer wrote `.claude/tasks/done/task-1-experiment-greet-review.md`
- integrator finalized `.claude/runs/LOCAL-20260503-225201/manifest.yaml`
- auditor exited 0 after `diff.patch` captured the new non-ignored files

Additional runner finding:

- `git diff` alone does not include untracked new files. The runner now uses temporary `git add -N` intent-to-add entries while generating `diff.patch`.

Final Phase 0 status after rerun:

```text
Claude-native: accepted
Codex exec-per-task: accepted
Artifact-only auditor: shared pass on complete runs
```
