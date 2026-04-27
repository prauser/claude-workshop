#!/usr/bin/env python3
"""Artifact-only auditor for Phase 0 workflow contract runs.

This intentionally avoids provider logs, LLM judging, and third-party
dependencies. It validates only the shared artifacts described in
templates/workflow-contract/.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_RESULT_FIELDS = {
    "ticket",
    "workflow",
    "task",
    "role",
    "runner",
    "model",
    "status",
    "started_at",
    "ended_at",
}

RESULT_WORKFLOWS = {"impl", "review", "integration", "validation"}
RESULT_ROLES = {"implementer", "reviewer", "integrator", "debugger", "analyzer"}
RESULT_STATUSES_BY_ROLE = {
    "implementer": {"success", "failure", "partial"},
    "integrator": {"success", "failure", "partial"},
    "debugger": {"success", "failure", "partial"},
    "analyzer": {"success", "failure", "partial"},
    "reviewer": {"approved", "needs-fix"},
}

MANIFEST_STATUSES = {"pending", "success", "failure", "partial"}
WORKFLOW_RUNS = {"spec-plan", "impl", "review", "validation"}
GATE_STATUSES = {"pass", "fail", "skipped", "not-evaluated"}
AUDIT_STATUSES = {"not-run", "pass", "fail", "warning"}
TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2}$"
)


@dataclass
class Finding:
    severity: str
    check: str
    message: str
    artifact: str | None = None


@dataclass
class AuditResult:
    manifest: str
    findings: list[Finding]

    @property
    def status(self) -> str:
        if any(f.severity == "fail" for f in self.findings):
            return "fail"
        if any(f.severity == "warning" for f in self.findings):
            return "warning"
        return "pass"


def strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for idx, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return line[:idx]
    return line


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "~"}:
        return None
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value in {"true", "false"}:
        return value == "true"
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def yaml_lines(text: str) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        raw = strip_comment(raw).rstrip()
        if not raw.strip():
            continue
        rows.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))
    return rows


def parse_key_value(text: str) -> tuple[str, Any | None, bool]:
    key, _, value = text.partition(":")
    key = key.strip()
    if not key:
        raise ValueError(f"invalid YAML key/value line: {text}")
    if not value.strip():
        return key, None, True
    return key, parse_scalar(value), False


def parse_yaml_subset(text: str) -> Any:
    """Parse the small YAML subset used by Phase 0 manifests.

    Supported: simple key/value scalars, nested mappings, block lists, null,
    booleans, and quoted or unquoted strings. Unsupported: multiline scalars,
    anchors, aliases, tags, flow collections, and escape-sequence handling.
    """

    rows = yaml_lines(text)

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(rows) or rows[index][0] < indent:
            return None, index
        if rows[index][1].startswith("- "):
            return parse_list(index, indent)
        return parse_dict(index, indent)

    def parse_list(index: int, indent: int) -> tuple[list[Any], int]:
        items: list[Any] = []
        while index < len(rows):
            line_indent, stripped = rows[index]
            if line_indent < indent:
                break
            if line_indent != indent or not stripped.startswith("- "):
                break
            rest = stripped[2:].strip()
            index += 1
            if not rest:
                value, index = parse_block(index, indent + 2)
                items.append(value)
                continue
            if ":" in rest:
                key, value, needs_nested = parse_key_value(rest)
                item: dict[str, Any] = {}
                if needs_nested:
                    nested, index = parse_block(index, indent + 2)
                    item[key] = nested
                else:
                    item[key] = value
                while index < len(rows) and rows[index][0] > indent:
                    nested, index = parse_block(index, rows[index][0])
                    if isinstance(nested, dict):
                        item.update(nested)
                    else:
                        item.setdefault("_items", []).append(nested)
                items.append(item)
            else:
                items.append(parse_scalar(rest))
        return items, index

    def parse_dict(index: int, indent: int) -> tuple[dict[str, Any], int]:
        data: dict[str, Any] = {}
        while index < len(rows):
            line_indent, stripped = rows[index]
            if line_indent < indent:
                break
            if line_indent != indent or stripped.startswith("- "):
                break
            key, value, needs_nested = parse_key_value(stripped)
            index += 1
            if needs_nested:
                if index < len(rows) and rows[index][0] > indent:
                    value, index = parse_block(index, rows[index][0])
                else:
                    value = None
            data[key] = value
        return data, index

    parsed, next_index = parse_block(0, 0)
    if next_index != len(rows):
        raise ValueError(f"could not parse YAML near line: {rows[next_index][1]}")
    return parsed or {}


def repo_path(root: Path, path: str | Path | None) -> Path | None:
    if path is None:
        return None
    candidate = Path(str(path))
    if candidate.is_absolute():
        return candidate
    return root / candidate


def display_path(root: Path, path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section_body(markdown: str, heading: str) -> str:
    pattern = re.compile(rf"^##+\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        return ""
    next_match = re.search(r"^##+\s+\S", markdown[match.end() :], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(markdown)
    return markdown[match.end() : end].strip()


def extract_plan_quality_gates(plan_text: str) -> list[str]:
    body = section_body(plan_text, "Quality Gates")
    gates: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        gate = re.sub(r"^-\s*(?:\[[ xX]\]\s*)?", "", stripped).strip()
        gate = gate.strip("` ")
        if gate:
            gates.append(gate)
    return gates


def extract_task_outputs(task_text: str) -> set[str]:
    body = section_body(task_text, "Outputs")
    outputs: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        if re.search(r"\bnone\b", stripped, re.IGNORECASE):
            continue
        paths = re.findall(r"`([^`]+)`", stripped)
        if not paths:
            value = re.sub(r"^-\s*", "", stripped).strip()
            if value.endswith(":"):
                continue
            paths = [value]
        for path in paths:
            if path and path.lower() != "none":
                outputs.add(path)
    return outputs


def extract_task_commands(task_text: str) -> list[str]:
    body = section_body(task_text, "Verification")
    commands: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not re.match(r"^-\s*\[[ xX]\]", stripped):
            continue
        for command in re.findall(r"(?:Run|Execute)\s+`([^`]+)`", stripped, re.I):
            commands.append(command)
    return commands


def expected_result_paths(root: Path, task_path: Path, task_text: str) -> list[Path]:
    paths = [
        repo_path(root, match)
        for match in re.findall(r"`([^`]*\.claude/tasks/(?:done|failed)/[^`]+-result\.md)`", task_text)
    ]
    paths = [p for p in paths if p is not None]
    if paths:
        return paths
    slug = task_path.stem
    return [
        root / ".claude" / "tasks" / "done" / f"{slug}-result.md",
        root / ".claude" / "tasks" / "failed" / f"{slug}-result.md",
    ]


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    frontmatter_text = text[4:end]
    body = text[text.find("\n", end + 1) + 1 :]
    data: dict[str, Any] = {}
    for line in frontmatter_text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        if not key or not _:
            continue
        data[key.strip()] = parse_scalar(value)
    return data, body


def extract_diff_paths(diff_text: str) -> set[str]:
    paths: set[str] = set()
    for match in re.finditer(r"^diff --git a/(.*?) b/(.*?)$", diff_text, re.MULTILINE):
        before, after = match.groups()
        path = after if after != "/dev/null" else before
        paths.add(path.strip('"'))
    if paths:
        return paths
    for match in re.finditer(r"^\+\+\+ b/(.*?)$", diff_text, re.MULTILINE):
        paths.add(match.group(1).strip('"'))
    return paths


def path_is_allowed(path: str, allowed: set[str]) -> bool:
    for pattern in allowed:
        if pattern == path:
            return True
        if pattern.endswith("/") and path.startswith(pattern):
            return True
        if any(char in pattern for char in "*?[]") and fnmatch.fnmatch(path, pattern):
            return True
    return False


def manifest_artifact_values(manifest: dict[str, Any], key: str) -> list[str]:
    values: list[str] = []
    for run in manifest.get("workflow_runs") or []:
        if not isinstance(run, dict):
            continue
        artifacts = run.get("artifacts") or {}
        if not isinstance(artifacts, dict) or key not in artifacts:
            continue
        value = artifacts[key]
        if isinstance(value, list):
            values.extend(str(item) for item in value if item)
        elif value:
            values.append(str(value))
    return values


def find_manifest_paths(root: Path, ticket: str | None, manifest: str | None) -> list[Path]:
    if manifest:
        path = repo_path(root, manifest)
        return [path] if path else []
    if ticket:
        return [root / ".claude" / "runs" / ticket / "manifest.yaml"]
    return sorted((root / ".claude" / "runs").glob("*/manifest.yaml"))


def add(
    findings: list[Finding],
    severity: str,
    check: str,
    message: str,
    artifact: Path | str | None = None,
    root: Path | None = None,
) -> None:
    artifact_text = display_path(root, artifact) if root and artifact is not None else str(artifact) if artifact else None
    findings.append(Finding(severity, check, message, artifact_text))


def validate_result_file(root: Path, path: Path, findings: list[Finding]) -> tuple[dict[str, Any], str]:
    if not path.exists():
        add(findings, "fail", "result-presence", "Result file is missing.", path, root)
        return {}, ""
    frontmatter, body = split_frontmatter(read_text(path))
    if not frontmatter:
        add(findings, "fail", "result-frontmatter", "Result file is missing YAML frontmatter.", path, root)
        return {}, body
    missing = REQUIRED_RESULT_FIELDS - set(frontmatter)
    if missing:
        add(
            findings,
            "fail",
            "result-frontmatter",
            f"Result frontmatter is missing required field(s): {', '.join(sorted(missing))}.",
            path,
            root,
        )
    role = str(frontmatter.get("role", ""))
    status = str(frontmatter.get("status", ""))
    workflow = str(frontmatter.get("workflow", ""))
    if role not in RESULT_ROLES:
        add(findings, "fail", "result-frontmatter", f"Unknown result role: {role or '<empty>'}.", path, root)
    elif status not in RESULT_STATUSES_BY_ROLE[role]:
        allowed = ", ".join(sorted(RESULT_STATUSES_BY_ROLE[role]))
        add(
            findings,
            "fail",
            "result-status",
            f"Status {status or '<empty>'} is invalid for role {role}; expected one of: {allowed}.",
            path,
            root,
        )
    if workflow not in RESULT_WORKFLOWS:
        add(
            findings,
            "fail",
            "result-frontmatter",
            f"Unknown result workflow: {workflow or '<empty>'}.",
            path,
            root,
        )
    for field in ("started_at", "ended_at"):
        value = str(frontmatter.get(field, ""))
        if not TIMESTAMP_RE.match(value):
            add(
                findings,
                "fail",
                "result-frontmatter",
                f"{field} must be an ISO 8601 timestamp with timezone offset.",
                path,
                root,
            )
    return frontmatter, body


def validate_manifest(root: Path, manifest_path: Path) -> AuditResult:
    findings: list[Finding] = []
    if not manifest_path.exists():
        add(findings, "fail", "manifest-presence", "manifest.yaml is missing.", manifest_path, root)
        return AuditResult(display_path(root, manifest_path) or str(manifest_path), findings)

    try:
        manifest = parse_yaml_subset(read_text(manifest_path))
    except ValueError as exc:
        add(findings, "fail", "manifest-structure", f"manifest.yaml could not be parsed: {exc}", manifest_path, root)
        return AuditResult(display_path(root, manifest_path) or str(manifest_path), findings)

    if not isinstance(manifest, dict):
        add(findings, "fail", "manifest-structure", "manifest.yaml must be a mapping.", manifest_path, root)
        return AuditResult(display_path(root, manifest_path) or str(manifest_path), findings)

    required_top = {
        "schema_version",
        "ticket",
        "created_at",
        "updated_at",
        "status",
        "workflow_runs",
        "quality_gates",
        "audit",
    }
    missing_top = required_top - set(manifest)
    if missing_top:
        add(
            findings,
            "fail",
            "manifest-structure",
            f"Manifest is missing top-level field(s): {', '.join(sorted(missing_top))}.",
            manifest_path,
            root,
        )
    if str(manifest.get("schema_version")) != "0.1":
        add(findings, "fail", "manifest-structure", "schema_version must be 0.1 for Phase 0.", manifest_path, root)
    if manifest.get("status") not in MANIFEST_STATUSES:
        add(findings, "fail", "manifest-structure", "Manifest status is invalid.", manifest_path, root)
    for field in ("created_at", "updated_at"):
        value = str(manifest.get(field, ""))
        if not TIMESTAMP_RE.match(value):
            add(findings, "fail", "manifest-structure", f"{field} must include a timezone offset.", manifest_path, root)

    workflow_runs = manifest.get("workflow_runs")
    if not isinstance(workflow_runs, list) or not workflow_runs:
        add(findings, "fail", "manifest-structure", "workflow_runs must be a non-empty list.", manifest_path, root)
        workflow_runs = []
    implementation_like_run = any(
        isinstance(run, dict) and run.get("workflow") in {"impl", "review", "validation"}
        for run in workflow_runs
    )

    for index, run in enumerate(workflow_runs, start=1):
        if not isinstance(run, dict):
            add(findings, "fail", "manifest-structure", f"workflow_runs[{index}] must be a mapping.", manifest_path, root)
            continue
        workflow = run.get("workflow")
        if workflow not in WORKFLOW_RUNS:
            add(findings, "fail", "manifest-structure", f"workflow_runs[{index}].workflow is invalid.", manifest_path, root)
        if run.get("status") not in MANIFEST_STATUSES:
            add(findings, "fail", "manifest-structure", f"workflow_runs[{index}].status is invalid.", manifest_path, root)
        for field in ("runner", "session_id", "model", "started_at"):
            if not run.get(field):
                add(findings, "fail", "manifest-structure", f"workflow_runs[{index}].{field} is required.", manifest_path, root)
        if run.get("started_at") and not TIMESTAMP_RE.match(str(run["started_at"])):
            add(findings, "fail", "manifest-structure", f"workflow_runs[{index}].started_at must include an offset.", manifest_path, root)
        if run.get("ended_at") and not TIMESTAMP_RE.match(str(run["ended_at"])):
            add(findings, "fail", "manifest-structure", f"workflow_runs[{index}].ended_at must include an offset.", manifest_path, root)
        artifacts = run.get("artifacts") or {}
        if not isinstance(artifacts, dict):
            add(findings, "fail", "manifest-structure", f"workflow_runs[{index}].artifacts must be a mapping.", manifest_path, root)
            continue
        if workflow == "spec-plan":
            forbidden = sorted(set(artifacts) & {"tasks", "results", "diff", "test_output", "integration_result"})
            if forbidden:
                add(
                    findings,
                    "fail",
                    "spec-plan-planning-only",
                    f"spec-plan run records non-planning artifact(s): {', '.join(forbidden)}.",
                    manifest_path,
                    root,
                )
        if workflow in {"impl", "review", "validation"}:
            for artifact_key in ("diff", "test_output"):
                artifact_value = artifacts.get(artifact_key)
                if not artifact_value:
                    add(
                        findings,
                        "fail",
                        "run-artifacts",
                        f"workflow_runs[{index}].artifacts.{artifact_key} is required for Phase 0 validation.",
                        manifest_path,
                        root,
                    )
                else:
                    artifact_path = repo_path(root, str(artifact_value))
                    if artifact_path and not artifact_path.exists():
                        add(findings, "fail", "run-artifacts", f"{artifact_key} artifact does not exist.", artifact_path, root)

    audit = manifest.get("audit")
    if not isinstance(audit, dict):
        add(findings, "fail", "manifest-structure", "audit must be a mapping.", manifest_path, root)
    else:
        if audit.get("status") not in AUDIT_STATUSES:
            add(findings, "fail", "manifest-structure", "audit.status is invalid.", manifest_path, root)

    task_paths = [repo_path(root, value) for value in manifest_artifact_values(manifest, "tasks")]
    task_paths.extend(sorted((root / ".claude" / "tasks" / "pending").glob("task-*.md")))
    task_paths = sorted({path for path in task_paths if path is not None})
    if implementation_like_run and not task_paths:
        add(findings, "warning", "task-presence", "No task files were found for this run.", manifest_path, root)

    result_paths = [repo_path(root, value) for value in manifest_artifact_values(manifest, "results")]
    result_paths = [path for path in result_paths if path is not None]
    allowed_outputs: set[str] = set()
    commands: list[str] = []
    result_bodies: list[str] = []
    for task_path in task_paths:
        if not task_path.exists():
            add(findings, "fail", "task-presence", "Task listed in manifest does not exist.", task_path, root)
            continue
        task_text = read_text(task_path)
        allowed_outputs.update(extract_task_outputs(task_text))
        commands.extend(extract_task_commands(task_text))
        expected = expected_result_paths(root, task_path, task_text)
        matching = [path for path in expected if path.exists()]
        if not matching:
            add(
                findings,
                "fail",
                "result-presence",
                "Task has no matching result file in done/ or failed/.",
                task_path,
                root,
            )
        for result_path in matching:
            if result_path not in result_paths:
                result_paths.append(result_path)

    for result_path in sorted(set(result_paths)):
        _, body = validate_result_file(root, result_path, findings)
        result_bodies.append(body)

    test_output_values = manifest_artifact_values(manifest, "test_output")
    test_output_text = ""
    for value in test_output_values:
        path = repo_path(root, value)
        if path and path.exists():
            test_output_text += "\n" + read_text(path)
    evidence_text = test_output_text + "\n" + "\n".join(result_bodies)
    for command in commands:
        if command not in evidence_text:
            add(
                findings,
                "warning",
                "test-evidence",
                f"Verification command is promised but not found in result bodies or test-output.log: {command}",
                manifest_path,
                root,
            )

    diff_values = manifest_artifact_values(manifest, "diff")
    if implementation_like_run and not diff_values:
        add(findings, "fail", "diff-presence", "No diff.patch artifact is referenced by the manifest.", manifest_path, root)
    for value in diff_values:
        path = repo_path(root, value)
        if not path or not path.exists():
            continue
        changed_paths = extract_diff_paths(read_text(path))
        if not changed_paths:
            add(findings, "warning", "diff-scope", "diff.patch contains no changed file entries.", path, root)
        for changed_path in sorted(changed_paths):
            if not path_is_allowed(changed_path, allowed_outputs):
                add(
                    findings,
                    "fail",
                    "diff-scope",
                    f"Changed file is not declared in any task Outputs: {changed_path}",
                    path,
                    root,
                )

    gate_entries = manifest.get("quality_gates")
    if not isinstance(gate_entries, list):
        add(findings, "fail", "quality-gates", "quality_gates must be a list.", manifest_path, root)
        gate_entries = []
    gate_names: set[str] = set()
    for index, gate in enumerate(gate_entries, start=1):
        if not isinstance(gate, dict):
            add(findings, "fail", "quality-gates", f"quality_gates[{index}] must be a mapping.", manifest_path, root)
            continue
        name = str(gate.get("name") or "")
        status = gate.get("status")
        evidence = gate.get("evidence")
        notes = str(gate.get("notes") or "")
        if not name:
            add(findings, "fail", "quality-gates", f"quality_gates[{index}].name is required.", manifest_path, root)
        else:
            gate_names.add(name)
        if status not in GATE_STATUSES:
            add(findings, "fail", "quality-gates", f"quality_gates[{index}].status is invalid.", manifest_path, root)
        if status == "skipped" and not notes:
            add(findings, "fail", "quality-gates", f"quality_gates[{index}] is skipped without notes.", manifest_path, root)
        if status in {"pass", "fail"}:
            if not isinstance(evidence, list) or not evidence:
                add(findings, "fail", "quality-gates", f"quality_gates[{index}] needs evidence.", manifest_path, root)
            else:
                for evidence_path in evidence:
                    artifact = repo_path(root, str(evidence_path))
                    if not artifact or not artifact.exists():
                        add(findings, "fail", "quality-gates", "Quality gate evidence path does not exist.", artifact or str(evidence_path), root)
                    elif not read_text(artifact).strip():
                        add(findings, "fail", "quality-gates", "Quality gate evidence file is empty.", artifact, root)

    plan_paths = [repo_path(root, value) for value in manifest_artifact_values(manifest, "plan")]
    plan_paths = [path for path in plan_paths if path is not None]
    if not plan_paths and manifest.get("ticket"):
        fallback = root / ".claude" / "plans" / str(manifest["ticket"]) / "plan.md"
        if fallback.exists():
            plan_paths.append(fallback)
    for plan_path in sorted(set(plan_paths)):
        if not plan_path.exists():
            add(findings, "fail", "plan-presence", "Plan artifact does not exist.", plan_path, root)
            continue
        plan_gates = set(extract_plan_quality_gates(read_text(plan_path)))
        if not plan_gates:
            add(findings, "warning", "quality-gates", "Plan has no parseable Quality Gates bullets.", plan_path, root)
            continue
        if not implementation_like_run:
            continue
        missing_gates = sorted(plan_gates - gate_names)
        extra_gates = sorted(gate_names - plan_gates)
        if missing_gates:
            add(
                findings,
                "fail",
                "quality-gates",
                f"Manifest is missing plan quality gate(s): {', '.join(missing_gates)}.",
                manifest_path,
                root,
            )
        if extra_gates:
            add(
                findings,
                "warning",
                "quality-gates",
                f"Manifest has quality gate(s) not found in the plan: {', '.join(extra_gates)}.",
                manifest_path,
                root,
            )

    return AuditResult(display_path(root, manifest_path) or str(manifest_path), findings)


def render_markdown(results: list[AuditResult]) -> str:
    lines = ["# Artifact Audit", ""]
    overall = "pass"
    if any(result.status == "fail" for result in results):
        overall = "fail"
    elif any(result.status == "warning" for result in results):
        overall = "warning"
    lines.append(f"Overall status: **{overall}**")
    for result in results:
        lines.extend(["", f"## {result.manifest}", "", f"Status: **{result.status}**"])
        if not result.findings:
            lines.append("")
            lines.append("- pass: no findings")
            continue
        for finding in result.findings:
            artifact = f" (`{finding.artifact}`)" if finding.artifact else ""
            lines.append(f"- {finding.severity}: {finding.check}{artifact} - {finding.message}")
    lines.append("")
    return "\n".join(lines)


def render_json(results: list[AuditResult]) -> str:
    return json.dumps(
        {
            "status": "fail"
            if any(result.status == "fail" for result in results)
            else "warning"
            if any(result.status == "warning" for result in results)
            else "pass",
            "results": [
                {
                    "manifest": result.manifest,
                    "status": result.status,
                    "findings": [finding.__dict__ for finding in result.findings],
                }
                for result in results
            ],
        },
        indent=2,
    )


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_self_test_fixture(root: Path) -> None:
    ticket = "SYNTH-1"
    write(
        root / ".claude" / "plans" / ticket / "plan.md",
        """# Synthetic Plan

