# Codex Parity Roadmap

> Status: execution roadmap  
> Date: 2026-04-27  
> Primary strategy: `codex-parity-runner-strategy.md`

## Goal

Make the existing Claude Code `/spec-plan` and `/impl` workflow portable enough that Codex can run the same workflow shape through shared artifacts.

The near-term target is not identical model output quality. The near-term target is:

```text
same artifact contract
same objective audit checks
same quality gate evidence
one end-to-end Codex validation run
```

## Read First

Use this reading order in a new session.

1. `notes/impl-workflow/codex-parity-runner-strategy.md`  
   Main execution strategy. Follow this first.

2. `notes/impl-workflow/design.md`  
   Existing `/spec-plan` + `/impl` workflow overview.

3. `claude-config/commands/impl.md` and `claude-config/commands/spec-plan.md`  
   Current Claude command behavior.

4. `claude-config/agents/implementer.md`, `reviewer.md`, `integrator.md`  
   Canonical role prompts for Phase 0.

5. `notes/impl-workflow/workflow-observability-audit-proposal.md`  
   Audit design reference only. For Phase 0, use artifact-only audit checks.

6. `notes/impl-workflow/workflow-improvement-system-proposal.md`  
   Long-term improvement loop. Do not build full experiment infrastructure in Phase 0.

7. `notes/agent-skills-analysis/agentlens-spec-awareness-proposal.md`  
   Reference for extending agentlens with artifact/spec-aware audit checks.

## Phase 0 Scope

Phase 0 proves that a provider-neutral artifact contract is useful.

Do:

- Define the artifact contract.
- Keep Claude-native workflow behavior unchanged.
- Reuse `claude-config/agents/*.md` as canonical role prompts.
- Add only minimal result metadata.
- Define `manifest.yaml`.
- Build or outline an artifact-only auditor.
- Prototype one Codex `exec-per-task` runner.
- Run one small validation task.

Do not:

- Add broad decision records to every agent.
- Build transcript-heavy LLM audit.
- Add hard gates based on noisy heuristics.
- Normalize every low-level tool event.
- Replace Claude-native subagents.
- Build a large external orchestrator before one Codex validation succeeds.

## Current Claude Gap Analysis

This table captures the gap between the current Claude-native workflow and the Phase 0 artifact contract.

| Artifact | Claude current | Contract requirement | Gap |
| --- | --- | --- | --- |
| `plan.md` sections | 7 sections from `spec-plan.md` | Same 7 sections | None |
| task file structure | Matches `impl.md` task template | Same required sections | None |
| result frontmatter | Not present | Minimal frontmatter required | Add small instructions to result writers during adapter alignment |
| result body | XML tags from canonical agents | XML remains valid; markdown is recommended for fresh adapters | Auditor must parse frontmatter plus XML or markdown body |
| `diff.patch` | Not automatically standardized | Required for validation runs | Wrapper or integrator must write it |
| `test-output.log` | Not standardized | Required for validation runs | Runner or integrator must capture command evidence |
| `manifest.yaml` | Not present | Required | Integrator creates or finalizes it |

Dependency note:

- Task 6 depends on Task 4, Task 5, and Task 8.
- Other Phase 0 tasks can proceed in parallel after Task 1 is accepted.

## Phase 0 Tasks

### 1. Artifact Contract

Create:

```text
templates/workflow-contract/
  contract.md
  roles.md
  manifest.schema.md
  task.schema.md
  result.schema.md
```

Requirements:

- `roles.md` is only a short role charter.
- Full role prompts remain canonical in `claude-config/agents/*.md`.
- The contract treats `.claude/` runtime paths as historical compatibility, not a Claude-only boundary.

Reference:

- `notes/impl-workflow/codex-parity-runner-strategy.md`, "Minimal Phase 0"

### 2. Manifest Ownership

Decision:

```text
integrator owns final manifest writing
```

Tasks:

- Define the manifest schema in `templates/workflow-contract/manifest.schema.md`.
- Later add a minimal instruction to `claude-config/agents/integrator.md` after the contract is accepted.

Claude adapter rule:

- Claude-native `/impl` lets the integrator create `manifest.yaml` from scratch at integration time.
- Codex validation wrappers can create an initial stub and let the integrator finalize it.

Do not implement provider-specific `Stop` hook manifest writing in Phase 0.

### 3. Result Metadata

Define minimal frontmatter for result files.

Example fields:

