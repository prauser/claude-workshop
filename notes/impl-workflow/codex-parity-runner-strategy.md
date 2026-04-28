# Codex Parity Runner Strategy

> Status: draft for review  
> Scope: make `/spec-plan` and `/impl` workflow concepts portable to Codex without weakening the current Claude Code workflow  
> Date: 2026-04-27  
> Related:
> - `workflow-observability-audit-proposal.md`
> - `workflow-improvement-system-proposal.md`
> - `agentlens-spec-awareness-proposal.md`

## Summary

The original motivation is not only Claude observability. The larger goal is to make the workflow harness portable enough that Claude Code and Codex can both run a similar `/spec-plan` and `/impl` process with consistent artifacts, comparable outputs, and shared audits.

The right first step is not deep Claude transcript analysis. The right first step is:

```text
provider-neutral artifact contract
  + thin Claude adapter
  + thin Codex adapter
  + artifact-only auditor
```

This keeps the existing Claude-native workflow intact while making Codex parity testable.

## Core Claim

Harness engineering should not promise immediate identical output quality across providers.

It should guarantee:

```text
same inputs
same task/result contract
same verification gates
same scope/test/spec audit
same retry/escalation policy
same comparability metrics
```

This gives us process parity and gate parity. Outcome equivalence is a long-term optimization target, not something the harness can guarantee on day one.

## What "Parity" Means

### Must Be Shared

```text
plan.md
task-N.md
task-N-result.md
manifest.yaml
diff.patch
test-output.log
quality gate evidence
artifact-only audit result
```

### May Be Provider-Specific

```text
subagent spawning mechanism
hook mechanism
tool event format
MCP integration
model selection
reasoning visibility
session transcript format
```

The shared contract should not depend on provider-specific internals.

## Why Artifact Contract Comes First

Claude Code already has strong native workflow primitives:

- custom slash commands,
- subagents,
- hooks,
- transcript logs,
- task/result files.

Codex has similar but not identical primitives:

- custom agents,
- spawned agent threads,
- `codex exec`,
- hooks with different event semantics,
- session JSONL and CLI JSON output.

Trying to normalize provider internals first is expensive and brittle. Normalizing the artifacts is cheaper and more stable.

## Minimal Phase 0

### Phase 0 Decisions To Lock First

Before implementation, lock these four decisions. They prevent drift and keep the Phase 0 scope small.

#### 1. Role Prompt Source Of Truth

Use `claude-config/agents/*.md` as the canonical role prompt source for now.

`templates/workflow-contract/roles.md` should be a short role charter only:

```text
implementer: owns code/test changes for one task artifact
reviewer: read-only review against task/result/diff
integrator: evaluates completed task results and quality gates
debugger: read-only root-cause analysis
analyzer: read-only structure/data-flow analysis
```

Do not duplicate full role prompts into `roles.md`. Codex adapters can load the canonical Claude agent prompt and ignore Claude-specific frontmatter fields where needed.

Reason:

- This matches the repo's compression principle.
- It avoids prompt drift between Claude and Codex.
- It lets Codex parity reuse the currently validated agent behavior before inventing Codex-specific prompts.

Codex-specific prompts may be introduced later only when real Codex runs show a repeated gap.

#### 2. Manifest Writer

The `integrator` owns final manifest writing.

Reason:

- It already runs after all implementation/review tasks.
- It already has read/write/bash permissions.
- It is the natural place to record quality gate evidence and final workflow status.
- It avoids relying on provider-specific `Stop` hooks.

The orchestrator or runner wrapper may create an initial manifest stub, but the integrator should finalize it.

#### 3. Codex Runner Location

During validation, place Codex runner scripts under:

```text
templates/workflow-contract/runners/codex/
```

After a successful end-to-end validation, graduate them to:

```text
codex-config/commands/
codex-config/agents/ or codex-config/prompts/
```

This mirrors the existing `claude-config/` deployment model without changing it prematurely.

The repo docs should later standardize naming between `Codex-config/` in `AGENTS.md` and `codex-config/` if this path graduates.

#### 4. Earlier Audit Documents Are Deferred Details

This strategy changes the priority of the earlier audit proposals:

```text
workflow-observability-audit-proposal.md
  Keep as design reference.
  For Phase 0, use only artifact-only audit checks.
  Defer broad decision records, events.jsonl, and hard gates.

workflow-improvement-system-proposal.md
  Keep as long-term improvement loop.
  For Phase 0, apply only lightweight validation reporting.
```

The Phase 0 implementation should not start with full transcript analysis, broad decision records, or provider-neutral low-level tool events.

### Phase 0a: Artifact Contract

Create a small contract document before building more audit infrastructure.

Suggested location while experimental:

```text
templates/workflow-contract/
  contract.md
  roles.md             # short role charter, not full prompts
  manifest.schema.md
  task.schema.md
  result.schema.md
```