### Requirements

- Add parser fallback.

### Out of Scope

- none

### Impact scope

- `src/parser.ts`

### Task breakdown

- Task 1: Parser fallback

### Test Strategy

- Run parser tests.

### Quality Gates

- All tests pass

### Open questions

- none
""",
    )
    write(
        root / ".claude" / "tasks" / "pending" / "task-1-parser-fallback.md",
        """# Task 1: Parser fallback

## Context

Synthetic auditor fixture.

## Goal

Return empty metadata when optional metadata is absent.

## Inputs

- Plan: `.claude/plans/SYNTH-1/plan.md`

## Outputs

- Modify:
  - `src/parser.ts`
- Create:
  - none

## Reference Guidelines

- none

## Verification

- [ ] Run `npm test -- parser`

## On completion

Write `.claude/tasks/done/task-1-parser-fallback-result.md` using the shared result schema.
""",
    )
    write(
        root / ".claude" / "tasks" / "done" / "task-1-parser-fallback-result.md",
        """---
ticket: SYNTH-1
workflow: impl
task: task-1-parser-fallback
role: implementer
runner: codex
model: gpt-5
status: success
started_at: 2026-04-27T10:00:00+09:00
ended_at: 2026-04-27T10:10:00+09:00
---

## Status

success

## Files Changed

