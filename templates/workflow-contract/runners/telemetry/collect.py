#!/usr/bin/env python3
"""
collect.py — 워크플로 텔레메트리 수집기 CLI 엔트리포인트 + 스테이지 오케스트레이터 골격.
외부 의존 0 — stdlib만 사용.

파이프라인 스테이지:
  discover         → 코퍼스 디스커버리 (T1, 이 파일)
  harvest_artifacts → 산출물 frontmatter harvest (TODO task-2)
  harvest_sessions  → 세션로그 메타 harvest (TODO task-3)
  deidentify        → 비식별(de-identification) (TODO task-4)
  serialize_bundle  → 번들 직렬화 + 업로드 (TODO task-5)
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# discover 모듈 모듈-레벨 임포트(import) — 같은 디렉토리를 sys.path에 추가
# ---------------------------------------------------------------------------

def _ensure_sys_path() -> None:
    """collect.py가 위치한 디렉토리를 sys.path에 추가 — 상대 임포트 허용."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


_ensure_sys_path()

try:
    import discover  # type: ignore
except ImportError:  # pragma: no cover — discover.py 부재 시 graceful 처리
    discover = None  # type: ignore

try:
    import harvest_artifacts as _harvest_mod  # type: ignore
except ImportError:  # pragma: no cover — harvest_artifacts.py 부재 시 graceful 처리
    _harvest_mod = None  # type: ignore

try:
    import harvest_sessions as _harvest_sessions_mod  # type: ignore
except ImportError:  # pragma: no cover — harvest_sessions.py 부재 시 graceful 처리
    _harvest_sessions_mod = None  # type: ignore

try:
    import deid as _deid_mod  # type: ignore
except ImportError:  # pragma: no cover — deid.py 부재 시 graceful 처리
    _deid_mod = None  # type: ignore

try:
    import bundle as _bundle_mod  # type: ignore
except ImportError:  # pragma: no cover — bundle.py 부재 시 graceful 처리
    _bundle_mod = None  # type: ignore


# ---------------------------------------------------------------------------
# 모듈-레벨 임계값 상수 — 테스트에서 임포트 가능
# ---------------------------------------------------------------------------

# selfcheck 슬라이딩 윈도우 최솟값: 4 토큰 미만은 단일 단어가 번들 메타데이터에 자연 등장해
# false-positive를 일으킬 수 있다 ("ok", "네" 등). deid._WINDOW_MIN_TOKENS와 동일.
FORBIDDEN_MIN_TOKENS = 4


# ---------------------------------------------------------------------------
# 스테이지 구현 / 스텁(stub)
# ---------------------------------------------------------------------------


def harvest_artifacts(repos: list) -> list:
    """산출물 frontmatter harvest. harvest_artifacts.py 의 harvest_repo 호출."""
    if _harvest_mod is None:  # pragma: no cover
        return []
    results = []
    for corpus in repos:
        rec = _harvest_mod.harvest_repo(corpus)
        results.append(rec)
    return results


def harvest_sessions(repos: list) -> list:
    """세션로그 메타 harvest — harvest_sessions.py 의 harvest_sessions_for_repo 호출.

    반환 레코드에는 raw_user_turns_by_session이 포함된다 (로컬 전용 — 번들 직행 금지).
    collect 파이프라인이 forbidden_raw 조립에 사용한다.
    """
    if _harvest_sessions_mod is None:  # pragma: no cover
        return []
    results = []
    for corpus in repos:
        rec = _harvest_sessions_mod.harvest_sessions_for_repo(corpus)
        results.append(rec)
    return results


def assemble_forbidden_raw(
    artifact_results: List[Any],
    session_results: List[Any],
) -> List[str]:
    """forbidden_raw를 조립한다 — plan user_prompt + 모든 session raw_user_turns.

    이 함수의 반환값은 로컬 전용이다 — 번들에 직렬화하지 않는다.
    deid.selfcheck_bundle 호출에만 사용한다.

    Args:
        artifact_results: harvest_artifacts 반환 리스트 (harvest_repo 레코드 목록).
        session_results:  harvest_sessions 반환 리스트 (harvest_sessions_for_repo 레코드 목록).

    Returns:
        raw NL 원문 문자열 리스트 (plan user_prompt + raw_user_turns 전체).
    """
    forbidden: List[str] = []

    if _harvest_mod is not None:
        # 각 artifact result의 by_ticket 버킷에서 plan_path를 수집해 user_prompt 추출
        for repo_rec in artifact_results:
            if not isinstance(repo_rec, dict):
                continue
            by_ticket = repo_rec.get("by_ticket") or {}
            for _ticket, bucket in by_ticket.items():
                if not isinstance(bucket, dict):
                    continue
                plan_rec = bucket.get("plan")
                if not isinstance(plan_rec, dict):
                    continue
                plan_path = plan_rec.get("plan_path")
                if plan_path:
                    prompt = _harvest_mod.get_plan_user_prompt(plan_path)
                    if prompt:
                        forbidden.append(prompt)

    # 세션 raw_user_turns 수집
    for repo_rec in session_results:
        if not isinstance(repo_rec, dict):
            continue
        raw_by_session = repo_rec.get("raw_user_turns_by_session") or {}
        for _session_id, turns in raw_by_session.items():
            if isinstance(turns, list):
                for turn in turns:
                    if turn:
                        forbidden.append(turn)

    return forbidden


