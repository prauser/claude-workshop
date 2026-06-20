"""
test_collect.py — collect.py 배선(wiring) 통합 테스트 (p2-C).

검증 항목:
  (a) 세션 raw_user_turn이 forbidden_raw에 포함되면 DeidLeakError 발생.
  (b) plan user_prompt가 forbidden_raw에 포함되면 DeidLeakError 발생.
  (c) forbidden_raw가 BOTH session turns AND plan user_prompt를 포함하는지 회귀 테스트 (p1-A/p1-B).
  (d) DeidLeakError가 전파되고 삼켜지지(swallowed) 않는지 확인.
  (e) None/빈 forbidden_raw가 크래시를 일으키지 않는지 확인.
  (f) assemble_forbidden_raw가 plan_path를 통해 get_plan_user_prompt를 올바르게 호출하는지.
  (g) assemble_forbidden_raw가 raw_user_turns_by_session을 올바르게 수집하는지.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import pytest

# ---------------------------------------------------------------------------
# sys.path 조정 — telemetry 디렉토리 추가
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_TELEMETRY = os.path.dirname(_HERE)
if _TELEMETRY not in sys.path:
    sys.path.insert(0, _TELEMETRY)

import collect  # noqa: E402
from deid import DeidLeakError  # noqa: E402


# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------

def _make_plan_md(user_prompt: str) -> str:
    """임시 plan.md 파일을 생성하고 경로를 반환한다."""
    content = f"""---
ticket: TEST-1
user_prompt: {user_prompt}
intent:
  problem: test problem
  approach: test approach
---