Keep the current `.claude/` runtime paths for compatibility, but define them as provider-neutral artifacts:

```text
.claude/plans/{TICKET}/plan.md
.claude/tasks/pending/task-N-{name}.md
.claude/tasks/done/task-N-{name}-result.md
.claude/runs/{TICKET}/manifest.yaml
.claude/runs/{TICKET}/diff.patch
.claude/runs/{TICKET}/test-output.log
```

The `.claude/` name is historical compatibility, not a provider boundary.

### Phase 0b: Result Frontmatter

Add minimal metadata to result artifacts.

Example:

```yaml
---
ticket: OVDR-1234
workflow: impl
task: task-1-parser-fallback
role: implementer
runner: claude-code
model: claude-sonnet
status: success
started_at: 2026-04-27T10:00:00+09:00
ended_at: 2026-04-27T10:20:00+09:00
---
```

This should be small enough to preserve the repo's prompt compression principle.

### Phase 0c: Manifest Binding

Use `manifest.yaml` to bind sessions, plan revisions, and artifacts.

Example:

```yaml
ticket: OVDR-1234
workflow_runs:
  - workflow: spec-plan
    plan_revision: v1
    runner: claude-code
    session_id: 019...
    status: success
    artifacts:
      plan: .claude/plans/OVDR-1234/plan.md

  - workflow: impl
    plan_revision: v1
    runner: codex
    session_id: codex-...
    status: success
    artifacts:
      diff: .claude/runs/OVDR-1234/diff.patch
      test_output: .claude/runs/OVDR-1234/test-output.log
```

This handles the intended break between `/spec-plan` and `/impl`.

If replanning occurs:

```text
OVDR-1234 plan.md
OVDR-1234 plan-v2.md
manifest.yaml records plan_revision: v1 | v2
```

The manifest is grouped by ticket, not by one provider session. A single ticket may contain multiple workflow runs, plan revisions, and session ids.

### Phase 0d: Artifact-Only Auditor

Start with objective checks only.

Inputs:

```text
plan.md
task files
result files
manifest.yaml
diff.patch
test-output.log
integrator result
```

Checks:

```text
1. all tasks have result files
2. diff files are within task Outputs
3. promised tests or quality gates have evidence
4. integrator gates match plan Quality Gates
5. runner/role metadata is present
6. spec-plan stayed planning-only, when applicable
```

Avoid transcript-heavy LLM audit at this stage.

## Runner Adapters

### Claude Adapter

Claude remains native.

```text
/spec-plan
  -> Claude slash command
  -> Claude subagents
  -> Claude hooks
  -> provider-neutral artifacts

/impl
  -> Claude slash command
  -> implementer/reviewer/integrator subagents
  -> provider-neutral artifacts
```

The Claude adapter should add minimal metadata and manifest writing without changing core behavior.

### Codex Adapter

Codex should first be validated through artifact-only execution.

Initial shape:

```text
codex-flow impl OVDR-1234
  -> read plan.md
  -> create or read task-N.md
  -> run implementer
  -> run reviewer
  -> retry if needed
  -> run integrator
  -> write result artifacts
  -> write manifest
```

The Codex adapter can use either:

```text
1. Codex native custom agents
2. codex exec per role/task
```

For the first end-to-end validation, prefer `codex exec` per role/task because it tests whether the artifact contract is sufficient.

## Subagent Isolation Levels

### Level 1: Role Switching In One Session

```text
same context
different instruction block
```

Pros:

- fastest,
- simplest.

Cons:

- high context contamination,
- reviewer may inherit implementer framing,
- poor benchmark isolation.

Use only for lightweight work.

### Level 2: Native Subagent / Custom Agent

Claude:

```text
Agent tool -> custom subagent -> separate context window
```

Codex:

```text
spawn custom agent thread/session -> custom .codex/agents/*.toml config
```

Pros:

- good UX,
- good interactive orchestration,
- role-specific instructions,
- role-specific tools/sandbox/model settings depending on provider.

Cons:

- provider event models differ,
- lifecycle hooks are not identical,
- parent context/config may still influence child behavior,
- harder to prove that artifacts alone are sufficient.

Use for normal operations after the contract is validated.

### Level 3: Separate Exec Per Role Or Task

```text
codex exec implementer + task.md
codex exec reviewer + task.md + result + diff
codex exec integrator + all results + gates
```

Pros:

- strongest practical context isolation,
- clear process boundary,
- clean role-level logs,
- clear exit codes,
- easiest contract validation,
- reviewer sees artifacts rather than implementer conversation.

Cons:

- slower,
- more expensive,
- less natural interactive UX,
- external harness must manage orchestration.

Use for initial Codex parity validation, benchmarks, and high-value audit runs.

## Should Claude Also Use Level 3?

Not by default.