# ---------------------------------------------------------------------------
# harvest-sessions 서브커맨드 핸들러
# ---------------------------------------------------------------------------


def cmd_harvest_sessions(args: argparse.Namespace) -> None:
    """harvest-sessions 서브커맨드: 세션로그 메타 harvest 결과를 JSON으로 stdout 출력."""
    if discover is None:  # pragma: no cover
        print(json.dumps({"error": "discover 모듈을 찾을 수 없습니다."}), file=sys.stderr)
        sys.exit(1)
    if _harvest_sessions_mod is None:  # pragma: no cover
        print(json.dumps({"error": "harvest_sessions 모듈을 찾을 수 없습니다."}), file=sys.stderr)
        sys.exit(1)

    roots = args.roots if args.roots else ["~/sbx-work"]
    repos = discover.discover_repos(roots)

    # --ticket 필터: discover 서브커맨드와 동일한 로직 적용
    if args.ticket:
        filtered = []
        for repo in repos:
            if repo.plans_dir:
                ticket_plan_dir = os.path.join(repo.plans_dir, args.ticket)
                if os.path.isdir(ticket_plan_dir):
                    filtered.append(repo)
        repos = filtered

    results = harvest_sessions(repos)

    output: Dict[str, Any] = {
        "repo_count": len(repos),
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


def deidentify(bundle_obj: dict, forbidden_raw: Optional[List[str]] = None) -> dict:
    """비식별(de-identification) 게이트 — secret 스캔 + 런타임 self-check.

    deid.selfcheck_bundle을 호출해 번들 객체에 forbidden_raw 원문이나 secret이 없는지
    검증한다. self-check 실패 시 deid.DeidLeakError가 raise되며(hard-fail) 이 함수
    밖으로 전파된다. 통과 객체만 호출자(caller)에게 반환된다.

    Args:
        bundle_obj:    self-check할 번들 딕셔너리.
        forbidden_raw: 추상화 입력이었던 raw NL 리스트(plan user_prompt + raw_user_turns).
                       None이면 빈 리스트로 처리한다.

    Returns:
        self-check를 통과한 bundle_obj 그대로.

    Raises:
        deid.DeidLeakError: 누출 탐지 시 hard-fail.
        RuntimeError:       deid 모듈을 임포트할 수 없을 때.
    """
    if _deid_mod is None:  # pragma: no cover
        raise RuntimeError("deid 모듈을 찾을 수 없습니다. deid.py가 같은 디렉토리에 있는지 확인하세요.")
    raw_list: List[str] = forbidden_raw if forbidden_raw is not None else []
    # scan_secrets는 selfcheck_bundle 내부에서 번들 직렬화 바이트에 대해 호출된다.
    _deid_mod.selfcheck_bundle(bundle_obj, raw_list)
    # 통과 시 원본 객체 반환 — 복사하지 않는다(upstream이 동일 참조 유지 필요 가능성).
    return bundle_obj


def serialize_bundle_stage(
    artifact_results: List[Any],
    session_results: List[Any],
    characteristics: Optional[Dict[str, Any]] = None,
    *,
    generated_at: str,
) -> Dict[str, Any]:
    """번들 직렬화 스테이지 — bundle.serialize_bundle 호출.

    Args:
        artifact_results: harvest_artifacts 반환 리스트.
        session_results:  harvest_sessions 반환 리스트.
        characteristics:  ticket → user_input_characteristics 매핑 (T4 추상화 산출).
                          None이면 빈 dict로 처리.
        generated_at:     번들 생성 타임스탬프 (INJECT받는다 — datetime.now() 금지).

    Returns:
        번들 dict.

    Raises:
        RuntimeError: bundle 모듈을 임포트할 수 없을 때.
    """
    if _bundle_mod is None:  # pragma: no cover
        raise RuntimeError("bundle 모듈을 찾을 수 없습니다. bundle.py가 같은 디렉토리에 있는지 확인하세요.")

    harvested: Dict[str, Any] = {
        "artifact_results": artifact_results,
        "session_results": session_results,
    }
    return _bundle_mod.serialize_bundle(
        harvested,
        characteristics or {},
        generated_at=generated_at,
    )


def upload_bundle_stage(
    bundle_obj: Dict[str, Any],
    target: Optional[str],
    *,
    dry_run: bool = True,
    out: Optional[str] = None,
    forbidden_raw: Optional[List[str]] = None,
    plaintext_subtrees: Optional[List[str]] = None,
) -> Any:
    """업로드 스테이지 — bundle.upload_bundle 호출.

    Args:
        bundle_obj:         직렬화할 번들 dict.
        target:             업로드 타깃 (env WF_COLLECT_TARGET 또는 --target).
        dry_run:            True(기본) = 파일 쓰기만. False = 실제 git push.
        out:                dry-run 출력 파일 경로.
        forbidden_raw:      selfcheck_bundle에 전달할 forbidden_raw 리스트.
        plaintext_subtrees: selfcheck_bundle NL-check에서 제외할 키-경로 리스트.
                            예: ["tickets.plan.intent"] — intent.*는 spec-plan AI 의역 평문.

    Returns:
        bundle.UploadResult.

    Raises:
        RuntimeError:       bundle 모듈을 임포트할 수 없을 때.
        deid.DeidLeakError: selfcheck_bundle hard-fail 시.
    """
    if _bundle_mod is None:  # pragma: no cover
        raise RuntimeError("bundle 모듈을 찾을 수 없습니다.")

    return _bundle_mod.upload_bundle(
        bundle_obj,
        target,
        dry_run=dry_run,
        out=out,
        forbidden_raw=forbidden_raw,
        plaintext_subtrees=plaintext_subtrees,
    )


# ---------------------------------------------------------------------------
# discover 서브커맨드 핸들러
# ---------------------------------------------------------------------------


def cmd_discover(args: argparse.Namespace) -> None:
    """discover 서브커맨드: 레포 디스커버리 결과를 JSON으로 stdout 출력."""
    if discover is None:  # pragma: no cover
        print(json.dumps({"error": "discover 모듈을 찾을 수 없습니다."}), file=sys.stderr)
        sys.exit(1)

    roots = args.roots if args.roots else ["~/sbx-work"]
    repos = discover.discover_repos(roots)

    summary: Dict[str, Any] = {
        "repo_count": len(repos),
        "repos": [],
    }

    for repo in repos:
        entry: Dict[str, Any] = {
            "repo_path": repo.repo_path,
            "name": repo.name,
            "session_dir": repo.session_dir,
            "has_plans": repo.plans_dir is not None,
            "has_runs": repo.runs_dir is not None,
            "tasks_dirs": repo.tasks_dirs,
        }

        # --ticket 필터: 특정 티켓만 포함할지 선택
        if args.ticket:
            # plans 디렉토리 아래에 해당 티켓 디렉토리가 있을 때만 포함
            if repo.plans_dir:
                ticket_plan_dir = os.path.join(repo.plans_dir, args.ticket)
                if not os.path.isdir(ticket_plan_dir):
                    continue
            else:
                continue

        summary["repos"].append(entry)

    if args.ticket:
        summary["repo_count"] = len(summary["repos"])

    print(json.dumps(summary, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# harvest-artifacts 서브커맨드 핸들러
# ---------------------------------------------------------------------------


def cmd_harvest_artifacts(args: argparse.Namespace) -> None:
    """harvest-artifacts 서브커맨드: 산출물 frontmatter harvest 결과를 JSON으로 stdout 출력."""
    if discover is None:  # pragma: no cover
        print(json.dumps({"error": "discover 모듈을 찾을 수 없습니다."}), file=sys.stderr)
        sys.exit(1)
    if _harvest_mod is None:  # pragma: no cover
        print(json.dumps({"error": "harvest_artifacts 모듈을 찾을 수 없습니다."}), file=sys.stderr)
        sys.exit(1)

    roots = args.roots if args.roots else ["~/sbx-work"]
    repos = discover.discover_repos(roots)

    # --ticket 필터: discover 서브커맨드와 동일한 로직 적용
    if args.ticket:
        filtered = []
        for repo in repos:
            if repo.plans_dir:
                ticket_plan_dir = os.path.join(repo.plans_dir, args.ticket)
                if os.path.isdir(ticket_plan_dir):
                    filtered.append(repo)
            # plans_dir 없는 레포는 ticket 필터에 맞지 않으므로 제외
        repos = filtered

    results = harvest_artifacts(repos)

    output: Dict[str, Any] = {
        "repo_count": len(repos),
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


# ---------------------------------------------------------------------------
# argparse 설정
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collect.py",
        description="워크플로 텔레메트리 수집기(workflow telemetry collector). 명시 실행만.",
    )

    # 전역 플래그
    parser.add_argument(
        "--roots",
        nargs="+",
        metavar="PATH",
        default=None,
        help="디스커버리(discovery) 루트(root) 목록 (기본: ~/sbx-work)",
    )
    parser.add_argument(
        "--ticket",
        metavar="TICKET",
        default=None,
        help="특정 티켓만 처리 (예: PRA-109)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="드라이런(dry-run) 모드 — 번들 업로드 없이 감사(audit)만. T5에서 활성화.",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        default=None,
        help="번들 출력 경로. T5에서 활성화.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # discover 서브커맨드
    discover_sub = subparsers.add_parser(
        "discover",
        help="코퍼스 디스커버리 — 결과를 JSON으로 stdout 출력",
    )
    discover_sub.add_argument(
        "--roots",
        nargs="+",
        metavar="PATH",
        default=None,
        help="디스커버리(discovery) 루트(root) 목록 (기본: ~/sbx-work). 서브커맨드 로컬 플래그.",
    )
    discover_sub.add_argument(
        "--ticket",
        metavar="TICKET",
        default=None,
        help="특정 티켓만 처리 (서브커맨드 로컬 플래그).",
    )

    # harvest-artifacts 서브커맨드
    harvest_sub = subparsers.add_parser(
        "harvest-artifacts",
        help="산출물 frontmatter harvest — 결과를 JSON으로 stdout 출력",
    )
    harvest_sub.add_argument(
        "--roots",
        nargs="+",
        metavar="PATH",
        default=None,
        help="디스커버리(discovery) 루트(root) 목록 (기본: ~/sbx-work). 서브커맨드 로컬 플래그.",
    )
    harvest_sub.add_argument(
        "--ticket",
        metavar="TICKET",
        default=None,
        help="특정 티켓만 처리 (서브커맨드 로컬 플래그).",
    )

    # harvest-sessions 서브커맨드
    harvest_sessions_sub = subparsers.add_parser(
        "harvest-sessions",
        help="세션로그 메타 harvest — 결과를 JSON으로 stdout 출력",
    )
    harvest_sessions_sub.add_argument(
        "--roots",
        nargs="+",
        metavar="PATH",
        default=None,
        help="디스커버리(discovery) 루트(root) 목록 (기본: ~/sbx-work). 서브커맨드 로컬 플래그.",
    )
    harvest_sessions_sub.add_argument(
        "--ticket",
        metavar="TICKET",
        default=None,
        help="특정 티켓만 처리 (서브커맨드 로컬 플래그).",
    )

    # run 서브커맨드 — 전체 파이프라인: discover→harvest→deidentify→serialize→upload
    run_sub = subparsers.add_parser(
        "run",
        help="전체 파이프라인 실행: discover→harvest-artifacts→harvest-sessions→deidentify→serialize_bundle→upload",
    )
    run_sub.add_argument(
        "--roots",
        nargs="+",
        metavar="PATH",
        default=None,
        help="디스커버리(discovery) 루트(root) 목록 (기본: ~/sbx-work).",
    )
    run_sub.add_argument(
        "--ticket",
        metavar="TICKET",
        default=None,
        help="특정 티켓만 처리.",
    )
    run_sub.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="드라이런(dry-run) 모드 (기본: ON). --no-dry-run으로 해제.",
    )
    run_sub.add_argument(
        "--no-dry-run",
        action="store_false",
        dest="dry_run",
        help="실제 git push 활성화. --target도 함께 필요.",
    )
    run_sub.add_argument(
        "--out",
        metavar="PATH",
        default=None,
        help="번들 출력 경로 (기본: .claude/runs/PRA-109/bundle.sample.json).",
    )
    run_sub.add_argument(
        "--target",
        metavar="REPO_PATH",
        default=None,
        help="업로드 타깃 git repo 경로/URL. env WF_COLLECT_TARGET으로도 설정 가능.",
    )
    run_sub.add_argument(
        "--generated-at",
        metavar="ISO8601",
        default=None,
        help="번들 생성 타임스탬프 주입. 미지정 시 호출 셸이 date -Iseconds로 주입해야 한다.",
    )

    return parser


def cmd_run(args: argparse.Namespace) -> int:
    """run 서브커맨드: 전체 파이프라인 실행.

    파이프라인: discover → harvest-artifacts → harvest-sessions →
               assemble_forbidden_raw → deidentify(self-check) →
               serialize_bundle → upload(dry-run 기본).

    --generated-at 미지정 시: 호출 셸이 `date -Iseconds` 값을 주입해야 한다.
    이 함수 내부에서 datetime.now()를 호출하지 않는다 (결정성 보장).
    """
    if discover is None:  # pragma: no cover
        print(json.dumps({"error": "discover 모듈을 찾을 수 없습니다."}), file=sys.stderr)
        return 1
    if _harvest_mod is None:  # pragma: no cover
        print(json.dumps({"error": "harvest_artifacts 모듈을 찾을 수 없습니다."}), file=sys.stderr)
        return 1
    if _harvest_sessions_mod is None:  # pragma: no cover
        print(json.dumps({"error": "harvest_sessions 모듈을 찾을 수 없습니다."}), file=sys.stderr)
        return 1
    if _bundle_mod is None:  # pragma: no cover
        print(json.dumps({"error": "bundle 모듈을 찾을 수 없습니다."}), file=sys.stderr)
        return 1

    # generated_at 검증: 코드에서 생성 금지 — 반드시 주입받아야 한다
    generated_at: Optional[str] = getattr(args, "generated_at", None)
    if not generated_at:
        print(
            "[ERROR] --generated-at 이 필요합니다. "
            "예: --generated-at \"$(date -Iseconds)\"",
            file=sys.stderr,
        )
        return 1

    # 1. 디스커버리(discover)
    roots = getattr(args, "roots", None) or ["~/sbx-work"]
    repos = discover.discover_repos(roots)

    # --ticket 필터
    ticket_filter: Optional[str] = getattr(args, "ticket", None)
    if ticket_filter:
        filtered = []
        for repo in repos:
            if repo.plans_dir:
                ticket_plan_dir = os.path.join(repo.plans_dir, ticket_filter)
                if os.path.isdir(ticket_plan_dir):
                    filtered.append(repo)
        repos = filtered

    print(f"[RUN] discover 완료: {len(repos)}개 레포", file=sys.stderr)

    # 2. harvest-artifacts
    artifact_results = harvest_artifacts(repos)
    print(f"[RUN] harvest-artifacts 완료: {len(artifact_results)}개 레포 산출물", file=sys.stderr)

    # 3. harvest-sessions
    session_results = harvest_sessions(repos)
    print(f"[RUN] harvest-sessions 완료: {len(session_results)}개 레포 세션", file=sys.stderr)

    # 4. forbidden_raw 조립 (assemble_forbidden_raw)
    forbidden_raw = assemble_forbidden_raw(artifact_results, session_results)
    print(f"[RUN] forbidden_raw 조립 완료: {len(forbidden_raw)}개 항목", file=sys.stderr)

    # 5. characteristics 조립 — T4 LLM 추상화 대체 샘플 특성 (Phase B fixture 용)
    #    실제 LLM 추상화는 /wf-collect 커맨드(claude-config)가 담당한다.
    #    collect.py run 기본 실행은 샘플 특성을 사용한다.
    characteristics: Dict[str, Any] = {}
    # artifact_results에서 ticket 목록 수집해 샘플 특성 생성
    for repo_rec in artifact_results:
        if not isinstance(repo_rec, dict):
            continue
        for ticket_id in (repo_rec.get("by_ticket") or {}).keys():
            characteristics[ticket_id] = {
                "length_band": "M",
                "has_ticket_ref": True,
                "request_shape": "feature",
                "specificity": "med",
                "mentions_external_tool": False,
                "language": "ko",
            }
    for repo_rec in session_results:
        if not isinstance(repo_rec, dict):
            continue
        for ticket_id in (repo_rec.get("by_ticket") or {}).keys():
            if ticket_id not in characteristics:
                characteristics[ticket_id] = {
                    "length_band": "M",
                    "has_ticket_ref": True,
                    "request_shape": "feature",
                    "specificity": "med",
                    "mentions_external_tool": False,
                    "language": "ko",
                }

    # 6. forbidden_raw 필터링:
    #    하한(≥ FORBIDDEN_MIN_TOKENS): selfcheck 슬라이딩 윈도우 최솟값 미만은 false-positive 유발
    #    ("ok", "네" 등 단어가 번들 메타데이터에 자연 등장).
    #
    #    상한 없음 (Round 3 수정): Round 2에서 ≤100 토큰 상한을 적용했으나 이는 P0 백스톱 구멍이었다.
    #    100단어 초과 유저 입력은 self-check 대상에서 제외됐었다. Round 3에서 두 root cause를 직접 수정:
    #    (a) p2-a: isMeta=True 유저 턴(CLAUDE.md/커맨드 주입)을 harvest_sessions에서 소스 배제.
    #    (b) p2-b: intent.* 평문 서브트리를 NL-check에서 제외(plaintext_subtrees).
    #    이 두 수정으로 false-positive 원인이 제거됐으므로 상한 제거가 안전하다.
    forbidden_raw_filtered = [
        r for r in forbidden_raw
        if len(r.split()) >= FORBIDDEN_MIN_TOKENS
    ]
    print(
        f"[RUN] forbidden_raw 조립됨({len(forbidden_raw)}개) — "
        f"필터 후 {len(forbidden_raw_filtered)}개 항목을 self-check에 전달",
        file=sys.stderr,
    )

    # 7. serialize_bundle
    try:
        bundle_obj = serialize_bundle_stage(
            artifact_results,
            session_results,
            characteristics,
            generated_at=generated_at,
        )
    except Exception as exc:
        print(f"[ERROR] serialize_bundle 실패: {exc}", file=sys.stderr)
        return 1
    print("[RUN] serialize_bundle 완료", file=sys.stderr)

    # 8. upload (dry-run 기본)
    #    forbidden_raw_filtered + plaintext_subtrees를 upload_bundle에 전달.
    #    intent.*는 spec-plan AI 의역 평문(plan P0-2) — NL-check 대상 아님.
    #    scan_secrets는 항상 전체 번들 바이트에 수행된다.
    dry_run: bool = getattr(args, "dry_run", True)
    out: Optional[str] = getattr(args, "out", None)
    target: Optional[str] = getattr(args, "target", None) or os.environ.get("WF_COLLECT_TARGET")

    # 번들 스키마에서 평문 허용 서브트리 (NL-check 제외 대상):
    #   tickets[].plan.intent          — spec-plan 생성 AI 의역 내러티브 (plan P0-2 평문 허용)
    #   tickets[].plan.intent_history  — intent 변경 이력(prev_value/reason). intent.* 와
    #                                    동일 클래스의 spec-plan 생성 평문 — raw 유저 NL 아님.
    # 보수적 제외: 위 두 서브트리만 NL-check 면제, 나머지 필드는 모두 검사.
    # Note: tasks[].risk_acks.detail은 bundle.serialize_bundle에서 이미 제거된다
    #       (감사 산문은 번들 메트릭 범위 밖 — bundle.py 참조).
    # scan_secrets는 항상 전체 번들 바이트에 실행된다.
    _INTENT_SUBTREES = ["tickets.plan.intent", "tickets.plan.intent_history"]

    try:
        result = upload_bundle_stage(
            bundle_obj,
            target,
            dry_run=dry_run,
            out=out,
            forbidden_raw=forbidden_raw_filtered,
            plaintext_subtrees=_INTENT_SUBTREES,
        )
    except Exception as exc:
        # DeidLeakError 포함
        print(f"[ERROR] upload_bundle 실패 (self-check hard-fail 포함): {exc}", file=sys.stderr)
        return 1

    # 감사 리포트 출력
    for line in result.audit_lines:
        print(line, file=sys.stderr)

    if result.ok:
        if result.dry_run:
            print(f"[RUN][OK] dry-run 완료. 번들 파일: {result.out_path}", file=sys.stderr)
        else:
            print("[RUN][OK] live upload 완료.", file=sys.stderr)
        return 0
    else:
        print(f"[RUN][FAIL] upload 실패: {result.error}", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "discover":
        cmd_discover(args)
        return 0

    if args.command == "harvest-artifacts":
        cmd_harvest_artifacts(args)
        return 0

    if args.command == "harvest-sessions":
        cmd_harvest_sessions(args)
        return 0

    if args.command == "run":
        return cmd_run(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
