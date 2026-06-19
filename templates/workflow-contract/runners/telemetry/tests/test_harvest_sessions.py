"""
test_harvest_sessions.py — harvest_sessions + vendor/session_lean 단위 테스트.

parity 테스트: agentlens가 설치돼 있을 때만 비교 — 없으면 skip + 로그 출력.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import textwrap
import unittest

# ---------------------------------------------------------------------------
# sys.path 조정 — 텔레메트리 디렉토리를 임포트 경로에 추가
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_TELEMETRY = os.path.dirname(_HERE)
if _TELEMETRY not in sys.path:
    sys.path.insert(0, _TELEMETRY)

import harvest_sessions as hs
from vendor.session_lean import parse_session_lean, collect_tool_names, total_event_count


# ---------------------------------------------------------------------------
# 테스트 픽스처(fixture) 헬퍼
# ---------------------------------------------------------------------------

def _make_jsonl(entries: list) -> str:
    """list[dict] → 임시 jsonl 파일 경로 반환."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def _simple_session(ticket: str = "PRA-109") -> list:
    """단순 세션 픽스처 — user 턴 + assistant(tool_use) + user(tool_result)."""
    return [
        {
            "type": "user",
            "message": {"role": "user", "content": f"/impl {ticket} 테스트 작업 수행"},
            "timestamp": "2026-06-19T10:00:00.000Z",
            "cwd": "/home/user/sbx-work/claude-workshop",
            "userType": "external",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_001",
                        "name": "Read",
                        "input": {
                            "file_path": "/home/user/file.py",
                        },
                    }
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_input_tokens": 20,
                    "cache_read_input_tokens": 80,
                },
            },
            "timestamp": "2026-06-19T10:00:05.000Z",
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_001",
                        "content": "file contents here",
                        "is_error": False,
                    }
                ],
            },
            "timestamp": "2026-06-19T10:00:06.000Z",
        },
    ]


def _error_session() -> list:
    """tool_result is_error=True 포함 세션."""
    return [
        {
            "type": "user",
            "message": {"role": "user", "content": "/impl PRA-200 에러 테스트"},
            "timestamp": "2026-06-19T11:00:00.000Z",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_002",
                        "name": "Bash",
                        "input": {"command": "python3 nonexistent.py"},
                    }
                ],
                "usage": {
                    "input_tokens": 50,
                    "output_tokens": 30,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
            "timestamp": "2026-06-19T11:00:05.000Z",
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_002",
                        "content": "FileNotFoundError: nonexistent.py",
                        "is_error": True,
                    }
                ],
            },
            "timestamp": "2026-06-19T11:00:06.000Z",
        },
    ]


# ---------------------------------------------------------------------------
# 1. vendor session_lean 기본 파싱
# ---------------------------------------------------------------------------

