"""
test_discover.py — discover.py 단위 테스트.
stdlib unittest 사용 — 외부 의존 0.
"""

import os
import sys
import tempfile
import unittest

# discover 모듈 경로 추가
_TELEMETRY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TELEMETRY_DIR not in sys.path:
    sys.path.insert(0, _TELEMETRY_DIR)

import discover


class TestSlugForPath(unittest.TestCase):
    """slug_for_path 정확성 테스트."""

    def test_claude_workshop_slug(self):
        """실제 claude-workshop 레포 절대경로 → 예상 slug."""
        result = discover.slug_for_path("/home/prasuer/sbx-work/claude-workshop")
        self.assertEqual(result, "-home-prasuer-sbx-work-claude-workshop")

    def test_leading_dash_preserved(self):
        """선행(leading) '-'가 유지되어야 한다."""
        slug = discover.slug_for_path("/home/user/project")
        self.assertTrue(slug.startswith("-"), f"선행 '-' 없음: {slug}")

    def test_dot_converted(self):
        """경로 중 '.'가 '-'로 변환된다."""
        slug = discover.slug_for_path("/home/user/.local/project")
        self.assertNotIn(".", slug, f"'.' 미변환 잔존: {slug}")
        self.assertIn("-", slug)

    def test_slash_converted(self):
        """경로 중 '/'가 '-'로 변환된다."""
        slug = discover.slug_for_path("/a/b/c")
        self.assertNotIn("/", slug, f"'/' 미변환 잔존: {slug}")

    def test_trailing_slash_ignored(self):
        """후행(trailing) 슬래시는 결과에 영향을 주지 않는다."""
        s1 = discover.slug_for_path("/home/user/project")
        s2 = discover.slug_for_path("/home/user/project/")
        self.assertEqual(s1, s2)


class TestDiscoverRepos(unittest.TestCase):
    """discover_repos가 .claude 보유 레포만 반환하는지 테스트."""

    def _make_repo(self, base_dir: str, name: str, with_claude: bool = True) -> str:
        """임시 레포 디렉토리를 생성한다."""
        repo_dir = os.path.join(base_dir, name)
        os.makedirs(repo_dir)
        if with_claude:
            os.makedirs(os.path.join(repo_dir, ".claude"))
        return repo_dir

    def test_only_returns_repos_with_claude_dir(self):
        """`.claude/` 없는 디렉토리는 결과에 포함되지 않는다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_repo(tmpdir, "has-claude", with_claude=True)
            self._make_repo(tmpdir, "no-claude", with_claude=False)

            repos = discover.discover_repos([tmpdir])

            names = [r.name for r in repos]
            self.assertIn("has-claude", names)
            self.assertNotIn("no-claude", names)

    def test_nonexistent_root_no_crash(self):
        """존재하지 않는 root를 넘겨도 crash하지 않는다."""
        repos = discover.discover_repos(["/nonexistent/path/that/does/not/exist"])
        self.assertEqual(repos, [])

    def test_returns_list(self):
        """반환값은 항상 list다."""
        result = discover.discover_repos([])
        self.assertIsInstance(result, list)

    def test_absent_subdirs_are_none_or_empty(self):
        """.claude/plans·runs·tasks 없는 레포에서 각 필드는 None/빈 리스트."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_repo(tmpdir, "minimal", with_claude=True)
            repos = discover.discover_repos([tmpdir])

            self.assertEqual(len(repos), 1)
            repo = repos[0]
            self.assertIsNone(repo.plans_dir)
            self.assertIsNone(repo.runs_dir)
            self.assertIsInstance(repo.tasks_dirs, list)
            self.assertEqual(repo.tasks_dirs, [])

    def test_present_subdirs_are_detected(self):
        """.claude/plans·runs·tasks/done 이 있으면 각 필드에 채워진다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = self._make_repo(tmpdir, "full", with_claude=True)
            claude = os.path.join(repo_dir, ".claude")
            os.makedirs(os.path.join(claude, "plans"))
            os.makedirs(os.path.join(claude, "runs"))
            os.makedirs(os.path.join(claude, "tasks", "done"))
            os.makedirs(os.path.join(claude, "tasks", "pending"))

            repos = discover.discover_repos([tmpdir])
            self.assertEqual(len(repos), 1)
            repo = repos[0]

            self.assertIsNotNone(repo.plans_dir)
            self.assertIsNotNone(repo.runs_dir)
            self.assertIn(os.path.join(claude, "tasks", "done"), repo.tasks_dirs)
            self.assertIn(os.path.join(claude, "tasks", "pending"), repo.tasks_dirs)

    def test_file_in_root_is_ignored(self):
        """root 하위의 파일(file)은 디렉토리가 아니므로 무시된다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 파일 생성
            open(os.path.join(tmpdir, "some-file.txt"), "w").close()
            self._make_repo(tmpdir, "real-repo", with_claude=True)

            repos = discover.discover_repos([tmpdir])
            self.assertEqual(len(repos), 1)
            self.assertEqual(repos[0].name, "real-repo")


class TestSessionDirForRepo(unittest.TestCase):
    """session_dir_for_repo 반환값 테스트."""

    def test_returns_none_for_nonexistent_base(self):
        """base 디렉토리가 없으면 None 반환 (무crash)."""
        result = discover.session_dir_for_repo(
            "/home/prasuer/sbx-work/claude-workshop",
            base="/nonexistent/base",
        )
        self.assertIsNone(result)

    def test_returns_dir_when_exists(self):
        """slug가 일치하는 디렉토리가 있으면 해당 경로를 반환한다."""
        with tempfile.TemporaryDirectory() as base:
            slug = discover.slug_for_path("/home/prasuer/sbx-work/claude-workshop")
            target = os.path.join(base, slug)
            os.makedirs(target)

            result = discover.session_dir_for_repo(
                "/home/prasuer/sbx-work/claude-workshop",
                base=base,
            )
            self.assertEqual(result, target)


if __name__ == "__main__":
    unittest.main()
