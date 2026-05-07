# Phase 0 Artifact Auditor

Small, dependency-free auditor for the Phase 0 workflow artifact contract.

It checks only shared artifacts under `.claude/`:

- task/result presence
- required result frontmatter and role-specific statuses
- `diff.patch` and `test-output.log` manifest references
- changed files staying inside task `## Outputs`
- `manifest.yaml` structure and quality gate evidence
- plan `### Quality Gates` matching manifest `quality_gates`
- `spec-plan` manifests staying planning-only

Manifest YAML support is intentionally narrow: simple scalars, nested mappings, and block lists only. Gate names must match exactly between the plan and manifest.

Run against a ticket:

```bash
python3 templates/workflow-contract/auditor/audit.py --ticket LOCAL-20260427-101500
```

Run against an explicit manifest:

```bash
python3 templates/workflow-contract/auditor/audit.py \
  --manifest .claude/runs/LOCAL-20260427-101500/manifest.yaml
```

Write an audit artifact:

```bash
python3 templates/workflow-contract/auditor/audit.py \
  --ticket LOCAL-20260427-101500 \
  --output .claude/runs/LOCAL-20260427-101500/artifact-audit.md
```

Validate the auditor with synthetic fixtures:

```bash
python3 templates/workflow-contract/auditor/audit.py --self-test
```

Exit codes: `0` for pass or warning, `1` for hard contract failures.