# Test Plan
"""
    fd, path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _make_artifact_results(plan_path: str, ticket: str = "TEST-1") -> list:
    """harvest_artifacts 결과 형태를 모방한 artifact_results 픽스처."""
    return [
        {
            "repo_path": "/tmp/test_repo",
            "repo_name": "test_repo",
            "by_ticket": {
                ticket: {
                    "plan": {
                        "ticket": ticket,
                        "plan_path": plan_path,
                        "intent": {"problem": "test"},
                        "gate_events": [],
                        "skip_presearch": 0,
                        "skip_gate2": 0,
                        "readiness_flags": [],
                        "risk_acks": [],
                        "intent_history_len": 0,
                        "plan_sha": None,
                    },
                    "tasks": [],
                    "manifest": None,
                }
            },
            "ticketless": [],
            "parse_errors": [],
        }
    ]


def _make_session_results(raw_turns: list) -> list:
    """harvest_sessions 결과 형태를 모방한 session_results 픽스처."""
    return [
        {
            "by_ticket": {},
            "ticketless": [],
            "parse_errors": [],
            "raw_user_turns_by_session": {
                "test_session_001": raw_turns,
            },
        }
    ]


# ---------------------------------------------------------------------------
# (a) session raw_user_turn → DeidLeakError
# ---------------------------------------------------------------------------


class TestSessionTurnLeak:
    """세션 raw_user_turn이 번들에 남으면 DeidLeakError가 발생하는지 검증."""

    def test_session_raw_turn_in_bundle_raises(self):
        """forbidden_raw에 session raw_user_turn → 번들에 있으면 DeidLeakError."""
        sentinel = "SENTINEL_SESSION_TURN_LEAK_TEST_ABCDEF"
        # forbidden_raw에 sentinel이 있고 번들에도 sentinel이 있으면 fail
        bundle = {"user_input_characteristics": {"raw_leak": sentinel}}
        with pytest.raises(DeidLeakError):
            collect.deidentify(bundle, [sentinel])

    def test_session_raw_turn_abstracted_passes(self):
        """session raw_user_turn을 추상화한 특성만 번들에 있으면 통과."""
        sentinel = "SENTINEL_SESSION_TURN_CLEAN_TEST_ABCDEF"
        bundle = {"user_input_characteristics": {"length_band": "M", "request_shape": "feature"}}
        result = collect.deidentify(bundle, [sentinel])
        assert result is bundle


# ---------------------------------------------------------------------------
# (b) plan user_prompt → DeidLeakError
# ---------------------------------------------------------------------------


class TestPlanUserPromptLeak:
    """plan user_prompt가 번들에 남으면 DeidLeakError가 발생하는지 검증."""

    def test_plan_user_prompt_in_bundle_raises(self):
        """forbidden_raw에 plan user_prompt → 번들에 있으면 DeidLeakError."""
        sentinel = "SENTINEL_PLAN_USER_PROMPT_LEAK_TEST_XYZXYZ"
        bundle = {"leaked_data": sentinel}
        with pytest.raises(DeidLeakError):
            collect.deidentify(bundle, [sentinel])

    def test_plan_user_prompt_abstracted_passes(self):
        """plan user_prompt를 추상화한 특성만 번들에 있으면 통과."""
        sentinel = "SENTINEL_PLAN_USER_PROMPT_CLEAN_TEST_XYZXYZ"
        bundle = {"user_input_characteristics": {"request_shape": "bugfix"}}
        result = collect.deidentify(bundle, [sentinel])
        assert result is bundle


# ---------------------------------------------------------------------------
# (c) assemble_forbidden_raw - BOTH session turns AND plan user_prompt 회귀 테스트
# ---------------------------------------------------------------------------


class TestAssembleForbiddenRaw:
    """assemble_forbidden_raw가 두 소스를 모두 수집하는지 회귀 테스트 (p1-A/p1-B)."""

    def test_includes_plan_user_prompt(self):
        """assemble_forbidden_raw가 plan user_prompt를 포함하는지 확인 (p1-B 회귀)."""
        sentinel = "SENTINEL_PLAN_PROMPT_ASSEMBLE_TEST_12345"
        plan_path = _make_plan_md(sentinel)
        try:
            artifact_results = _make_artifact_results(plan_path)
            session_results = _make_session_results([])

            forbidden = collect.assemble_forbidden_raw(artifact_results, session_results)
            assert sentinel in forbidden, (
                f"plan user_prompt({sentinel!r})이 forbidden_raw에 없음 — p1-B 회귀"
            )
        finally:
            os.unlink(plan_path)

    def test_includes_session_raw_turns(self):
        """assemble_forbidden_raw가 session raw_user_turns를 포함하는지 확인 (p1-A 회귀)."""
        sentinel = "SENTINEL_SESSION_TURN_ASSEMBLE_TEST_67890"
        artifact_results = _make_artifact_results("/nonexistent/plan.md")
        session_results = _make_session_results([sentinel])

        forbidden = collect.assemble_forbidden_raw(artifact_results, session_results)
        assert sentinel in forbidden, (
            f"session raw_user_turn({sentinel!r})이 forbidden_raw에 없음 — p1-A 회귀"
        )

    def test_includes_both_sources(self):
        """assemble_forbidden_raw가 plan user_prompt AND session turns를 동시에 수집."""
        plan_sentinel = "SENTINEL_PLAN_BOTH_TEST_AAABBB"
        session_sentinel = "SENTINEL_SESSION_BOTH_TEST_CCCDDD"
        plan_path = _make_plan_md(plan_sentinel)
        try:
            artifact_results = _make_artifact_results(plan_path)
            session_results = _make_session_results([session_sentinel])

            forbidden = collect.assemble_forbidden_raw(artifact_results, session_results)
            assert plan_sentinel in forbidden, "plan user_prompt가 forbidden_raw에 없음"
            assert session_sentinel in forbidden, "session raw_user_turn이 forbidden_raw에 없음"
        finally:
            os.unlink(plan_path)

    def test_wired_pipeline_bundle_with_session_turn_raises(self):
        """end-to-end 배선 확인: assemble_forbidden_raw → deidentify가 session turn 누출을 차단."""
        sentinel = "SENTINEL_WIRED_SESSION_GATE_TEST_EEEFFF"
        # session raw turn이 forbidden_raw에 들어가고
        session_results = _make_session_results([sentinel])
        artifact_results = _make_artifact_results("/nonexistent/plan.md")

        forbidden = collect.assemble_forbidden_raw(artifact_results, session_results)
        # 번들에 sentinel이 있으면 DeidLeakError가 raise돼야 한다
        bundle = {"leaked_session_content": sentinel}
        with pytest.raises(DeidLeakError):
            collect.deidentify(bundle, forbidden)

    def test_wired_pipeline_bundle_with_plan_prompt_raises(self):
        """end-to-end 배선 확인: assemble_forbidden_raw → deidentify가 plan user_prompt 누출을 차단."""
        sentinel = "SENTINEL_WIRED_PLAN_GATE_TEST_GGGHHH"
        plan_path = _make_plan_md(sentinel)
        try:
            artifact_results = _make_artifact_results(plan_path)
            session_results = _make_session_results([])

            forbidden = collect.assemble_forbidden_raw(artifact_results, session_results)
            # 번들에 sentinel이 있으면 DeidLeakError가 raise돼야 한다
            bundle = {"leaked_plan_prompt": sentinel}
            with pytest.raises(DeidLeakError):
                collect.deidentify(bundle, forbidden)
        finally:
            os.unlink(plan_path)


# ---------------------------------------------------------------------------
# (d) DeidLeakError 전파 — 삼켜지지(swallowed) 않는지 확인
# ---------------------------------------------------------------------------


class TestDeidLeakErrorPropagation:
    """DeidLeakError가 deidentify에서 전파되고 내부에서 삼켜지지 않는지 확인."""

    def test_deidentify_propagates_deid_leak_error(self):
        """deidentify가 DeidLeakError를 그대로 전파하는지 확인."""
        sentinel = "SENTINEL_PROPAGATION_TEST_IIIJJJ"
        bundle = {"leaked": sentinel}
        with pytest.raises(DeidLeakError) as exc_info:
            collect.deidentify(bundle, [sentinel])
        # detail이 비어있지 않아야 한다
        assert exc_info.value.detail

    def test_deidentify_does_not_swallow_error(self):
        """deidentify가 DeidLeakError를 포함한 예외를 RuntimeError로 변환하지 않는지 확인."""
        sentinel = "SENTINEL_NO_SWALLOW_TEST_KKKLL"
        bundle = {"leaked": sentinel}
        try:
            collect.deidentify(bundle, [sentinel])
            assert False, "예외가 발생해야 하는데 발생하지 않았다"
        except DeidLeakError:
            pass  # 올바른 동작 — DeidLeakError 그대로 전파
        except RuntimeError:
            assert False, "DeidLeakError가 RuntimeError로 변환됐다"
        except Exception as e:
            assert False, f"예상치 못한 예외 타입: {type(e).__name__}"

    def test_clean_bundle_returns_original_object(self):
        """통과 시 deidentify가 원본 bundle_obj를 그대로 반환하는지 확인."""
        bundle = {"user_input_characteristics": {"length_band": "S"}}
        result = collect.deidentify(bundle, [])
        assert result is bundle  # 동일 객체 참조 (복사 없음)


# ---------------------------------------------------------------------------
# (e) None/빈 forbidden_raw — 크래시 없음
# ---------------------------------------------------------------------------


class TestEdgeCaseForbiddenRaw:
    """None/빈 forbidden_raw에서 크래시가 없는지 확인."""

    def test_none_forbidden_raw_does_not_crash(self):
        """forbidden_raw=None 전달 시 크래시 없이 통과."""
        bundle = {"x": 1}
        result = collect.deidentify(bundle, None)
        assert result is bundle

    def test_empty_forbidden_raw_does_not_crash(self):
        """forbidden_raw=[] 전달 시 크래시 없이 통과."""
        bundle = {"x": 1}
        result = collect.deidentify(bundle, [])
        assert result is bundle

    def test_forbidden_raw_with_empty_strings_does_not_crash(self):
        """forbidden_raw에 빈 문자열이 포함돼도 크래시 없이 통과."""
        bundle = {"x": "hello"}
        result = collect.deidentify(bundle, ["", "  ", None])  # type: ignore[list-item]
        assert result is bundle

    def test_assemble_forbidden_raw_empty_inputs(self):
        """assemble_forbidden_raw에 빈 리스트를 전달해도 크래시 없음."""
        result = collect.assemble_forbidden_raw([], [])
        assert isinstance(result, list)

    def test_assemble_forbidden_raw_none_plan_path(self):
        """plan_path가 없는 artifact result에서 크래시 없음."""
        artifact_results = [
            {
                "by_ticket": {
                    "TEST-1": {
                        "plan": {
                            "plan_path": None,  # plan_path 없음
                        }
                    }
                }
            }
        ]
        result = collect.assemble_forbidden_raw(artifact_results, [])
        assert isinstance(result, list)

    def test_assemble_forbidden_raw_nonexistent_plan_path(self):
        """존재하지 않는 plan_path를 전달해도 크래시 없음 (get_plan_user_prompt가 None 반환)."""
        artifact_results = _make_artifact_results("/nonexistent/plan.md")
        result = collect.assemble_forbidden_raw(artifact_results, [])
        assert isinstance(result, list)
        # 존재하지 않는 파일 → user_prompt 없음 → forbidden에 추가되지 않음
        assert "/nonexistent/plan.md" not in result