class TestSessionLeanParsing(unittest.TestCase):

    def test_parse_simple_session_message_count(self):
        path = _make_jsonl(_simple_session())
        try:
            session = parse_session_lean(path)
            # user + assistant + user(tool_response) = 3
            self.assertEqual(len(session.messages), 3)
        finally:
            os.unlink(path)

    def test_parse_tool_pairs(self):
        path = _make_jsonl(_simple_session())
        try:
            session = parse_session_lean(path)
            assistant_msgs = [m for m in session.messages if m.type == "assistant"]
            self.assertEqual(len(assistant_msgs), 1)
            self.assertEqual(len(assistant_msgs[0].tool_pairs), 1)
            self.assertEqual(assistant_msgs[0].tool_pairs[0].tool_name, "Read")
        finally:
            os.unlink(path)

    def test_parse_token_usage(self):
        path = _make_jsonl(_simple_session())
        try:
            session = parse_session_lean(path)
            self.assertEqual(session.total_tokens.input_tokens, 100)
            self.assertEqual(session.total_tokens.output_tokens, 50)
            self.assertEqual(session.total_tokens.cache_creation_tokens, 20)
            self.assertEqual(session.total_tokens.cache_read_tokens, 80)
        finally:
            os.unlink(path)

    def test_collect_tool_names(self):
        path = _make_jsonl(_simple_session())
        try:
            session = parse_session_lean(path)
            names = collect_tool_names(session)
            self.assertIn("Read", names)
        finally:
            os.unlink(path)

    def test_total_event_count(self):
        path = _make_jsonl(_simple_session())
        try:
            session = parse_session_lean(path)
            self.assertEqual(total_event_count(session), 1)
        finally:
            os.unlink(path)

    def test_malformed_jsonl_no_crash(self):
        """깨진(malformed) jsonl 줄이 있어도 crash 없이 parse_error로 수집."""
        entries_raw = [
            '{"type": "user", "message": {"role": "user", "content": "hello"}, "timestamp": "2026-06-19T10:00:00Z"}\n',
            'THIS IS NOT JSON {{broken\n',
            '{"type": "assistant", "message": {"content": [], "usage": {"input_tokens": 10, "output_tokens": 5, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}, "timestamp": "2026-06-19T10:00:01Z"}\n',
        ]
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(entries_raw)
        try:
            session = parse_session_lean(path)
            self.assertEqual(len(session.parse_errors), 1)
            self.assertEqual(session.parse_errors[0].line_no, 2)
        finally:
            os.unlink(path)

    def test_empty_file_no_crash(self):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        try:
            session = parse_session_lean(path)
            self.assertEqual(len(session.messages), 0)
        finally:
            os.unlink(path)

    def test_nonexistent_file_no_crash(self):
        session = parse_session_lean("/tmp/nonexistent_session_xyz.jsonl")
        self.assertEqual(len(session.messages), 0)
        self.assertEqual(len(session.parse_errors), 1)
        self.assertIn("OSError", session.parse_errors[0].reason)

    def test_timestamp_fallback_on_bad_value(self):
        """타임스탬프 파싱 실패 시 epoch(UTC) 폴백 동작."""
        entries = [
            {
                "type": "user",
                "message": {"role": "user", "content": "hi"},
                "timestamp": "NOT_A_TIMESTAMP",
            }
        ]
        path = _make_jsonl(entries)
        try:
            session = parse_session_lean(path)
            self.assertEqual(len(session.messages), 1)
            # epoch 폴백 — timestamp=0
            self.assertEqual(session.messages[0].timestamp.timestamp(), 0.0)
        finally:
            os.unlink(path)

    def test_no_agentlens_import_in_vendor(self):
        """vendor/session_lean.py에 agentlens/pydantic import가 없다."""
        import re as _re
        vendor_path = os.path.join(_TELEMETRY, "vendor", "session_lean.py")
        with open(vendor_path, encoding="utf-8") as f:
            content = f.read()
        bad_imports = _re.findall(
            r"^\s*(?:import|from)\s+(agentlens|pydantic|requests|yaml|httpx|anthropic)\b",
            content,
            _re.MULTILINE,
        )
        self.assertEqual(bad_imports, [], f"vendor에 외부 import 발견: {bad_imports}")


# ---------------------------------------------------------------------------
# 2. build_event_stream — user_turn raw 텍스트 부재
# ---------------------------------------------------------------------------

