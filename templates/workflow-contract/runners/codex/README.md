# Codex Phase 0 Runner Prototype

Prototype runner for `codex exec` per role/task.

This is intentionally small and validation-oriented. It does not deploy
`claude-config/`, does not integrate agentlens, and does not replace the
Claude-native workflow.

## S3 CLI Surface Notes

Confirmed locally:

- prompt input: argv or stdin with `-`
- non-interactive command: `codex -a never exec ...`
- working directory: `--cd PATH`
- sandbox: `--sandbox read-only|workspace-write|danger-full-access`
- JSONL events: `--json`
- final response capture: `--output-last-message PATH`
- session id: first JSONL event has `thread_id`
- token usage: `turn.completed.usage`
- temp/non-git probes need `--skip-git-repo-check`; repo runs do not

The runner records JSONL events and final messages as Codex sidecars under
`.claude/runs/{TICKET}/codex/`. The artifact-only auditor must rely only on the
shared artifacts: task results, `diff.patch`, `test-output.log`, and
`manifest.yaml`. Because this prototype creates one Codex thread per role/task,
the manifest stub uses a stable local run id for `session_id`; provider thread
ids remain in the JSONL sidecars.

`diff.patch` is generated from tracked changes plus non-ignored untracked files
using temporary `git add -N` intent-to-add entries. Start validation from a clean
worktree so unrelated untracked files do not enter the patch.

## Usage

Dry-run command planning:

```bash
templates/workflow-contract/runners/codex/impl.sh \
  --ticket LOCAL-20260427-101500 \
  --dry-run
```

Run against the default Phase 0 paths:

```bash
templates/workflow-contract/runners/codex/impl.sh \
  --ticket LOCAL-20260427-101500
```

Override model or sandbox:

```bash
templates/workflow-contract/runners/codex/impl.sh \
  --ticket LOCAL-20260427-101500 \
  --model gpt-5.4 \
  --sandbox workspace-write
```

Expected shared artifacts:

```text
.claude/runs/{TICKET}/manifest.yaml
.claude/runs/{TICKET}/diff.patch
.claude/runs/{TICKET}/test-output.log
.claude/runs/{TICKET}/integration-result.md
.claude/tasks/done/task-N-{name}-result.md
```
