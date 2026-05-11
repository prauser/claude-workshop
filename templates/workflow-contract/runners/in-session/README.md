# In-Session Runner

The `in-session` runner has **no shell script**. The `/impl` orchestrator in the current Claude
Code session calls sub-agents (`implementer`, `reviewer`, `integrator`) directly, prepends
`../preamble.md` to each delegated prompt, and writes the same shared artifacts as the headless
runners (`.claude/runs/{TICKET}/diff.patch`, `test-output.log`, `manifest.yaml`).

## Why no script

In-session is the default and most contextual runner — the orchestrator already lives in the
session. A script would only be a degenerate `cat preamble.md && cat task.md` shim.

## Contract compliance

| Requirement | How in-session satisfies it |
|---|---|
| Same artifacts | orchestrator writes plan / task / result / diff / test-output / manifest at the same paths |
| Preamble prepend | orchestrator prepends `../preamble.md` to each sub-agent prompt |
| Status machine | sub-agent result frontmatter writes terminal status; orchestrator demotes leftover `in-progress` to `error` |
| Codex fail-loud | n/a (no codex involved) |
| Runner ID | `in-session` in result frontmatter (legacy alias `claude-code` still accepted) |

## When to pick a different runner

- `--runner headless-claude` — when you want the same Claude provider but a clean exec session
  per role (no shared session memory, easier audit logs, parallelizable).
- `--runner headless-codex` — when you want Codex provider for cost/parity comparison.