class TestBuildEventStream(unittest.TestCase):

    def test_event_stream_not_empty(self):
        path = _make_jsonl(_simple_session())
        try:
            events, raw = hs.build_event_stream(path)
            self.assertTrue(len(events) > 0, "이벤트 스트림이 비어있음")
        finally:
            os.unlink(path)

    def test_user_turn_has_no_content_key(self):
        """user_turn 이벤트에 'content' 키가 없어야 한다 (raw text 유출 방지)."""
        path = _make_jsonl(_simple_session())
        try:
            events, raw = hs.build_event_stream(path)
            user_turn_events = [e for e in events if e["type"] == "user_turn"]
            self.assertTrue(len(user_turn_events) > 0, "user_turn 이벤트 없음")
            for e in user_turn_events:
                self.assertNotIn("content", e, "user_turn에 content 키 존재 — raw text 유출")
                self.assertNotIn("text", e, "user_turn에 text 키 존재 — raw text 유출")
        finally:
            os.unlink(path)

    def test_user_turn_has_meta_keys(self):
        """user_turn 이벤트에는 seq, ts, char_len, token_count만 있어야 한다."""
        path = _make_jsonl(_simple_session())
        try:
            events, raw = hs.build_event_stream(path)
            user_turn_events = [e for e in events if e["type"] == "user_turn"]
            for e in user_turn_events:
                self.assertIn("seq", e)
                self.assertIn("ts", e)
                self.assertIn("char_len", e)
                self.assertIn("token_count", e)
        finally:
            os.unlink(path)

    def test_raw_user_turns_held_separately(self):
        """raw_user_turns 리스트에 원문 텍스트가 존재한다."""
        path = _make_jsonl(_simple_session())
        try:
            events, raw = hs.build_event_stream(path)
            self.assertTrue(len(raw) > 0, "raw_user_turns가 비어 있음")
            # 원문 텍스트에 PRA-109 포함
            self.assertTrue(any("PRA-109" in t for t in raw))
        finally:
            os.unlink(path)

    def test_tool_event_has_tool_name(self):
        """tool 이벤트에 tool_name 필드가 있다."""
        path = _make_jsonl(_simple_session())
        try:
            events, raw = hs.build_event_stream(path)
            tool_events = [e for e in events if e["type"] == "tool"]
            self.assertTrue(len(tool_events) > 0, "tool 이벤트 없음")
            for e in tool_events:
                self.assertIn("tool_name", e)
                self.assertEqual(e["tool_name"], "Read")
        finally:
            os.unlink(path)

    def test_tool_event_has_path(self):
        """tool 이벤트에 path 필드가 있다 (file_path 인자에서 추출)."""
        path = _make_jsonl(_simple_session())
        try:
            events, raw = hs.build_event_stream(path)
            tool_events = [e for e in events if e["type"] == "tool"]
            self.assertTrue(any(e.get("path") for e in tool_events))
        finally:
            os.unlink(path)

    def test_error_event_has_error_class(self):
        """error 이벤트에 error_class와 error_first_line이 있다."""
        path = _make_jsonl(_error_session())
        try:
            events, raw = hs.build_event_stream(path)
            error_events = [e for e in events if e["type"] == "error"]
            self.assertTrue(len(error_events) > 0, "error 이벤트 없음")
            for e in error_events:
                self.assertIn("error_class", e)
                self.assertEqual(e.get("error_class"), "FileNotFoundError")
        finally:
            os.unlink(path)

    def test_error_first_line_no_user_supplied_string_leak(self):
        """Bash tool_result 에러에서 사용자 공급 비경로 문자열이 error_first_line에 누출되지 않는다.

        p2-A: error_first_line은 예외 클래스 토큰으로만 제한된다.
        콜론 뒤의 사용자 제공 인자(secret, NL 문자열 등)는 포함되어선 안 된다.
        """
        user_secret = "my-secret-argument-XYZ789"
        entries = [
            {
                "type": "user",
                "message": {"role": "user", "content": "/impl PRA-001"},
                "timestamp": "2026-06-19T10:00:00.000Z",
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "model": "claude-sonnet-4-6",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_bash",
                            "name": "Bash",
                            "input": {"command": f"do_something {user_secret}"},
                        }
                    ],
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                    },
                },
                "timestamp": "2026-06-19T10:00:05.000Z",
            },
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_bash",
                            "content": f"FileNotFoundError: {user_secret} not found\nmore lines here",
                            "is_error": True,
                        }
                    ],
                },
                "timestamp": "2026-06-19T10:00:06.000Z",
            },
        ]
        path = _make_jsonl(entries)
        try:
            events, raw = hs.build_event_stream(path)
            error_events = [e for e in events if e["type"] == "error"]
            self.assertTrue(len(error_events) > 0, "error 이벤트 없음")
            for e in error_events:
                # error_class는 예외 클래스 토큰이어야 함
                self.assertEqual(e.get("error_class"), "FileNotFoundError")
                # error_first_line은 예외 클래스 토큰으로만 제한 — 사용자 공급 문자열 없어야 함
                elf = e.get("error_first_line", "")
                self.assertNotIn(user_secret, elf,
                                 f"사용자 공급 문자열 '{user_secret}' 이 error_first_line에 누출됨: {elf!r}")
                # 멀티라인도 누출 안 됨
                self.assertNotIn("more lines", elf,
                                 "멀티라인 텍스트가 error_first_line에 누출됨")
        finally:
            os.unlink(path)

    def test_command_len_not_full_command(self):
        """command 인자가 있는 tool 이벤트에 전체 command 텍스트가 없다."""
        path = _make_jsonl(_error_session())
        try:
            events, raw = hs.build_event_stream(path)
            # 에러 이벤트에도 tool_name은 있지만 command 전체는 없음
            for e in events:
                self.assertNotIn("command", e, "이벤트에 command 전체 텍스트 유출")
        finally:
            os.unlink(path)

    def test_event_stream_bytes_no_user_raw_text(self):
        """이벤트 스트림을 JSON 직렬화해도 user 턴 원문 텍스트가 없다."""
        path = _make_jsonl(_simple_session())
        try:
            events, raw = hs.build_event_stream(path)
            serialized = json.dumps(events, ensure_ascii=False)
            # raw user turns의 원문이 이벤트 스트림 JSON에 없어야 한다
            for raw_text in raw:
                if raw_text.strip():
                    # 원문의 일부(첫 20자)가 이벤트 스트림에 있으면 안 된다
                    snippet = raw_text.strip()[:20]
                    if len(snippet) > 5:  # 너무 짧은 텍스트는 검사 제외
                        self.assertNotIn(snippet, serialized,
                                         f"user 턴 원문 텍스트 '{snippet}' 이벤트 스트림에 유출됨")
        finally:
            os.unlink(path)

    def test_seq_is_sequential(self):
        """이벤트의 seq 필드가 0부터 순서대로 증가한다."""
        path = _make_jsonl(_simple_session())
        try:
            events, raw = hs.build_event_stream(path)
            seqs = [e["seq"] for e in events]
            self.assertEqual(seqs, list(range(len(events))))
        finally:
            os.unlink(path)

    def test_malformed_jsonl_no_crash_in_event_stream(self):
        """깨진 jsonl도 build_event_stream이 crash 없이 처리한다."""
        entries_raw = [
            '{"type": "user", "message": {"role": "user", "content": "/impl PRA-999"}, "timestamp": "2026-06-19T10:00:00Z"}\n',
            'BROKEN JSON\n',
        ]
        fd, fpath = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(entries_raw)
        try:
            events, raw = hs.build_event_stream(fpath)
            # crash 없이 반환
            self.assertIsInstance(events, list)
        finally:
            os.unlink(fpath)


