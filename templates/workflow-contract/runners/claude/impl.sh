#!/usr/bin/env bash
# SECURITY NOTE: --dangerously-skip-permissions is required for headless exec environments.
# Without it, the claude CLI may hang indefinitely waiting for permission prompts.
# Use this script only in controlled, non-interactive CI/audit contexts.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  impl.sh --ticket TICKET [options]

Options:
  --ticket TICKET        Ticket or synthetic validation ID. Required.
  --plan PATH            Plan path. Default: .claude/plans/{TICKET}/plan.md
  --tasks-dir PATH       Task directory. Default: .claude/tasks/pending
  --model MODEL          Claude model override. Default: CLI configured model.
  --dry-run              Print planned commands without invoking Claude.
  -h, --help             Show this help.

Phase 0 scope:
  Runs claude headless exec once per task as implementer, once per task as reviewer,
  then once as integrator. Records Claude JSON output under
  .claude/runs/{TICKET}/claude/ and relies on shared artifacts for auditing.
  Runner ID: headless-claude
EOF
}

ticket=""
plan=""
tasks_dir=".claude/tasks/pending"
model=""
dry_run=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ticket)
      ticket="${2:-}"
      shift 2
      ;;
    --plan)
      plan="${2:-}"
      shift 2
      ;;
    --tasks-dir)
      tasks_dir="${2:-}"
      shift 2
      ;;
    --model)
      model="${2:-}"
      shift 2
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$ticket" ]]; then
  echo "--ticket is required" >&2
  usage >&2
  exit 2
fi

if [[ -z "$plan" ]]; then
  plan=".claude/plans/${ticket}/plan.md"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

runs_dir=".claude/runs/${ticket}"
claude_dir="${runs_dir}/claude"
diff_path="${runs_dir}/diff.patch"
test_output_path="${runs_dir}/test-output.log"
manifest_path="${runs_dir}/manifest.yaml"
integration_result_path="${runs_dir}/integration-result.md"
preamble_path="templates/workflow-contract/preamble.md"

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "Required file not found: $path" >&2
    exit 1
  fi
}

task_slug() {
  basename "$1" .md
}

iso_now() {
  date +"%Y-%m-%dT%H:%M:%S%z" | sed -E 's/([+-][0-9]{2})([0-9]{2})$/\1:\2/'
}

claude_base_cmd() {
  local cmd=(claude -p --output-format json --dangerously-skip-permissions)
  if [[ -n "$model" ]]; then
    cmd+=(--model "$model")
  fi
  printf '%q ' "${cmd[@]}"
}

prepend_preamble() {
  cat "${preamble_path}"
  printf '\n\n'
}

refresh_diff() {
  mkdir -p "$runs_dir"
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    local intent_paths=()
    while IFS= read -r -d '' path; do
      intent_paths+=("$path")
      git add -N -- "$path"
    done < <(git ls-files --others --exclude-standard -z)
    git diff --binary > "$diff_path"
    if [[ "${#intent_paths[@]}" -gt 0 ]]; then
      git reset -- "${intent_paths[@]}" >/dev/null
    fi
  else
    : > "$diff_path"
  fi
}

write_stub_manifest() {
  local started_at="$1"
  local run_id="$2"
  local task_paths=("$@")
  task_paths=("${task_paths[@]:2}")

  {
    cat <<EOF
schema_version: 0.1
ticket: ${ticket}
created_at: ${started_at}
updated_at: ${started_at}
status: pending
workflow_runs:
  - workflow: impl
    plan_revision: v1
    runner: headless-claude
    session_id: ${run_id}
    model: ${model:-unknown}
    status: pending
    started_at: ${started_at}
    ended_at: null
    artifacts:
      plan: ${plan}
      tasks:
EOF
    for task in "${task_paths[@]}"; do
      printf '        - %s\n' "$task"
    done
    cat <<EOF
      results: []
      diff: ${diff_path}
      test_output: ${test_output_path}
      integration_result: ${integration_result_path}
quality_gates: []
audit:
  status: not-run
  artifact: null
  checked_at: null
EOF
  } > "$manifest_path"
}

role_prompt() {
  local role="$1"
  local task_path="${2:-}"
  local result_path="${3:-}"

  case "$role" in
    implementer)
      cat <<EOF
You are running Phase 0 Claude headless parity as the implementer.

Use the canonical role prompt in claude-config/agents/implementer.md, with these headless-claude adapter overrides:
- Use runner: headless-claude in result frontmatter.
- Use model: ${model:-unknown} unless you can determine a more exact model name.
- Do not deploy or run ./deploy.sh.
- Write shared artifacts only under the paths named below.
- Append test commands and outcomes to ${test_output_path}.

Read:
- Plan: ${plan}
- Task: ${task_path}
- Result schema: templates/workflow-contract/result.schema.md
- Task schema: templates/workflow-contract/task.schema.md

Write the task result to the path requested by the task file, normally:
- .claude/tasks/done/$(task_slug "$task_path")-result.md

After implementation, stop.
EOF
      ;;
    reviewer)
      cat <<EOF
You are running Phase 0 Claude headless parity as the reviewer.

