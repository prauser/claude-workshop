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


def serialize_bundle(data: dict, out: Optional[str] = None) -> dict:  # TODO(task-5)
    """번들 직렬화 + 업로드 스텁(stub). T5에서 구현."""
    return {}


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

    return parser


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

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