# ---------------------------------------------------------------------------
# 3. correlate — ticket 복원
# ---------------------------------------------------------------------------

class _FakeCorpus:
    """테스트용 가짜 RepoCorpus."""
    def __init__(self, session_dir):
        self.session_dir = session_dir


class TestCorrelate(unittest.TestCase):

    def test_ticket_restoration(self):
        """ticket 있는 세션이 by_ticket에 올바르게 분류된다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sess1.jsonl")
            with open(path, "w") as f:
                for entry in _simple_session("PRA-109"):
                    f.write(json.dumps(entry) + "\n")
            corpus = _FakeCorpus(tmpdir)
            result = hs.correlate(corpus)
            self.assertIn("PRA-109", result["by_ticket"])
            self.assertEqual(len(result["by_ticket"]["PRA-109"]), 1)

    def test_ticketless_session_excluded_from_by_ticket(self):
        """ticket 복원 실패 세션이 ticketless에 들어간다."""
        entries = [
            {
                "type": "user",
                "message": {"role": "user", "content": "안녕하세요 그냥 질문입니다"},
                "timestamp": "2026-06-19T12:00:00Z",
            }
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sess_no_ticket.jsonl")
            with open(path, "w") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")
            corpus = _FakeCorpus(tmpdir)
            result = hs.correlate(corpus)
            self.assertEqual(len(result["by_ticket"]), 0)
            self.assertEqual(len(result["ticketless"]), 1)

    def test_multiple_sessions_grouped_by_ticket(self):
        """동일 ticket의 여러 세션이 by_ticket[ticket]에 모인다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                path = os.path.join(tmpdir, f"sess{i}.jsonl")
                with open(path, "w") as f:
                    for entry in _simple_session("PRA-999"):
                        f.write(json.dumps(entry) + "\n")
            corpus = _FakeCorpus(tmpdir)
            result = hs.correlate(corpus)
            self.assertEqual(len(result["by_ticket"]["PRA-999"]), 3)

    def test_no_session_dir_returns_empty(self):
        """session_dir가 None이면 빈 결과 반환."""
        corpus = _FakeCorpus(None)
        result = hs.correlate(corpus)
        self.assertEqual(result["by_ticket"], {})
        self.assertEqual(result["ticketless"], [])

    def test_nonexistent_session_dir_returns_empty(self):
        """존재하지 않는 session_dir도 빈 결과 반환 (무crash)."""
        corpus = _FakeCorpus("/tmp/nonexistent_session_dir_xyz/")
        result = hs.correlate(corpus)
        self.assertEqual(result["by_ticket"], {})

    def test_feat_branch_ticket_extraction(self):
        """feat/PRA-109 브랜치 패턴으로 ticket 복원."""
        entries = [
            {
                "type": "user",
                "message": {"role": "user", "content": "작업 시작"},
                "timestamp": "2026-06-19T13:00:00Z",
                "gitBranch": "feat/PRA-109-some-feature",
            }
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sess_branch.jsonl")
            with open(path, "w") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")
            corpus = _FakeCorpus(tmpdir)
            result = hs.correlate(corpus)
            self.assertIn("PRA-109", result["by_ticket"])

    def test_result_shape_has_required_keys(self):
        """correlate 반환값이 T2와 동일한 {by_ticket, ticketless, parse_errors} 형태."""
        corpus = _FakeCorpus("/tmp/nonexistent_xyz/")
        result = hs.correlate(corpus)
        self.assertIn("by_ticket", result)
        self.assertIn("ticketless", result)
        self.assertIn("parse_errors", result)


# ---------------------------------------------------------------------------
# 4. agentlens parity 테스트 (agentlens 설치돼 있을 때만)
# ---------------------------------------------------------------------------

class TestAgentlensParity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            sys.path.insert(0, os.path.expanduser("~/sbx-work/agentlens/src"))
            from agentlens.parsers.session import parse_session  # noqa
            cls._parse_session = staticmethod(parse_session)
            cls._agentlens_available = True
        except ImportError:
            cls._agentlens_available = False
            print(
                "\n[SKIP] agentlens 미설치 — parity 테스트 생략. "
                "~/sbx-work/agentlens 가 있을 때만 비교.",
                file=sys.stderr,
            )

    def _skip_if_unavailable(self):
        if not self.__class__._agentlens_available:
            self.skipTest("agentlens 미설치 — parity 테스트 건너뜀")

    def test_tool_name_set_parity(self):
        """동일 jsonl에서 tool 이름 집합이 agentlens와 일치한다."""
        self._skip_if_unavailable()
        path = _make_jsonl(_simple_session())
        try:
            lean_session = parse_session_lean(path)
            lean_names = collect_tool_names(lean_session)

            detail = self.__class__._parse_session(path)
            ref_names: set = set()
            for msg in detail.messages:
                if msg.tool_pairs:
                    for pair in msg.tool_pairs:
                        ref_names.add(pair.tool_name)

            self.assertEqual(lean_names, ref_names)
        finally:
            os.unlink(path)

    def test_token_sum_parity(self):
        """동일 jsonl에서 총 토큰 합이 agentlens canonical 합산과 일치한다.

        비교 대상: detail.summary.tokens.total_tokens() — 모델 유무와 무관하게
        모든 assistant usage를 누산하는 canonical 누산기.
        (tokens_by_model은 msg.model이 있을 때만 채워지므로 model-less assistant
        메시지가 있으면 diverge한다.)
        """
        self._skip_if_unavailable()
        path = _make_jsonl(_simple_session())
        try:
            lean_session = parse_session_lean(path)
            lean_total = lean_session.total_tokens.total()

            detail = self.__class__._parse_session(path)
            # canonical 누산기: summary.tokens는 model 유무 무관하게 전체 usage 합산
            ref_sum = detail.summary.tokens.total_tokens()

            self.assertEqual(lean_total, ref_sum)
        finally:
            os.unlink(path)

    def test_event_count_parity(self):
        """동일 jsonl에서 tool_use 페어 수가 agentlens와 일치한다."""
        self._skip_if_unavailable()
        path = _make_jsonl(_simple_session())
        try:
            lean_session = parse_session_lean(path)
            lean_count = total_event_count(lean_session)

            detail = self.__class__._parse_session(path)
            ref_count = 0
            for msg in detail.messages:
                if msg.tool_pairs:
                    ref_count += len(msg.tool_pairs)

            self.assertEqual(lean_count, ref_count)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# 5. collect.py harvest-sessions CLI 통합 테스트
# ---------------------------------------------------------------------------

class TestHarvestSessionsCli(unittest.TestCase):

    def test_harvest_sessions_for_repo_returns_dict_shape(self):
        """harvest_sessions_for_repo가 {by_ticket, ticketless, parse_errors} 반환."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sess1.jsonl")
            with open(path, "w") as f:
                for entry in _simple_session("PRA-109"):
                    f.write(json.dumps(entry) + "\n")

            class FakeCorpus:
                session_dir = tmpdir

            result = hs.harvest_sessions_for_repo(FakeCorpus())
            self.assertIn("by_ticket", result)
            self.assertIn("ticketless", result)
            self.assertIn("parse_errors", result)


if __name__ == "__main__":
    unittest.main()
