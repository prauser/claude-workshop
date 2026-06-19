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


# ---------------------------------------------------------------------------
# 스테이지 스텁(stub) — T2~T5에서 구현
# ---------------------------------------------------------------------------


def harvest_artifacts(repos: list) -> list:  # TODO(task-2)
    """산출물 frontmatter harvest 스텁(stub). T2에서 구현."""
    return []


def harvest_sessions(repos: list) -> list:  # TODO(task-3)
    """세션로그 메타 harvest 스텁(stub). T3에서 구현."""
    return []


def deidentify(data: dict) -> dict:  # TODO(task-4)
    """비식별(de-identification) 스텁(stub). T4에서 구현."""
    return data


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

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "discover":
        cmd_discover(args)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
