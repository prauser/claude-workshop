# claude-workshop rules

This workspace is for learning, experimenting, and managing Claude Code configuration.
Follow these rules for all tasks in this directory.

## Purpose

* Analyze plugin source code in `references/` and extract useful patterns
* Collect and organize knowledge in `notes/`
* Run prompt experiments in `experiments/` and record results
* Draft prompt templates in `templates/` before graduating to `claude-config/`
* Improve `claude-config/` based on findings
* Run isolated plugin experiments in `sandbox/`

## References analysis

* `references/` contains git-cloned plugin sources. They are plain files — nothing is installed or active.
* Read and analyze source files directly. Do not install anything from `references/`.
* When analyzing, focus on: hook usage, task decomposition patterns, agent definitions, context management strategies.

## Notes

* `notes/` is for collected knowledge — research summaries, articles, tips, reference material.
* Organize by topic in subdirectories (e.g., `notes/sycophancy/`, `notes/prompt-engineering/`).
* These are read-only reference material, not actionable configs.

## Experiments

* `experiments/` is for hands-on testing with recorded results.
* Each experiment should have a clear hypothesis and outcome.
* Organize by topic in subdirectories (e.g., `experiments/anti-sycophancy/`).
* When an experiment yields a useful pattern, draft it as a template in `templates/`.

## Templates

* `templates/` holds prompt templates that are still being validated.
* Once a template is proven effective, graduate it to `claude-config/` for deployment.
* Do not deploy templates directly — always go through the graduation flow.

## Sandbox rules

* Only install one plugin at a time in `sandbox/`
* After analysis is complete, always uninstall before finishing:

  ```
  claude plugin uninstall {plugin-name}
  ```
* Never install multiple plugins simultaneously — hook conflicts are likely.

## Improving claude-config

* All edits to commands and agents go in `claude-config/`
* After editing, remind the user to run `./deploy.sh` to apply changes to `~/.claude/`
* Do not directly modify `~/.claude/` — always go through `claude-config/` + `deploy.sh`

## Graduation flow

```
notes/         → knowledge gathering
experiments/   → hands-on validation
templates/     → draft template
claude-config/ → proven, deploy-ready
~/.claude/     → deployed (via deploy.sh)
```
