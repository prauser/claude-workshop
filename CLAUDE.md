# claude-workshop

Use this workspace for code analysis, prompt experiments, and config management.

## Directory structure

| Directory | Purpose |
|-----------|---------|
| `notes/` | Collected knowledge — research, articles, reference material. Organize by topic. |
| `experiments/` | Hands-on testing with hypothesis and outcome. Yields templates. |
| `templates/` | Prompt templates being validated. Graduate to `claude-config/` when proven. |
| `claude-config/` | Deploy-ready commands and agents. `deploy.sh` → `~/.claude/`. |
| `references/` | Git-cloned plugin sources for analysis. See `.claude/rules/references.md`. |
| `sandbox/` | Isolated plugin experiments. See `.claude/rules/sandbox.md`. |

## Graduation flow

```
notes/ → experiments/ → templates/ → claude-config/ → ~/.claude/ (via deploy.sh)
```