- `src/parser.ts`: returns empty metadata when optional metadata is absent.

## Tests

- Command: `npm test -- parser`
- Status: pass
- Evidence: `.claude/runs/SYNTH-1/test-output.log`
""",
    )
    write(
        root / ".claude" / "runs" / ticket / "diff.patch",
        """diff --git a/src/parser.ts b/src/parser.ts
index 0000000..1111111 100644
--- a/src/parser.ts
+++ b/src/parser.ts
@@ -1 +1 @@
-throw new Error("missing")
+return {}
""",
    )
    write(
        root / ".claude" / "runs" / ticket / "test-output.log",
        "$ npm test -- parser\nPASS parser.test.ts\n",
    )
    write(
        root / ".claude" / "runs" / ticket / "manifest.yaml",
        """schema_version: 0.1
ticket: SYNTH-1
created_at: 2026-04-27T10:00:00+09:00
updated_at: 2026-04-27T10:20:00+09:00
status: success
workflow_runs:
  - workflow: impl
    plan_revision: v1
    runner: codex
    session_id: codex-synth-1
    model: gpt-5
    status: success
    started_at: 2026-04-27T10:00:00+09:00
    ended_at: 2026-04-27T10:20:00+09:00
    artifacts:
      plan: .claude/plans/SYNTH-1/plan.md
      tasks:
        - .claude/tasks/pending/task-1-parser-fallback.md
      results:
        - .claude/tasks/done/task-1-parser-fallback-result.md
      diff: .claude/runs/SYNTH-1/diff.patch
      test_output: .claude/runs/SYNTH-1/test-output.log
