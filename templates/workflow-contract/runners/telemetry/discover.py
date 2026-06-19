"""
discover.py — 코퍼스 디스커버리(corpus discovery)
T1: ~/sbx-work/* 하위에서 .claude/ 디렉토리를 가진 레포를 찾고,
세션로그 slug 역매핑으로 ~/.claude/projects/{slug}/ 경로를 반환한다.

외부 의존 0 — stdlib만 사용.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RepoCorpus:
    """레포 하나의 디스커버리 결과."""
    repo_path: str
    name: str
    session_dir: Optional[str]   # ~/.claude/projects/{slug} 경로 (없으면 None)
    plans_dir: Optional[str]     # .claude/plans/ (없으면 None)
    tasks_dirs: List[str]        # .claude/tasks/{done,pending,failed}/ 중 존재하는 것
    runs_dir: Optional[str]      # .claude/runs/ (없으면 None)


def slug_for_path(repo_path: str) -> str:
    """
    절대경로 → Claude Code 세션로그 slug 변환.
    규칙: '/'과 '.'를 '-'로 치환하며, 선행(leading) '-'는 유지한다.
    예: /home/prasuer/sbx-work/claude-workshop → -home-prasuer-sbx-work-claude-workshop
    """
    # 경로를 정규화(normalize)한다 — 후행 슬래시 제거
    path = os.path.normpath(repo_path)
    # '/'와 '.'를 '-'로 치환
    slug = path.replace("/", "-").replace(".", "-")
    return slug


def session_dir_for_repo(
    repo_path: str,
    base: str = "~/.claude/projects",
) -> Optional[str]:
    """
    slug 역매핑(reverse-mapping)으로 세션로그 디렉토리 경로를 반환.
    디렉토리가 존재하지 않으면 None 반환.
    """
    base_expanded = os.path.expanduser(base)
    slug = slug_for_path(os.path.abspath(repo_path))
    candidate = os.path.join(base_expanded, slug)
    if os.path.isdir(candidate):
        return candidate
    return None


def discover_repos(roots: Optional[List[str]] = None) -> List[RepoCorpus]:
    """
    roots 목록(기본: ["~/sbx-work"]) 각각의 직계 하위 디렉토리 중
    .claude/ 디렉토리를 가진 레포를 찾아 RepoCorpus 리스트로 반환한다.

    부재 디렉토리는 None/빈 리스트로 처리 — 무crash(P1-3 선반영).
    """
    if roots is None:
        roots = ["~/sbx-work"]

    result: List[RepoCorpus] = []

    for root in roots:
        root_expanded = os.path.expanduser(root)
        if not os.path.isdir(root_expanded):
            continue

        try:
            entries = os.scandir(root_expanded)
        except PermissionError:
            continue

        with entries as it:
            for entry in it:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                claude_dir = os.path.join(entry.path, ".claude")
                if not os.path.isdir(claude_dir):
                    continue

                repo_path = entry.path
                name = entry.name

                # 세션로그 디렉토리
                sess_dir = session_dir_for_repo(repo_path)

                # plans 디렉토리
                plans_candidate = os.path.join(claude_dir, "plans")
                plans_dir: Optional[str] = (
                    plans_candidate if os.path.isdir(plans_candidate) else None
                )

                # tasks 하위 디렉토리(done / pending / failed)
                tasks_base = os.path.join(claude_dir, "tasks")
                tasks_dirs: List[str] = []
                for sub in ("done", "pending", "failed"):
                    p = os.path.join(tasks_base, sub)
                    if os.path.isdir(p):
                        tasks_dirs.append(p)

                # runs 디렉토리
                runs_candidate = os.path.join(claude_dir, "runs")
                runs_dir: Optional[str] = (
                    runs_candidate if os.path.isdir(runs_candidate) else None
                )

                result.append(
                    RepoCorpus(
                        repo_path=repo_path,
                        name=name,
                        session_dir=sess_dir,
                        plans_dir=plans_dir,
                        tasks_dirs=tasks_dirs,
                        runs_dir=runs_dir,
                    )
                )

    return result