```yaml
ticket:
workflow:
task:
role:
runner:
model:
status:
started_at:
ended_at:
```

Tasks:

- Document the frontmatter in `result.schema.md`.
- Add examples only. Do not rewrite existing task results unless needed for validation.
- Keep existing XML result bodies valid for Claude-native agents; markdown bodies are recommended only for fresh adapters.

### 4. Artifact-Only Auditor

Start with objective checks.

Checks:

```text
all tasks have result files
diff files are within task Outputs
promised tests or quality gates have evidence
integrator gates match plan Quality Gates
runner/role metadata exists
spec-plan stayed planning-only when applicable
```

Implementation options:

- Extend agentlens `--no-llm` mode.
- Or create a small script under `templates/workflow-contract/auditor/` during validation.

Preference:

```text
small script under templates/workflow-contract/auditor/ for the first validation;
migrate to agentlens in Phase 1 if repeated runs show the checks are useful.
```

### 5. Codex Runner Prototype

Create the first prototype under:

```text
templates/workflow-contract/runners/codex/
```

Initial mode:

```text
codex exec per role/task
```

Reason:

- strongest practical context isolation,
- clean process boundaries,
- tests whether artifact contract is sufficient.

Prototype shape:

```text
impl.sh
  read plan.md
  run implementer prompt + task.md
  run reviewer prompt + task.md + result + diff
  retry if needed
  run integrator prompt + results + gates
  write manifest
```

Do not graduate to `codex-config/` until at least one validation run succeeds.

### 6. Validation Run

Use a synthetic task first.

Reason:

- avoids Jira/tooling dependencies,
- isolates the artifact contract from product-ticket noise,
- keeps Claude vs Codex comparison small enough to inspect manually.

Run:

```text
Claude-native runner once
Codex exec-per-task runner once
artifact-only auditor on both
```

Both runs must produce:

```text
task-result.md
diff.patch
test-output.log
manifest.yaml
```

Success condition:

```text
The same artifact-only auditor can evaluate both runs.
```

This only proves contract sufficiency. It does not prove Codex outcome quality.

### 7. Validation Report

Write:

```text
experiments/workflow-improvement/{YYYYMMDD}-codex-parity-validation.md
```

Template:

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

### 8. Claude Adapter Alignment

After the contract is accepted, add minimal Claude-native alignment instructions without changing the core workflow shape.

Tasks:

- Add 1-2 lines to `claude-config/agents/integrator.md` requiring final `manifest.yaml` writing.
- Add 1-2 lines to result-writing roles requiring frontmatter before existing XML bodies.
- Add a note to `claude-config/commands/impl.md` that `.claude/runs/{TICKET}/` must exist for `diff.patch`, `test-output.log`, and `manifest.yaml`.

Do not rewrite canonical role prompts into the shared contract.

## Phase 1 Candidates

Start Phase 1 only after Phase 0 validation.

Potential next steps:

- Graduate Codex runner prototype to `codex-config/`.
- Add minimal manifest writing instruction to `integrator.md`.
- Extend agentlens with artifact-only checks.
- Add scope/test/gate audit findings.
- Add runner-specific policies for Codex gaps discovered during validation.

## Deferred Until Evidence Exists

Do not implement these until validation or repeated audits show a clear need:

- Broad decision records.
- Full transcript LLM evaluator.
- Low-level provider-neutral `events.jsonl`.
- Hard `Stop` or `SubagentStop` gates.
- Full Claude/Codex A/B benchmark suite.
- Native Codex custom-agent UX layer.

## Existing Documents And Status

| Document | Status For Phase 0 |
| --- | --- |
| `codex-parity-runner-strategy.md` | Primary strategy |
| `workflow-observability-audit-proposal.md` | Design reference; most items deferred |
| `workflow-improvement-system-proposal.md` | Long-term loop; use only validation report now |
| `design.md` | Existing workflow background |
| `spec-plan-spec.md` | Existing planning command behavior |
| `hooks-spec.md` | Claude-specific reference; not shared contract |
| `agentlens-spec-awareness-proposal.md` | Likely home for artifact-only audit evolution |

## Suggested New Session Prompt

```text
Follow notes/impl-workflow/codex-parity-roadmap.md.
Start Phase 0 by creating templates/workflow-contract/contract.md,
roles.md, manifest.schema.md, task.schema.md, and result.schema.md.
Keep claude-config/agents/*.md as the canonical role prompts.
Do not change the current Claude workflow behavior yet.
```