Use the canonical role prompt in claude-config/agents/reviewer.md, with these headless-claude adapter overrides:
- Review only; do not modify implementation files.
- Use runner: headless-claude and reviewer status approved or needs-fix in any result frontmatter you write.
- Do not deploy or run ./deploy.sh.

Read:
- Plan: ${plan}
- Task: ${task_path}
- Implementer result: ${result_path}
- Current diff: ${diff_path}
- Result schema: templates/workflow-contract/result.schema.md

Write your reviewer result to:
- .claude/tasks/done/$(task_slug "$task_path")-review.md

Also summarize the review in your final response.
EOF
      ;;
    integrator)
      cat <<EOF
You are running Phase 0 Claude headless parity as the integrator.

Use the canonical role prompt in claude-config/agents/integrator.md, with these headless-claude adapter overrides:
- Use runner: headless-claude in result frontmatter.
- Use model: ${model:-unknown} unless you can determine a more exact model name.
- Do not deploy or run ./deploy.sh.
- Finalize ${manifest_path}; do not rely on hooks.
- Ensure ${diff_path} and ${test_output_path} are referenced in the manifest.

Read:
- Plan: ${plan}
- Task directory: ${tasks_dir}
- Done results: .claude/tasks/done/
- Failed results: .claude/tasks/failed/
- Claude sidecars: ${claude_dir}/
- Current diff: ${diff_path}
- Test output: ${test_output_path}
- Manifest schema: templates/workflow-contract/manifest.schema.md
- Result schema: templates/workflow-contract/result.schema.md

Write:
- Integration result: ${integration_result_path}
- Final manifest: ${manifest_path}
EOF
      ;;
    *)
      echo "Unknown role: $role" >&2
      exit 2
      ;;
  esac
}

run_claude_role() {
  local role="$1"
  local task_path="${2:-}"
  local result_path="${3:-}"
  local label="$role"
  if [[ -n "$task_path" ]]; then
    label="$(task_slug "$task_path")-${role}"
  fi
  local out_dir="${claude_dir}/${label}"
  local prompt_path="${out_dir}/prompt.md"
  local events_path="${out_dir}/events.json"

  if [[ "$dry_run" -eq 1 ]]; then
    echo "[dry-run] would write ${prompt_path} and exec $(claude_base_cmd) < it > ${events_path}"
    return 0
  fi

  mkdir -p "$out_dir"
  {
    prepend_preamble
    role_prompt "$role" "$task_path" "$result_path"
  } > "${prompt_path}"

  if ! command -v claude >/dev/null 2>&1; then
    echo "claude CLI not found — install the Claude CLI before running headless-claude runner" >&2
    exit 3
  fi

  echo "Running ${label}"
  if ! eval "$(claude_base_cmd)" < "${prompt_path}" > "${events_path}"; then
    echo "claude exec failed for ${label} — see ${events_path}" >&2
    echo "No automatic fallback. Re-run with /impl --runner in-session if needed." >&2
    exit 3
  fi
}

find_task_result() {
  local task_path="$1"
  local slug
  slug="$(task_slug "$task_path")"
  if [[ -f ".claude/tasks/done/${slug}-result.md" ]]; then
    printf '%s\n' ".claude/tasks/done/${slug}-result.md"
  elif [[ -f ".claude/tasks/failed/${slug}-result.md" ]]; then
    printf '%s\n' ".claude/tasks/failed/${slug}-result.md"
  else
    printf '%s\n' ".claude/tasks/done/${slug}-result.md"
  fi
}

require_file "$plan"
require_file "$preamble_path"
if [[ ! -d "$tasks_dir" ]]; then
  echo "Task directory not found: $tasks_dir" >&2
  exit 1
fi

task_files=()
while IFS= read -r task_file; do
  task_files+=("$task_file")
done < <(find "$tasks_dir" -maxdepth 1 -type f -name 'task-*.md' | sort)
if [[ "${#task_files[@]}" -eq 0 ]]; then
  echo "No task files found in $tasks_dir" >&2
  exit 1
fi

if [[ "$dry_run" -ne 1 ]]; then
  mkdir -p "$runs_dir" "$claude_dir" ".claude/tasks/done" ".claude/tasks/failed"
  : > "$test_output_path"
  refresh_diff
fi
started_at="$(iso_now)"
run_id="claude-${ticket}-$(date +%Y%m%d-%H%M%S)"
if [[ "$dry_run" -ne 1 ]]; then
  write_stub_manifest "$started_at" "$run_id" "${task_files[@]}"
fi

for task in "${task_files[@]}"; do
  run_claude_role implementer "$task"
  if [[ "$dry_run" -ne 1 ]]; then refresh_diff; fi
  result_path="$(find_task_result "$task")"
  run_claude_role reviewer "$task" "$result_path"
done

if [[ "$dry_run" -ne 1 ]]; then refresh_diff; fi
run_claude_role integrator
if [[ "$dry_run" -ne 1 ]]; then refresh_diff; fi

if [[ "$dry_run" -eq 1 ]]; then
  echo "[dry-run] Would leave shared artifacts under ${runs_dir}"
else
  echo "Claude headless Phase 0 runner complete for ${ticket}"
  echo "Shared artifacts: ${runs_dir}"
fi
