# Workflow Roles

> Status: Phase 0 draft  
> Full prompt source of truth: `claude-config/agents/*.md`

This file is a short provider-neutral role charter only. Do not duplicate full agent prompts here.

Codex adapters may load the canonical Claude role prompts and ignore provider-specific frontmatter fields until validation shows a repeated gap.

## Roles

### implementer

Owns code and test changes for one task artifact.

Inputs:

- one task file
- referenced source files
- prior task results when listed

Outputs:

- changed files within task scope
- task result file
- task-level test evidence

Canonical prompt:

- `claude-config/agents/implementer.md`

### reviewer

Performs read-only review against task, result, diff, and relevant tests.

Inputs:

- task file
- task result file
- diff or changed file list
- test evidence

Outputs:

- `approved` or `needs-fix`
- findings by severity
- concise summary

Canonical prompt:

- `claude-config/agents/reviewer.md`

### integrator

Evaluates completed task results and quality gates after all task work is done.

Inputs:

- plan quality gates
- all task files
- all task result files
- full diff
- test output

Outputs:

- integration result
- final quality gate evidence
- finalized `manifest.yaml`

Canonical prompt:

- `claude-config/agents/integrator.md`

### debugger

Performs read-only root-cause analysis for bugs or failing gates.

Inputs:

- symptom or failure report
- relevant logs and files

Outputs:

- diagnosis
- likely cause
- recommended next task or fix scope

Canonical prompt:

- `claude-config/agents/debugger.md`

### analyzer

Performs read-only structure, data-flow, and impact analysis.

Inputs:

- analysis question
- relevant code and docs

Outputs:

- affected areas
- dependency map
- risk notes

Canonical prompt:

- `claude-config/agents/analyzer.md`

## Runner Notes

Role behavior should stay stable across runners, but execution can differ:

- Claude Code may use native subagents.
- Codex Phase 0 should use `codex exec` per role/task for isolation.
- Future adapters may introduce runner-specific prompts only after validation evidence shows a need.
