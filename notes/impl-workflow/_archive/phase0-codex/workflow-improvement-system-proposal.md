# Workflow Improvement System Proposal

> Archived 2026-05-07 — partially superseded by `.claude/plans/LOCAL-20260507-harness-revamp/plan.md`; unabsorbed ideas (audit/experiment loop) tracked in `notes/impl-workflow/future-ideas.md`. Kept for history.
> Status: draft for review  
> Scope: Claude Code workflow first; provider-neutral extension later  
> Date: 2026-04-25  
> Related: `workflow-observability-audit-proposal.md`  
> Phase 0 note: `codex-parity-runner-strategy.md` takes priority for the next implementation step. Use this document as the long-term improvement loop, but for Phase 0 keep the process lightweight: artifact contract, artifact-only audit, one Codex validation run, and a short validation report. Defer full experiment infrastructure until repeated audit findings justify it.

## Summary

This proposal describes a full improvement system for the Claude Code workflow.

The goal is to keep the existing interactive `/spec-plan` and `/impl` experience, while adding a disciplined loop for observing, auditing, experimenting, and promoting workflow changes.

The system has three layers:

```text
1. Run Audit
   Did this workflow run behave correctly?

2. Improvement Experiment
   Does a proposed prompt/agent/hook/process change improve the workflow?

3. Promotion Decision
   Should the change graduate from experiment/template into deployed config?
```

The earlier observability proposal covers layer 1 in detail. This document connects that audit layer to a broader workflow improvement process.

## Background

The project already follows a knowledge-to-deployment graduation path:

```text
notes/ -> experiments/ -> templates/ -> claude-config/ -> ~/.claude/
```

Recent work already fits this pattern:

- external workflow and agent-skill analysis,
- hook experiments,
- `/spec-plan` and `/impl` design,
- agent prompt improvements,
- agentlens-style session analysis,
- proposed observability and audit layers.

The missing piece is a shared protocol that connects these activities:

```text
Workflow run evidence
  -> audit findings
  -> improvement hypothesis
  -> controlled experiment
  -> promotion or rejection
```

## Core Position

Do not choose between "LLM-native flexibility" and "scripted reproducibility" too early.

Use both, but assign them different jobs:

```text
LLM-native workflow:
  - interactive user conversation
  - ambiguous requirement handling
  - planning and judgment
  - qualitative review and retro

Structured audit/experiment layer:
  - raw log preservation
  - normalized metrics
  - spec-vs-run comparison
  - missing evidence detection
  - repeatable experiments
  - promotion decisions
```

This lets Claude Code remain the primary user-facing workflow while making the workflow itself easier to improve.

## Design Principles

### 1. Preserve Native Workflow First

Keep `/spec-plan`, `/impl`, and existing subagents as the primary operating path.

Do not prematurely replace the workflow with an external CLI harness. A CLI harness can be added later if the same audit schema proves useful and stable.

### 2. Treat Raw Logs As Evidence, Not As Product

Raw transcripts, hook payloads, tool calls, diffs, and test logs are evidence.

They are not convenient for comparison by themselves. The system should preserve them, then derive normalized events and metrics.

### 3. Do Not Depend On Raw Thinking

Raw chain-of-thought should not be the primary analysis target.

Use:

```text
tool trace + diff + tests + review output + explicit decision records
```

Thinking text, if present, is optional supporting context.

### 4. Decision Records Are Annotations, Not Truth

Agent-written decision records are useful, but they can be incomplete or self-justifying.

The evaluator must cross-check them against actual tool traces and diffs.

### 5. Improve By Experiment, Not Taste

Prompt and workflow changes should be treated as hypotheses.

Each substantial change should define:

- expected improvement,
- baseline,
- test runs,
- metrics,
- acceptance criteria,
- promotion decision.

### 6. Promote Only What Survives Evidence

Do not move prompts, hooks, or agent changes into `claude-config/` only because they sound good.

Graduate them when run evidence supports them.

## System Overview

```text
Claude Code Run
  |
  | raw transcript, hooks, task files, diffs, tests
  v
Run Audit
  |
  | audit.md, metrics.json, deviations.json, retro.md
  v
Improvement Backlog
  |
  | hypothesis + candidate change
  v
Experiment
  |
  | baseline vs trial metrics
  v
Promotion Decision
  |
  | accept / revise / reject
  v
templates/ or claude-config/
```

## Layer 1: Run Audit

Run audit answers:

```text
Did this specific `/spec-plan` or `/impl` run follow the intended workflow?
```

Inputs:

- Claude transcript.
- Hook event logs.
- Tool calls and outputs.
- Task and result files.
- Plan files.
- Diffs.
- Test/build output.
- Review findings.
- Explicit decision records.

Outputs:

```text
.claude/runs/{run-id}/
  audit.md
  metrics.json
  deviations.json
  retro.md
  events.jsonl
  raw/
  decisions/
```

Run audit should detect:

- missing task/result files,
- skipped workflow steps,
- unsupported decision claims,
- scope expansion,
- promised tests not run,
- repeated review findings,
- command failures that were not interpreted,
- missing decision records around important changes.

For details, see `workflow-observability-audit-proposal.md`.

## Layer 2: Improvement Backlog

Audit findings should feed a workflow improvement backlog.

Each backlog item should be phrased as a problem, not a solution.

Good:

```text
Implementer often edits files outside task Outputs without recording scope expansion.
```

Less useful:

```text
Add more instructions to implementer.
```

Backlog item template:

```markdown
## Problem

## Evidence
- run id:
- audit finding:
- affected workflow:

## Suspected Cause

## Candidate Fixes
- prompt change
- task template change
- hook/check change
- evaluator rule change
- documentation/guideline change

## Priority
critical | high | medium | low
```

## Layer 3: Improvement Experiment

An improvement experiment tests whether a candidate change actually helps.

Use this when changing:

- command prompts,
- subagent prompts,
- task templates,
- result schemas,
- hooks,
- quality gates,
- evaluator rules,
- log schemas,
- external reference guidelines.

Experiment template:

```markdown
# Experiment: {name}

## Hypothesis
If we change {thing}, then {metric} will improve because {reason}.

## Candidate Change
- Files/prompts/hooks affected:
- Exact behavior change:

## Baseline
- Runs sampled:
- Current metric values:
- Known confounders:

## Trial Plan
- Number of runs:
- Workflow:
- Task type:
- Model/agent versions:
- What stays constant:

## Metrics
- primary:
- secondary:
- qualitative:

## Results
- observed:
- unexpected:
- failures:

## Decision
accept | revise | reject

## Promotion Target
notes | experiments | templates | claude-config
```

## Suggested Metrics

Start simple.

Run quality:

- workflow completion rate,
- task completion rate,
- review rounds per task,
- retries per task,
- failed commands per run,
- tests promised vs tests run,
- quality gates passed,
- scope expansion count.

Audit quality:

- missing decision records,
- unsupported decision claims,
- spec deviations,
- evidence gaps,
- repeated findings across runs.

Agent behavior:

- files read before first edit,
- tests read before implementation,
- tool calls per task,
- code edits after failed command,
- reviewer issue recurrence,
- uncertainty level vs actual failure rate.

Human experience:

- user interventions,
- plan revisions,
- blocked completions,
- time to final report,
- subjective usefulness of final summary.

## Layer 4: Promotion Decision

Promotion should be explicit.

```text
notes/
  analysis and proposals

experiments/
  tested hypotheses and results

templates/
  candidate prompts/scripts ready for repeated use

claude-config/
  deployed commands and agents
```

Promotion checklist:

```markdown
## Promotion Checklist

- [ ] Problem is supported by audit evidence.
- [ ] Candidate change was tested in at least one real or realistic run.
- [ ] Primary metric improved or failure mode was clearly removed.
- [ ] No major regressions observed.
- [ ] Added/updated documentation.
- [ ] Rollback path is clear.
- [ ] Owner accepted the tradeoff.
```

Promotion outcomes:

```text
accept:
  move to claude-config/ or project template

revise:
  keep in templates/ or experiments/ with next hypothesis

reject:
  archive result; keep lesson in notes/
```

## Proposed Directory Structure

Keep the current structure, but make experiment and audit outputs more explicit.

```text
notes/
  impl-workflow/
    design.md
    workflow-observability-audit-proposal.md
    workflow-improvement-system-proposal.md
  workflow-research/
    {topic}.md

experiments/
  impl-workflow/
    experiment-5-ue-hooks.md
  workflow-improvement/
    {YYYYMMDD}-{short-name}.md

templates/
  impl-workflow/
  workflow-candidates/
    commands/
    agents/
    hooks/
    evaluators/

claude-config/
  commands/
  agents/
```

## Relationship To Agentlens

The existing agentlens spec-awareness proposal fits directly into this system.

