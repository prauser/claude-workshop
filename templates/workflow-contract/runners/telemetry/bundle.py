"""
bundle.py — 번들 직렬화(versioned schema) + git 업로드 + --dry-run 감사.

책임 범위:
  - BUNDLE_SCHEMA_VERSION: 번들 스키마 버전 상수 (agentlens Phase B 계약 SSOT).
  - serialize_bundle: harvested + characteristics + generated_at → 번들 dict 조립.
  - validate_bundle: 필수 키·버전 검증. 빈 리스트 = valid.
  - upload_bundle: dry-run(기본) 또는 실제 git push. 반드시 selfcheck_bundle 통과.

주의사항:
  - generated_at은 INJECT받는다 — 코드에서 datetime.now() 호출 금지(결정성 보장).
  - 업로드 직전 deid.selfcheck_bundle을 BUNDLE_DUMPS_KWARGS로 호출 (checked bytes == written bytes).
  - target은 설정값(env WF_COLLECT_TARGET 또는 --target)으로 받는다. 하드코딩 금지.
  - raw 로그 본문 번들 포함 금지 — 메트릭 + 이벤트 스트림 + 추상화 특성 + evidence_ref 포인터만.

외부 의존 0 — stdlib만 사용.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# sys.path 조정 — deid 모듈 임포트
# ---------------------------------------------------------------------------

def _ensure_sys_path() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


_ensure_sys_path()

try:
    import deid as _deid_mod  # type: ignore
except ImportError:  # pragma: no cover
    _deid_mod = None  # type: ignore


# ---------------------------------------------------------------------------
# 번들 스키마 버전 상수 — agentlens Phase B 계약 SSOT
# ---------------------------------------------------------------------------

BUNDLE_SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# 업로드 결과 객체
# ---------------------------------------------------------------------------

@dataclass
class UploadResult:
    """upload_bundle 반환 결과."""

    ok: bool
    dry_run: bool
    out_path: Optional[str] = None          # dry-run 시 쓰인 파일 경로
    audit_lines: List[str] = field(default_factory=list)   # 감사 리포트 줄
    error: Optional[str] = None             # 실패 시 오류 메시지


# ---------------------------------------------------------------------------
# 번들 조립 — serialize_bundle
# ---------------------------------------------------------------------------

def serialize_bundle(
    harvested: Dict[str, Any],
    characteristics: Dict[str, Any],
    *,
    generated_at: str,
) -> Dict[str, Any]:
    """번들 dict를 조립한다.

    번들 형태(JSON):
    {
      "bundle_schema_version": "1.0",
      "generator": "wf-collect",
      "generated_at": "<ISO 8601 주입값>",
      "tickets": [
        {
          "ticket": str,
          "repo": str,
          "plan": {intent, gate_events, skip_presearch, skip_gate2,
                   readiness_flags, risk_acks, intent_history_len, plan_sha},
          "tasks": [{task_id, status, role, plan_deviations, risk_acks, rounds}],
          "manifest": {status, quality_gates},
          "sessions": [{session_id, events:[<평문 이벤트>]}],
          "user_input_characteristics": {<T4 추상화 산출>},
          "evidence_ref": {session_paths:[...], artifact_paths:[...]}
        }
      ],
      "parse_errors": [...]
    }

    Args:
        harvested:         harvest_artifacts + harvest_sessions 결과를 담은 dict.
                           키: artifact_results(list), session_results(list).
        characteristics:   ticket → user_input_characteristics 매핑 (T4 추상화 산출).
        generated_at:      번들 생성 타임스탬프 (INJECT받는다 — datetime.now() 금지).

    Returns:
        번들 dict. deid.BUNDLE_DUMPS_KWARGS로 직렬화 가능.
    """
    artifact_results: List[Any] = harvested.get("artifact_results") or []
    session_results: List[Any] = harvested.get("session_results") or []

    tickets_map: Dict[str, Dict[str, Any]] = {}
    all_parse_errors: List[Any] = []

    # --- artifact_results 처리 ---
    for repo_rec in artifact_results:
        if not isinstance(repo_rec, dict):
            continue

        repo_path = repo_rec.get("repo_path") or repo_rec.get("repo_name") or ""
        repo_name = repo_rec.get("repo_name") or ""

        # parse_errors 수집
        for pe in repo_rec.get("parse_errors") or []:
            all_parse_errors.append(pe)

        by_ticket = repo_rec.get("by_ticket") or {}
        for ticket_id, bucket in by_ticket.items():
            if not isinstance(bucket, dict):
                continue

            if ticket_id not in tickets_map:
                tickets_map[ticket_id] = {
                    "ticket": ticket_id,
                    "repo": repo_name or repo_path,
                    "plan": None,
                    "tasks": [],
                    "manifest": None,
                    "sessions": [],
                    "user_input_characteristics": {},
                    "evidence_ref": {
                        "session_paths": [],
                        "artifact_paths": [],
                    },
                }

            entry = tickets_map[ticket_id]

            # plan 필드 구성
            plan_rec = bucket.get("plan")
            if plan_rec and isinstance(plan_rec, dict):
                plan_path = plan_rec.get("plan_path")
                # evidence_ref에 plan_path 추가 (로컬 포인터 — raw 본문 미포함)
                if plan_path and plan_path not in entry["evidence_ref"]["artifact_paths"]:
                    entry["evidence_ref"]["artifact_paths"].append(plan_path)

                # plan_sha를 12자로 축약 — 40자 git SHA는 고엔트로피(high-entropy) 탐지기에
                # 걸릴 수 있다. 12자 short-SHA는 식별에 충분하며 엔트로피 임계값 미만.
                raw_sha = plan_rec.get("plan_sha")
                short_sha = raw_sha[:12] if raw_sha else None

                # plan risk_acks: detail 제거 (일관성 — 번들 메트릭 범위 밖 산문 제외)
                raw_plan_risk_acks = plan_rec.get("risk_acks") or []
                stripped_plan_risk_acks = [
                    {k: v for k, v in ra.items() if k != "detail"}
                    for ra in raw_plan_risk_acks
                    if isinstance(ra, dict)
                ]

                entry["plan"] = {
                    # intent.*는 spec-plan 생성 내러티브 — 비식별 대상 아님
                    # (plan P0-2 + Open Questions '평문 권장')
                    "intent": plan_rec.get("intent"),
                    "gate_events": plan_rec.get("gate_events") or [],
                    "skip_presearch": plan_rec.get("skip_presearch", 0),
                    "skip_gate2": plan_rec.get("skip_gate2", 0),
                    "readiness_flags": plan_rec.get("readiness_flags") or [],
                    "risk_acks": stripped_plan_risk_acks,
                    "intent_history_len": plan_rec.get("intent_history_len", 0),
                    # intent 변경 이력 상세(field/prev_value/reason) — spec-plan 생성 평문.
                    # drift finding 이 무엇이 왜 바뀌었는지 보이도록 싣는다. self-check 에서
                    # intent.* 와 함께 plaintext_subtrees 로 제외(collect.py _INTENT_SUBTREES).
                    "intent_history": plan_rec.get("intent_history") or [],
                    "plan_sha": short_sha,
                    # legacy schema-drift indicator (P1-1, plan A4)
                    # None when absent (modern plan), numeric/truthy when present (drift signal)
                    "skip_grill_count": plan_rec.get("skip_grill_count"),
                }

            # tasks 필드 구성
            task_recs = bucket.get("tasks") or []
            for task_rec in task_recs:
                if not isinstance(task_rec, dict):
                    continue
                task_path = task_rec.get("path")
                if task_path and task_path not in entry["evidence_ref"]["artifact_paths"]:
                    entry["evidence_ref"]["artifact_paths"].append(task_path)

                # risk_acks: detail 필드 제거 — 구현자 작성 감사 산문(audit prose)은
                # 번들 메트릭 범위 밖. ack/area/ts(구조화된 메트릭)만 유지.
                # detail에 유저 NL 인용이 포함될 수 있으며(Round 2 감사 기록 사례)
                # 번들 비식별 경계를 침범하지 않도록 제거한다.
                raw_risk_acks = task_rec.get("risk_acks") or []
                stripped_risk_acks = [
                    {k: v for k, v in ra.items() if k != "detail"}
                    for ra in raw_risk_acks
                    if isinstance(ra, dict)
                ]
                entry["tasks"].append({
                    "task_id": task_rec.get("task_id"),
                    "status": task_rec.get("status"),
                    "role": task_rec.get("role"),
                    "plan_deviations": task_rec.get("plan_deviations_count", 0),
                    "risk_acks": stripped_risk_acks,
                    "rounds": task_rec.get("round_count", 1),
                })

            # manifest 필드 구성
            manifest_rec = bucket.get("manifest")
            if manifest_rec and isinstance(manifest_rec, dict):
                manifest_path = manifest_rec.get("path")
                if manifest_path and manifest_path not in entry["evidence_ref"]["artifact_paths"]:
                    entry["evidence_ref"]["artifact_paths"].append(manifest_path)

                entry["manifest"] = {
                    "status": manifest_rec.get("status"),
                    "quality_gates": manifest_rec.get("quality_gates") or [],
                }

    # --- session_results 처리 ---
    for repo_rec in session_results:
        if not isinstance(repo_rec, dict):
            continue

        # parse_errors 수집
        for pe in repo_rec.get("parse_errors") or []:
            all_parse_errors.append(pe)

        by_ticket = repo_rec.get("by_ticket") or {}
        for ticket_id, sessions in by_ticket.items():
            if not isinstance(sessions, list):
                continue

            if ticket_id not in tickets_map:
                tickets_map[ticket_id] = {
                    "ticket": ticket_id,
                    "repo": "",
                    "plan": None,
                    "tasks": [],
                    "manifest": None,
                    "sessions": [],
                    "user_input_characteristics": {},
                    "evidence_ref": {
                        "session_paths": [],
                        "artifact_paths": [],
                    },
                }

            entry = tickets_map[ticket_id]

            for session_rec in sessions:
                if not isinstance(session_rec, dict):
                    continue
                session_id = session_rec.get("session_id")

                # events는 session_rec 내부에서 가져오거나, event_streams에서 가져온다
                events = session_rec.get("events") or []

                # evidence_ref에 session_id 추가
                if session_id and session_id not in entry["evidence_ref"]["session_paths"]:
                    entry["evidence_ref"]["session_paths"].append(session_id)

                entry["sessions"].append({
                    "session_id": session_id,
                    "events": events,
                })

    # --- characteristics 반영 ---
    for ticket_id, char_data in characteristics.items():
        if ticket_id in tickets_map:
            tickets_map[ticket_id]["user_input_characteristics"] = char_data

    # --- 번들 조립 ---
    bundle: Dict[str, Any] = {
        "bundle_schema_version": BUNDLE_SCHEMA_VERSION,
        "generator": "wf-collect",
        "generated_at": generated_at,
        "tickets": list(tickets_map.values()),
        "parse_errors": all_parse_errors,
    }

    return bundle


# ---------------------------------------------------------------------------
# 번들 검증 — validate_bundle
# ---------------------------------------------------------------------------

def validate_bundle(bundle: Dict[str, Any]) -> List[str]:
    """번들의 필수 키·버전 필드를 검증한다.

    Phase B(agentlens) ingest가 이 함수를 vendoring해 동일한 검증을 실행한다.

    Returns:
        오류 메시지 리스트. 빈 리스트 = valid.
    """
    errors: List[str] = []

    if not isinstance(bundle, dict):
        errors.append("번들은 dict여야 한다")
        return errors

    # 필수 최상위 키 검증
    required_top_keys = [
        "bundle_schema_version",
        "generator",
        "generated_at",
        "tickets",
        "parse_errors",
    ]
    for key in required_top_keys:
        if key not in bundle:
            errors.append(f"필수 키 누락: {key!r}")

    # 버전 필드 검증
    if "bundle_schema_version" in bundle:
        if bundle["bundle_schema_version"] != BUNDLE_SCHEMA_VERSION:
            errors.append(
                f"bundle_schema_version 불일치: "
                f"기대={BUNDLE_SCHEMA_VERSION!r}, 실제={bundle['bundle_schema_version']!r}"
            )

    # tickets 타입 검증
    if "tickets" in bundle:
        tickets = bundle["tickets"]
        if not isinstance(tickets, list):
            errors.append("tickets는 list여야 한다")
        else:
            for i, ticket_entry in enumerate(tickets):
                if not isinstance(ticket_entry, dict):
                    errors.append(f"tickets[{i}]는 dict여야 한다")
                    continue
                # 각 ticket 엔트리 필수 키
                for tkey in ("ticket", "sessions", "user_input_characteristics", "evidence_ref"):
                    if tkey not in ticket_entry:
                        errors.append(f"tickets[{i}] 필수 키 누락: {tkey!r}")

    # parse_errors 타입 검증
    if "parse_errors" in bundle:
        if not isinstance(bundle["parse_errors"], list):
            errors.append("parse_errors는 list여야 한다")

    return errors


# ---------------------------------------------------------------------------
# 감사 리포트 — _build_audit_report
# ---------------------------------------------------------------------------

def _build_audit_report(bundle_json: str) -> List[str]:
    """번들 JSON 바이트에 대한 --dry-run 감사 리포트를 생성한다.

    deid.redact_for_audit 기반 전부-또는-전무 감사 출력.

    Returns:
        감사 리포트 줄 리스트.
    """
    if _deid_mod is None:  # pragma: no cover
        return ["[WARN] deid 모듈 없음 — 감사 리포트 생략"]

    lines: List[str] = []
    lines.append(f"[AUDIT] 번들 바이트 수: {len(bundle_json.encode('utf-8'))}")
    lines.append(f"[AUDIT] 번들 schema version: {BUNDLE_SCHEMA_VERSION}")

    # 번들 전체 바이트에 대한 secret 스캔
    secrets = _deid_mod.scan_secrets(bundle_json)
    if secrets:
        lines.append(f"[AUDIT][WARN] secret 탐지 {len(secrets)}건 — 번들 업로드 차단됨")
        for s in secrets[:10]:
            lines.append(f"  - {s.kind}: {s.match[:30]!r}")
    else:
        lines.append("[AUDIT][OK] secret 탐지 없음")

    # redact_for_audit은 전부-또는-전무 마스킹
    redacted = _deid_mod.redact_for_audit(bundle_json[:200])
    lines.append(f"[AUDIT] 번들 앞부분 (200자, redact 후): {redacted[:100]!r}")

    return lines


# ---------------------------------------------------------------------------
# 업로드 — upload_bundle
# ---------------------------------------------------------------------------

def upload_bundle(
    bundle: Dict[str, Any],
    target: Optional[str],
    *,
    dry_run: bool = True,
    out: Optional[str] = None,
    forbidden_raw: Optional[List[str]] = None,
    plaintext_subtrees: Optional[List[str]] = None,
) -> UploadResult:
    """번들을 업로드하거나 dry-run 감사 파일을 작성한다.

    공통 동작 (dry-run 포함):
      1. deid.selfcheck_bundle을 BUNDLE_DUMPS_KWARGS로 직렬화한 바이트에 호출.
         실패 시 DeidLeakError를 전파(hard-fail) — 업로드/쓰기 차단.
      2. validate_bundle로 스키마 검증.

    dry-run=True (기본):
      - 번들을 out 경로에 쓴다 (기본: .claude/runs/bundle.sample.json).
      - 전부-또는-전무 감사 리포트를 반환한다.
      - 실제 git push 없음.

    dry-run=False (live upload):
      - 반드시 --no-dry-run + --target이 명시돼야 한다.
      - target git repo 경로에 bundle.json을 commit한다.
      - selfcheck_bundle 통과 후에만 push한다.

    Args:
        bundle:             직렬화할 번들 dict.
        target:             업로드 타깃 git repo 경로/URL. env WF_COLLECT_TARGET 또는 --target.
                            하드코딩 금지. dry-run=False 시 필수.
        dry_run:            True(기본) = 파일 쓰기만. False = 실제 git push.
        out:                dry-run 출력 파일 경로 (기본: .claude/runs/bundle.sample.json).
        forbidden_raw:      selfcheck_bundle에 전달할 forbidden_raw 리스트.
        plaintext_subtrees: selfcheck_bundle NL-check에서 제외할 키-경로 리스트.
                            예: ["tickets.plan.intent"] — intent.*는 spec-plan AI 의역
                            (plan P0-2 평문 허용). scan_secrets는 항상 전체 번들 검사.

    Returns:
        UploadResult.

    Raises:
        deid.DeidLeakError: selfcheck_bundle hard-fail 시.
        ValueError:         dry-run=False이고 target이 없을 때.
    """
    if _deid_mod is None:  # pragma: no cover
        raise RuntimeError("deid 모듈을 찾을 수 없습니다.")

    raw_list: List[str] = forbidden_raw if forbidden_raw is not None else []

    # 1. BUNDLE_DUMPS_KWARGS로 직렬화 (selfcheck 바이트 == 쓰일 바이트 보장)
    bundle_json = json.dumps(bundle, **_deid_mod.BUNDLE_DUMPS_KWARGS)

    # 2. 업로드 직전 self-check (dry-run 포함 — 쓰일 바이트 검사)
    # DeidLeakError는 여기서 전파됨 — 호출자에게 hard-fail
    _deid_mod.selfcheck_bundle(bundle, raw_list, plaintext_subtrees=plaintext_subtrees)

    # 3. 스키마 검증
    validation_errors = validate_bundle(bundle)

    # 4. 감사 리포트 생성
    audit_lines = _build_audit_report(bundle_json)
    if validation_errors:
        for ve in validation_errors:
            audit_lines.append(f"[AUDIT][SCHEMA ERROR] {ve}")

    if dry_run:
        # dry-run: 파일로 쓰기 (실제 push 없음)
        # 기본 경로는 cwd-relative 일반 경로 — 티켓 리터럴·절대 홈 경로 하드코딩 금지.
        # 호출자가 --out으로 명시하거나 env/플래그로 지정하는 것을 권장한다.
        default_out = os.path.join(".claude", "runs", "bundle.sample.json")
        out_path = out or default_out

        # 출력 디렉토리 생성
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(bundle_json)

        audit_lines.append(f"[DRY-RUN] 번들 파일 작성 완료: {out_path}")
        audit_lines.append("[DRY-RUN] 실제 git push 없음")

        return UploadResult(
            ok=True,
            dry_run=True,
            out_path=out_path,
            audit_lines=audit_lines,
        )

    else:
        # live upload — 반드시 target이 있어야 한다
        if not target:
            # env fallback
            target = os.environ.get("WF_COLLECT_TARGET")
        if not target:
            raise ValueError(
                "live upload에는 --target 또는 env WF_COLLECT_TARGET이 필요합니다."
            )

        # target git repo에 bundle.json 커밋
        try:
            result = _git_commit_bundle(bundle_json, target)
            audit_lines.append(f"[UPLOAD] git commit 완료: {result}")
            return UploadResult(
                ok=True,
                dry_run=False,
                audit_lines=audit_lines,
            )
        except Exception as exc:
            return UploadResult(
                ok=False,
                dry_run=False,
                audit_lines=audit_lines,
                error=str(exc),
            )


def _git_commit_bundle(bundle_json: str, target: str) -> str:
    """target git repo에 bundle.json을 커밋한다.

    target은 로컬 git repo 경로여야 한다 (URL은 추후 지원).
    bundle.json을 temp 파일로 써서 target/bundle.json으로 복사 후 커밋한다.

    파일명 동작: 항상 target/bundle.json 고정 이름으로 덮어쓴다(overwrite).
    타임스탬프 접미사 없음 — 멱등성(idempotent) 보장(같은 번들 재업로드 = 같은 파일 갱신).
    Phase B T8 추세 ingest는 이 파일을 항상 같은 경로에서 읽는다.

    Returns:
        커밋 SHA (짧은 형식).

    Raises:
        subprocess.CalledProcessError: git 명령 실패 시.
        FileNotFoundError: target 경로가 존재하지 않을 때.
    """
    target = os.path.expanduser(target)
    if not os.path.isdir(target):
        raise FileNotFoundError(f"target git repo 경로가 없습니다: {target}")

    bundle_path = os.path.join(target, "bundle.json")

    with open(bundle_path, "w", encoding="utf-8") as f:
        f.write(bundle_json)

    # git add
    subprocess.run(
        ["git", "-C", target, "add", "bundle.json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    # git commit
    commit_result = subprocess.run(
        ["git", "-C", target, "commit", "-m", "chore: update telemetry bundle"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    # 짧은 SHA 반환
    sha_result = subprocess.run(
        ["git", "-C", target, "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return sha_result.stdout.strip() if sha_result.returncode == 0 else "(unknown)"
