# Codex Parity Phase 0 Handoff

> Session name: `phase0-claude-adapter-alignment`  
> Branch to start from: after merging `codex/workflow-contract-phase0`  
> Suggested branch: `codex/phase0-claude-adapter-alignment`

## Current State

Phase 0 contract work is complete and review-ready.

Closed commits on `codex/workflow-contract-phase0`:

```text
9452a51 Add workflow artifact contract draft
54f51fb Refine workflow contract from Phase 0 review
b1b4d0d Record Phase 0 contract review decisions
```

Resolved:

- Artifact contract draft created under `templates/workflow-contract/`.
- Phase 0 review issues #1-#6 resolved.
- S1 auditor location decided: start with a small script under `templates/workflow-contract/auditor/`.
- S2 validation target decided: start with a synthetic task.
- S3 remains open intentionally: measure actual `codex exec` surface before Codex runner implementation.

Known unrelated worktree items at handoff time:

- `deploy.sh`, `init-project.sh`: permission-only changes.
- `AGENTS.md`: untracked.
- `notes/impl-workflow/codex-parity-runner-strategy.md`: untracked strategy note.
- `notes/impl-workflow/workflow-observability-audit-proposal.md`: untracked proposal note.
- `notes/impl-workflow/workflow-improvement-system-proposal.md`: untracked proposal note.

Do not mix those unrelated items into the next implementation commit unless explicitly requested.

## Recommended Next Task

Start with Phase 0 Task 8: Claude adapter alignment.

Why this first:

- It is smaller than the auditor or Codex runner.
- It does not require S3 Codex CLI measurement.
- It makes Claude-native runs produce the artifact shape the auditor will later check.

## Scope

Keep Claude-native workflow behavior unchanged.

Minimal changes:

- `claude-config/agents/integrator.md`
  - Add 1-2 lines requiring final `.claude/runs/{TICKET}/manifest.yaml` writing.
  - State that Claude-native integrator creates the manifest from scratch at integration time.

- `claude-config/agents/implementer.md`
  - Add 1-2 lines requiring required YAML frontmatter before the existing `<result>` body.
  - Do not replace the XML body format.

- `claude-config/agents/reviewer.md`
  - Add 1-2 lines requiring required YAML frontmatter before the existing `<review>` body.
  - Do not replace the XML body format.

- `claude-config/agents/integrator.md`
  - Add required YAML frontmatter before the existing `<integration-result>` body.
  - Keep XML body valid.

- `claude-config/commands/impl.md`
  - Ensure `.claude/runs/{TICKET}/` exists or is assigned as the run artifact directory.
  - Record expected run artifacts: `diff.patch`, `test-output.log`, `manifest.yaml`.

## References

Read in this order:

1. `notes/impl-workflow/codex-parity-roadmap.md`
2. `notes/impl-workflow/codex-parity-phase0-review.md`
3. `templates/workflow-contract/contract.md`
4. `templates/workflow-contract/result.schema.md`
5. `templates/workflow-contract/manifest.schema.md`
6. `claude-config/commands/impl.md`
7. `claude-config/agents/implementer.md`
8. `claude-config/agents/reviewer.md`
9. `claude-config/agents/integrator.md`

## Acceptance Criteria

- Existing Claude agent body formats remain XML.
- Required result frontmatter is documented in each result-writing role.
- Integrator ownership of final manifest writing is explicit.
- `/impl` command points agents at a ticket run artifact directory.
- No provider-specific Stop hook manifest writing is introduced.
- Changes are narrow enough for a focused review.

## Suggested New Session Prompt

```text
Follow notes/impl-workflow/codex-parity-roadmap.md and notes/impl-workflow/codex-parity-phase0-review.md.
Start Phase 0 Task 8: Claude adapter alignment.
Use session name: phase0-claude-adapter-alignment.
Create a new branch: codex/phase0-claude-adapter-alignment.
Keep changes minimal:
- integrator writes/finalizes manifest.yaml
- result-writing roles add required frontmatter before existing XML bodies
- impl command ensures .claude/runs/{TICKET}/ exists for diff.patch, test-output.log, manifest.yaml
Do not change core Claude workflow behavior.
Do not include unrelated worktree items.
```