It can become the evaluation component that compares:

```text
intended workflow spec
  commands/*.md
  agents/*.md

actual run
  transcript
  tool calls
  task files
  results

findings
  spec-deviation
  missing evidence
  unsupported decision
  workflow inefficiency
```

Recommended direction:

1. Let agentlens discover workflows from deployed command and agent files.
2. Add normalized event loading.
3. Add audit finding types from this proposal.
4. Generate improvement backlog entries from repeated findings.

## Relationship To Codex Or Other Providers

Provider-neutral support should come later.

The stable abstraction is not "Claude vs Codex." It is:

```text
runner executes task
runner produces raw log
normalizer produces events.jsonl
evaluator audits against workflow spec
```

When Codex is added:

```text
Claude transcript -> normalize -> events.jsonl
Codex jsonl       -> normalize -> events.jsonl
```

Keep raw logs separately. Compare normalized events and metrics.

This allows token/use distribution across providers without splitting the improvement system into provider-specific silos.

## Recommended Rollout

### Phase 1: Audit Current Claude Workflow

- Keep existing `/spec-plan` and `/impl`.
- Add decision record sections to result outputs.
- Archive raw transcripts and hook events.
- Generate minimal `events.jsonl`, `metrics.json`, and `audit.md`.

### Phase 2: Add Workflow Auditor

- Create a `workflow-auditor` agent.
- It checks run evidence against command/agent specs.
- It outputs deviations, metrics, and retro.

### Phase 3: Start Experiment Protocol

- Add `experiments/workflow-improvement/`.
- Use the experiment template for prompt/hook/schema changes.
- Start with one small change, such as reviewer decision records or scope expansion detection.

### Phase 4: Close The Loop

- Feed repeated audit findings into an improvement backlog.
- Promote only tested changes.
- Keep rejected experiments as lessons.

### Phase 5: Provider-Neutral Runner Layer

- Only after the Claude audit schema is stable, add Codex or other runners.
- Normalize their logs into the same event schema.
- Compare runner behavior with shared metrics.

## First Candidate Experiments

### Experiment 1: Reviewer Decision Records

Hypothesis:

```text
Adding short Decision Records to reviewer output will make repeated review-loop causes easier to classify.
```

Primary metric:

```text
percentage of needs-fix findings with evidence-backed rationale
```

### Experiment 2: Scope Expansion Detection

Hypothesis:

```text
Flagging diff files outside task Outputs will reduce unacknowledged scope drift.
```

Primary metric:

```text
unacknowledged scope expansions per impl run
```

### Experiment 3: Tests-Promised vs Tests-Run Audit

Hypothesis:

```text
Comparing task Verification checkboxes against actual test tool calls will reduce false completion reports.
```

Primary metric:

```text
promised tests not run
```

### Experiment 4: Workflow Spec Deviation Analysis

Hypothesis:

```text
Loading commands/*.md and agents/*.md into the evaluator will catch skipped steps more reliably than transcript-only analysis.
```

Primary metric:

```text
high-confidence spec-deviation findings per audited run
```

## Risks

### Logging Burden

Too much required logging can slow agents down.

Mitigation:

- record only meaningful decision points,
- keep templates short,
- detect missing decisions after the run rather than forcing verbose logs during every tool call.

### False Positives

Audit rules may flag acceptable behavior.

Mitigation:

- start with observe-only mode,
- review several runs before hard gates,
- record false-positive examples.

### Overfitting To Metrics

Agents may optimize for audit fields rather than good work.

Mitigation:

- keep qualitative review,
- use metrics as signals, not absolute truth,
- preserve raw logs for manual review.

### Provider Drift

Claude and Codex expose different logs and thinking visibility.

Mitigation:

- do not depend on raw thinking,
- normalize only stable events,
- preserve provider-specific raw logs separately.

## Non-Goals

- Do not replace Claude Code native workflow immediately.
- Do not build a large external orchestrator before audit needs are proven.
- Do not require verbose reasoning before every tool call.
- Do not treat decision records as ground truth.
- Do not promote prompt changes without run evidence.

## Recommendation

Use the audit proposal as the first implementation detail, but treat it as one part of a larger improvement system.

The recommended path is:

```text
Claude-native workflow
  + run audit
  + improvement experiments
  + explicit promotion decisions
  + later provider-neutral runners
```

This keeps the current interactive workflow intact while making workflow engineering measurable, reviewable, and easier to improve over time.