Claude Code's native Level 2 subagents are already well aligned with the current `/impl` design. Replacing them with external processes would weaken the interactive Claude workflow that the project already values.

Use Level 3 for Claude only when:

```text
- running a benchmark,
- doing Claude vs Codex A/B comparison,
- isolating reviewer contamination,
- reproducing a workflow bug,
- testing whether artifact contract alone is sufficient.
```

Normal Claude operation should stay native Level 2.

## Hook Strategy

Hooks are runner-specific implementation details.

Contract-level requirement:

```text
Each runner must enforce or record quality gates.
```

Runner-specific mechanisms:

```text
Claude:
  PreToolUse / PostToolUse / Stop / SubagentStop hooks

Codex:
  Codex hooks where available
  wrapper script checks
  git hooks when appropriate
  integrator gate execution
```

Do not make the shared contract depend on any one hook API.

## Quality Strategy

The harness should guarantee process and gate parity.

```text
Level 1: Process parity
  Same artifact contract and workflow steps.

Level 2: Gate parity
  Same build/test/review/scope criteria.

Level 3: Outcome comparability
  Same metrics and audit outputs.

Level 4: Outcome equivalence
  Similar practical quality across runners.

Level 5: Full model interchangeability
  Any model can be swapped with identical quality.
```

The realistic near-term target is Level 1-3.

Level 4 is a long-term optimization target.

Level 5 should not be assumed.

## Runner-Specific Policy

Shared contract does not mean identical prompts.

Runner-specific compensating policies are allowed as long as final artifacts and gates remain shared.

Example:

```yaml
runner_policies:
  claude-code:
    reviewer:
      mode: native_subagent
      require_scope_check: true

  codex:
    implementer:
      mode: exec_per_task
      require_context_pack: true
    reviewer:
      mode: exec_per_task
      sandbox: read-only
      rerun_on_large_diff: true
```

The shared auditor evaluates final artifacts, not provider internals.

## What Not To Do Yet

Do not start with:

- full decision record rollout,
- transcript-heavy LLM audit after every run,
- provider-neutral events schema for every low-level tool event,
- hard gates based on noisy heuristics,
- a large external orchestrator before one Codex ticket is proven.

These can come later if the artifact-only approach proves insufficient.

## Minimal Validation Test

The first milestone should be small and concrete.

```text
Given:
  one existing plan.md
  one task.md

Run:
  Claude runner completes task
  Codex runner completes same or similar task

Both produce:
  task-result.md
  diff.patch
  test-output.log
  manifest.yaml

Auditor checks:
  scope
  tests
  quality gates
  result metadata
```

Success condition:

```text
The artifact-only auditor can evaluate both runs with the same checks.
```

This proves the contract is useful before investing in deeper parity.

This does not prove Codex outcome quality yet. The validation report must separate contract sufficiency from output quality and cost.

Validation report template:

```markdown
# Codex Parity Validation: {TICKET}

## Contract Sufficiency
pass | fail

## Artifact Completeness
- plan:
- task:
- result:
- manifest:
- diff:
- test output:

## Artifact-Only Audit
- scope:
- tests:
- quality gates:
- metadata:

## Result Quality Notes
- Claude runner:
- Codex runner:
- reviewer observations:

## Cost And Latency
- Claude runtime:
- Codex runtime:
- Codex exec calls:
- estimated or reported token usage:
- notable cache/re-read overhead:

## Recommendation
contract-progress | codex-adapter-progress | both | hold
```

The first pass should record cost even if token numbers are approximate. Level 3 isolation can multiply calls quickly:

```text
5 tasks -> 5 implementer calls + 5 reviewer calls + 1 integrator call
```

So "contract works" must not be mistaken for "this is efficient enough for daily use."

## Recommended Next Steps

1. Write `templates/workflow-contract/contract.md`.
2. Define `roles.md` as a short role charter; keep `claude-config/agents/*.md` canonical.
3. Define `manifest.yaml` and make `integrator` the final manifest writer.
4. Add frontmatter metadata to one or two task result examples.
5. Extend agentlens or a small script with artifact-only checks.
6. Place the first Codex runner prototype under `templates/workflow-contract/runners/codex/`.
7. Run one small ticket through Claude native and Codex `exec-per-task`.
8. Write a validation report separating contract sufficiency, result quality, cost, and recommendation.
9. After the validation report, revisit deferred audit/improvement proposal items and decide: implement, further defer, or drop.

## Key Decision

The project should not choose between Claude-native workflow and Codex portability.

Use this split:

```text
Claude-native workflow:
  remains the high-quality interactive default

Artifact contract:
  becomes the shared workflow language

Codex adapter:
  proves portability and token/workload distribution

Artifact-only auditor:
  measures both without depending on provider internals
```

That gives Codex parity a real path without overloading the current Claude workflow.