quality_gates:
  - name: All tests pass
    status: pass
    evidence:
      - .claude/runs/SYNTH-1/test-output.log
    notes: Recorded test command exited 0.
audit:
  status: not-run
  artifact: null
  checked_at: null
""",
    )


def run_self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="artifact-audit-") as tmp:
        root = Path(tmp)
        create_self_test_fixture(root)
        passing = [validate_manifest(root, root / ".claude" / "runs" / "SYNTH-1" / "manifest.yaml")]
        if any(result.status != "pass" for result in passing):
            print(render_markdown(passing), file=sys.stderr)
            print("self-test failed: valid synthetic fixture did not pass", file=sys.stderr)
            return 1
        (root / ".claude" / "tasks" / "done" / "task-1-parser-fallback-result.md").unlink()
        failing = [validate_manifest(root, root / ".claude" / "runs" / "SYNTH-1" / "manifest.yaml")]
        if not any(result.status == "fail" for result in failing):
            print(render_markdown(failing), file=sys.stderr)
            print("self-test failed: missing-result synthetic fixture did not fail", file=sys.stderr)
            return 1
    print("self-test passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 0 workflow artifacts without LLM or provider logs.")
    parser.add_argument("--root", default=".", help="Repository root containing .claude artifacts.")
    parser.add_argument("--ticket", help="Ticket/run directory under .claude/runs/.")
    parser.add_argument("--manifest", help="Explicit manifest.yaml path, relative to --root unless absolute.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", help="Optional audit report path.")
    parser.add_argument("--self-test", action="store_true", help="Run synthetic fixture validation and exit.")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = Path(args.root).resolve()
    manifest_paths = find_manifest_paths(root, args.ticket, args.manifest)
    if not manifest_paths:
        result = AuditResult(
            "<none>",
            [Finding("fail", "manifest-presence", "No manifest.yaml files found under .claude/runs/.")],
        )
        results = [result]
    else:
        results = [validate_manifest(root, path) for path in manifest_paths]

    rendered = render_json(results) if args.format == "json" else render_markdown(results)
    if args.output:
        write(repo_path(root, args.output) or Path(args.output), rendered)
    print(rendered)
    return 1 if any(result.status == "fail" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
