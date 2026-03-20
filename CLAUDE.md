# claude-workshop rules

This workspace is for analyzing reference plugins and improving claude-config.
Follow these rules for all tasks in this directory.

## Purpose
- Analyze plugin source code in `references/` and extract useful patterns
- Improve `claude-config/` based on findings
- Run isolated plugin experiments in `sandbox/`

## References analysis
- `references/` contains git-cloned plugin sources. They are plain files — nothing is installed or active.
- Read and analyze source files directly. Do not install anything from `references/`.
- When analyzing, focus on: hook usage, task decomposition patterns, agent definitions, context management strategies.

## Sandbox rules
- Only install one plugin at a time in `sandbox/`
- After analysis is complete, always uninstall before finishing:
  ```bash
  claude plugin uninstall {plugin-name}
  ```
- Never install multiple plugins simultaneously — hook conflicts are likely.

## Improving claude-config
- All edits to commands and agents go in `claude-config/`
- After editing, remind the user to run `./deploy.sh` to apply changes to `~/.claude/`
- Do not directly modify `~/.claude/` — always go through `claude-config/` + `deploy.sh`
