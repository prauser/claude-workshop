"""
test_bundle.py — bundle.py 단위 테스트.

검증 항목:
  ① serialize_bundle 형태·버전 필드
  ② validate_bundle 정상/누락
  ③ 업로드 경계 골든: sentinel/secret 주입 번들 → self-check가 막아 쓰일 바이트에 sentinel 0
  ④ 같은 입력 + 같은 generated_at → 동일 바이트 (결정성)
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

import bundle  # noqa: E402
from bundle import (  # noqa: E402
    BUNDLE_SCHEMA_VERSION,
    serialize_bundle,
    validate_bundle,
    upload_bundle,
    UploadResult,
)
from deid import DeidLeakError, BUNDLE_DUMPS_KWARGS, selfcheck_bundle  # noqa: E402
from collect import FORBIDDEN_MIN_TOKENS  # noqa: E402


# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------

_GENERATED_AT = "2026-06-19T00:00:00+09:00"
_SENTINEL = "SENTINEL_UNIQUE_RAW_周杰倫_42"


def _make_minimal_harvested() -> dict:
    """비어있는 harvested 구조."""
    return {
        "artifact_results": [],
        "session_results": [],
    }


def _make_harvested_with_ticket(
    ticket: str = "PRA-TEST",
    repo_name: str = "test-repo",
) -> dict:
    """ticket 한 개를 포함한 harvested 구조."""
    return {
        "artifact_results": [
            {
                "repo_path": "/tmp/test-repo",
                "repo_name": repo_name,
                "by_ticket": {
                    ticket: {
                        "plan": {
                            "ticket": ticket,
                            "plan_path": f"/tmp/test-repo/.claude/plans/{ticket}/plan.md",
                            "intent": {
                                "problem": "테스트 문제 설명",
                                "approach": "테스트 접근법",
                                "why": None,
                                "prd_ref": None,
                            },
                            "gate_events": [
                                {"gate": 0, "result": "ok"},
                            ],
                            "skip_presearch": 0,
                            "skip_gate2": 0,
                            "readiness_flags": [],
                            "risk_acks": [],
                            "intent_history_len": 0,
                            "plan_sha": "abc123",
                        },
                        "tasks": [
                            {
                                "task_id": "task-1-test",
                                "status": "success",
                                "role": "implementer",
                                "plan_deviations_count": 0,
                                "risk_acks": [],
                                "round_count": 1,
                                "path": f"/tmp/test-repo/.claude/tasks/done/task-1-test-result.md",
                            }
                        ],
                        "manifest": {
                            "status": "done",
                            "quality_gates": ["gate-0-pass"],
                            "path": f"/tmp/test-repo/.claude/runs/{ticket}/manifest.yaml",
                        },
                    }
                },
                "ticketless": [],
                "parse_errors": [],
            }
        ],
        "session_results": [
            {
                "by_ticket": {
                    ticket: [
                        {
                            "session_id": "sess-abc123",
                            "event_count": 5,
                            "events": [
                                {"seq": 0, "ts": "2026-06-19T00:00:00+09:00", "type": "user_turn",
                                 "char_len": 20, "token_count": 4},
                                {"seq": 1, "ts": "2026-06-19T00:00:01+09:00", "type": "assistant",
                                 "tokens": {"in": 100, "out": 50, "cache_read": 0, "cache_creation": 0}},
                                {"seq": 2, "ts": "2026-06-19T00:00:02+09:00", "type": "tool",
                                 "tool_name": "Read", "path": "/tmp/test.py",
                                 "pattern_summary": None, "command_len": None},
                            ],
                            "parse_errors": [],
                        }
                    ]
                },
                "ticketless": [],
                "parse_errors": [],
                "raw_user_turns_by_session": {
                    "sess-abc123": ["some user input here"]
                },
            }
        ],
    }


def _make_clean_characteristics(ticket: str = "PRA-TEST") -> dict:
    """raw NL 없는 추상화된 특성 dict."""
    return {
        ticket: {
            "length_band": "S",
            "has_ticket_ref": True,
            "request_shape": "feature",
            "specificity": "med",
            "mentions_external_tool": False,
            "language": "ko",
        }
    }


# ---------------------------------------------------------------------------
# TestSerializeBundle — ① 형태·버전 필드
# ---------------------------------------------------------------------------

class TestSerializeBundle:
    """serialize_bundle 형태·버전 필드 테스트."""

    def test_schema_version_field(self):
        """bundle_schema_version이 BUNDLE_SCHEMA_VERSION과 일치해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        assert b["bundle_schema_version"] == BUNDLE_SCHEMA_VERSION
        assert b["bundle_schema_version"] == "1.0"

    def test_generator_field(self):
        """generator 필드가 'wf-collect'이어야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        assert b["generator"] == "wf-collect"

    def test_generated_at_injected(self):
        """generated_at이 주입값과 일치해야 한다."""
        ts = "2026-06-19T12:34:56+09:00"
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=ts,
        )
        assert b["generated_at"] == ts

    def test_tickets_is_list(self):
        """tickets 필드가 list이어야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        assert isinstance(b["tickets"], list)

    def test_parse_errors_is_list(self):
        """parse_errors 필드가 list이어야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        assert isinstance(b["parse_errors"], list)

    def test_ticket_entry_has_required_keys(self):
        """ticket 엔트리에 필수 키(ticket, sessions, user_input_characteristics, evidence_ref)가 있어야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        assert len(b["tickets"]) >= 1
        entry = next(t for t in b["tickets"] if t["ticket"] == "PRA-TEST")
        assert "ticket" in entry
        assert "sessions" in entry
        assert "user_input_characteristics" in entry
        assert "evidence_ref" in entry

    def test_ticket_entry_plan_shape(self):
        """ticket 엔트리 plan 필드가 기대 키를 포함해야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        entry = next(t for t in b["tickets"] if t["ticket"] == "PRA-TEST")
        plan = entry.get("plan")
        assert plan is not None
        for key in ("intent", "gate_events", "skip_presearch", "skip_gate2",
                    "readiness_flags", "risk_acks", "intent_history_len", "plan_sha"):
            assert key in plan, f"plan에 {key!r} 누락"

    def test_ticket_entry_tasks_shape(self):
        """ticket 엔트리 tasks 필드가 기대 키를 포함해야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        entry = next(t for t in b["tickets"] if t["ticket"] == "PRA-TEST")
        assert isinstance(entry["tasks"], list)
        assert len(entry["tasks"]) >= 1
        task = entry["tasks"][0]
        for key in ("task_id", "status", "role", "plan_deviations", "risk_acks", "rounds"):
            assert key in task, f"task에 {key!r} 누락"

    def test_ticket_entry_manifest_shape(self):
        """ticket 엔트리 manifest 필드가 기대 키를 포함해야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        entry = next(t for t in b["tickets"] if t["ticket"] == "PRA-TEST")
        manifest = entry.get("manifest")
        assert manifest is not None
        assert "status" in manifest
        assert "quality_gates" in manifest

    def test_ticket_entry_sessions_shape(self):
        """ticket 엔트리 sessions 필드가 session_id + events를 포함해야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        entry = next(t for t in b["tickets"] if t["ticket"] == "PRA-TEST")
        assert isinstance(entry["sessions"], list)
        assert len(entry["sessions"]) >= 1
        session = entry["sessions"][0]
        assert "session_id" in session
        assert "events" in session

    def test_ticket_entry_evidence_ref_shape(self):
        """evidence_ref가 session_paths + artifact_paths를 포함해야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        entry = next(t for t in b["tickets"] if t["ticket"] == "PRA-TEST")
        eref = entry.get("evidence_ref")
        assert eref is not None
        assert "session_paths" in eref
        assert "artifact_paths" in eref

    def test_characteristics_mapped_to_ticket(self):
        """characteristics가 올바른 ticket에 매핑되어야 한다."""
        char = {
            "PRA-TEST": {"length_band": "L", "has_ticket_ref": True,
                         "request_shape": "feature", "specificity": "high",
                         "mentions_external_tool": False, "language": "ko"},
        }
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            char,
            generated_at=_GENERATED_AT,
        )
        entry = next(t for t in b["tickets"] if t["ticket"] == "PRA-TEST")
        assert entry["user_input_characteristics"]["length_band"] == "L"

    def test_raw_user_prompt_not_in_bundle(self):
        """raw user_prompt 원문이 번들에 포함되지 않아야 한다 (비식별 경계)."""
        raw_prompt = "먼저 linear로 티켓 만들고 그거 이용해서 하자"
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        bundle_str = json.dumps(b, **BUNDLE_DUMPS_KWARGS)
        assert raw_prompt not in bundle_str, "raw user_prompt 원문이 번들에 누출됨"

    def test_empty_harvested_produces_valid_structure(self):
        """빈 harvested에서도 유효한 번들 구조가 생성되어야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        errors = validate_bundle(b)
        assert errors == []


# ---------------------------------------------------------------------------
# TestValidateBundle — ② validate_bundle 정상/누락
# ---------------------------------------------------------------------------

class TestValidateBundle:
    """validate_bundle 정상/누락 테스트."""

    def test_valid_bundle_returns_empty_list(self):
        """유효한 번들은 빈 리스트를 반환해야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        errors = validate_bundle(b)
        assert errors == []

    def test_missing_bundle_schema_version(self):
        """bundle_schema_version 누락 시 오류를 반환해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        del b["bundle_schema_version"]
        errors = validate_bundle(b)
        assert any("bundle_schema_version" in e for e in errors)

    def test_wrong_bundle_schema_version(self):
        """잘못된 버전은 오류를 반환해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        b["bundle_schema_version"] = "9.9"
        errors = validate_bundle(b)
        assert any("bundle_schema_version" in e for e in errors)

    def test_missing_generated_at(self):
        """generated_at 누락 시 오류를 반환해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        del b["generated_at"]
        errors = validate_bundle(b)
        assert any("generated_at" in e for e in errors)

    def test_missing_tickets(self):
        """tickets 누락 시 오류를 반환해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        del b["tickets"]
        errors = validate_bundle(b)
        assert any("tickets" in e for e in errors)

    def test_missing_parse_errors(self):
        """parse_errors 누락 시 오류를 반환해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        del b["parse_errors"]
        errors = validate_bundle(b)
        assert any("parse_errors" in e for e in errors)

    def test_tickets_not_list(self):
        """tickets가 list가 아니면 오류를 반환해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        b["tickets"] = "not a list"
        errors = validate_bundle(b)
        assert any("tickets" in e for e in errors)

    def test_ticket_entry_missing_required_key(self):
        """ticket 엔트리에서 필수 키 누락 시 오류를 반환해야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        # ticket 엔트리에서 'sessions' 제거
        del b["tickets"][0]["sessions"]
        errors = validate_bundle(b)
        assert any("sessions" in e for e in errors)

    def test_non_dict_bundle_returns_error(self):
        """번들이 dict가 아니면 오류를 반환해야 한다."""
        errors = validate_bundle("not a dict")  # type: ignore
        assert len(errors) > 0

    def test_missing_generator(self):
        """generator 누락 시 오류를 반환해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        del b["generator"]
        errors = validate_bundle(b)
        assert any("generator" in e for e in errors)


# ---------------------------------------------------------------------------
# TestUploadBoundaryGolden — ③ 업로드 경계 골든
# ---------------------------------------------------------------------------

class TestUploadBoundaryGolden:
    """sentinel/secret 주입 → self-check 차단 → 쓰일/올라갈 바이트에 raw 부재."""

    def test_sentinel_in_bundle_blocks_upload(self, tmp_path):
        """sentinel을 번들에 직접 주입하면 upload_bundle이 DeidLeakError를 raise해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        # sentinel을 번들에 직접 주입
        b["_LEAKED"] = _SENTINEL

        out_path = str(tmp_path / "bundle_out.json")
        with pytest.raises(DeidLeakError):
            upload_bundle(b, None, dry_run=True, out=out_path, forbidden_raw=[_SENTINEL])

        # sentinel이 파일에 쓰이지 않았어야 한다 (self-check가 차단했으므로 파일 미생성)
        assert not os.path.exists(out_path), "self-check 차단 후 파일이 쓰여서는 안 된다"

    def test_sentinel_in_forbidden_raw_blocks_upload(self, tmp_path):
        """forbidden_raw에 sentinel이 있고 번들에 sentinel이 있으면 차단해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        # 번들에 sentinel 주입
        b["sessions_raw"] = _SENTINEL

        out_path = str(tmp_path / "bundle_out.json")
        with pytest.raises(DeidLeakError):
            upload_bundle(
                b, None, dry_run=True, out=out_path,
                forbidden_raw=[_SENTINEL],
            )
        assert not os.path.exists(out_path)

    def test_aws_secret_in_bundle_blocks_upload(self, tmp_path):
        """AWS access key를 번들에 주입하면 upload_bundle이 DeidLeakError를 raise해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        b["_LEAKED_KEY"] = "AKIAIOSFODNN7EXAMPLE0000"

        out_path = str(tmp_path / "bundle_out.json")
        with pytest.raises(DeidLeakError):
            upload_bundle(b, None, dry_run=True, out=out_path)
        assert not os.path.exists(out_path)

    def test_clean_bundle_upload_writes_file(self, tmp_path):
        """clean 번들은 dry-run으로 파일을 정상적으로 써야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        out_path = str(tmp_path / "bundle_clean.json")
        result = upload_bundle(
            b, None, dry_run=True, out=out_path, forbidden_raw=[]
        )
        assert result.ok
        assert result.dry_run
        assert result.out_path == out_path
        assert os.path.exists(out_path)

        # 쓰인 파일이 유효한 JSON이어야 한다
        with open(out_path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["bundle_schema_version"] == BUNDLE_SCHEMA_VERSION

    def test_sentinel_not_in_written_bytes(self, tmp_path):
        """clean 번들의 쓰인 바이트에 sentinel이 없어야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        out_path = str(tmp_path / "bundle_check.json")
        result = upload_bundle(
            b, None, dry_run=True, out=out_path, forbidden_raw=[_SENTINEL]
        )
        assert result.ok

        with open(out_path, encoding="utf-8") as f:
            content = f.read()
        assert _SENTINEL not in content, "sentinel이 쓰인 바이트에 있어서는 안 된다"

    def test_slack_secret_in_bundle_blocks_upload(self, tmp_path):
        """Slack 토큰을 번들에 주입하면 upload_bundle이 DeidLeakError를 raise해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        b["_SLACK"] = ("xoxb-" + "1234567890" + "-abcdefghijklmnop")

        out_path = str(tmp_path / "bundle_slack.json")
        with pytest.raises(DeidLeakError):
            upload_bundle(b, None, dry_run=True, out=out_path)
        assert not os.path.exists(out_path)

    def test_pem_in_bundle_blocks_upload(self, tmp_path):
        """PEM 헤더를 번들에 주입하면 upload_bundle이 DeidLeakError를 raise해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        b["_PEM"] = "-----BEGIN RSA PRIVATE KEY-----"

        out_path = str(tmp_path / "bundle_pem.json")
        with pytest.raises(DeidLeakError):
            upload_bundle(b, None, dry_run=True, out=out_path)
        assert not os.path.exists(out_path)

    def test_dry_run_no_target_required(self, tmp_path):
        """dry-run 모드에서는 target이 없어도 동작해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        out_path = str(tmp_path / "bundle_notarget.json")
        # target=None, dry_run=True — 오류 없어야 한다
        result = upload_bundle(b, None, dry_run=True, out=out_path)
        assert result.ok

    def test_live_upload_requires_target(self, tmp_path):
        """live upload(dry_run=False)는 target이 없으면 ValueError를 raise해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        # env를 명시적으로 비워서 fallback도 없게 한다
        old_env = os.environ.pop("WF_COLLECT_TARGET", None)
        try:
            with pytest.raises(ValueError, match="target"):
                upload_bundle(b, None, dry_run=False)
        finally:
            if old_env is not None:
                os.environ["WF_COLLECT_TARGET"] = old_env

    def test_audit_report_included_in_result(self, tmp_path):
        """dry-run 결과에 audit_lines가 포함되어야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        out_path = str(tmp_path / "bundle_audit.json")
        result = upload_bundle(b, None, dry_run=True, out=out_path)
        assert result.audit_lines is not None
        assert len(result.audit_lines) > 0
        # 감사 리포트에 "[AUDIT]" 태그가 있어야 한다
        assert any("[AUDIT]" in line for line in result.audit_lines)


# ---------------------------------------------------------------------------
# TestDeterminism — ④ 결정성 (같은 generated_at → 동일 바이트)
# ---------------------------------------------------------------------------

class TestDeterminism:
    """같은 입력 + 같은 generated_at → 동일 바이트."""

    def test_same_input_same_bytes(self):
        """같은 harvested + characteristics + generated_at → 동일한 직렬화 바이트."""
        harvested = _make_harvested_with_ticket("PRA-TEST")
        char = _make_clean_characteristics("PRA-TEST")
        ts = _GENERATED_AT

        b1 = serialize_bundle(harvested, char, generated_at=ts)
        b2 = serialize_bundle(harvested, char, generated_at=ts)

        bytes1 = json.dumps(b1, **BUNDLE_DUMPS_KWARGS)
        bytes2 = json.dumps(b2, **BUNDLE_DUMPS_KWARGS)

        assert bytes1 == bytes2, "같은 입력이지만 직렬화 바이트가 달라졌다"

    def test_different_generated_at_different_bytes(self):
        """different generated_at → 다른 직렬화 바이트."""
        harvested = _make_harvested_with_ticket("PRA-TEST")
        char = _make_clean_characteristics("PRA-TEST")

        b1 = serialize_bundle(harvested, char, generated_at="2026-06-19T00:00:00+09:00")
        b2 = serialize_bundle(harvested, char, generated_at="2026-06-19T01:00:00+09:00")

        bytes1 = json.dumps(b1, **BUNDLE_DUMPS_KWARGS)
        bytes2 = json.dumps(b2, **BUNDLE_DUMPS_KWARGS)

        assert bytes1 != bytes2

    def test_upload_dry_run_writes_deterministic_bytes(self, tmp_path):
        """upload_bundle dry-run이 결정론적 바이트를 파일에 써야 한다."""
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )

        out1 = str(tmp_path / "b1.json")
        out2 = str(tmp_path / "b2.json")

        upload_bundle(b, None, dry_run=True, out=out1)
        upload_bundle(b, None, dry_run=True, out=out2)

        with open(out1, encoding="utf-8") as f:
            content1 = f.read()
        with open(out2, encoding="utf-8") as f:
            content2 = f.read()

        assert content1 == content2, "같은 번들을 두 번 쓴 바이트가 달라졌다"

    def test_bundle_schema_version_constant(self):
        """BUNDLE_SCHEMA_VERSION이 '1.0'이어야 한다."""
        assert BUNDLE_SCHEMA_VERSION == "1.0"

    def test_bundle_uses_bundle_dumps_kwargs(self, tmp_path):
        """upload_bundle이 쓴 파일이 BUNDLE_DUMPS_KWARGS로 직렬화된 것과 동일해야 한다."""
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        out_path = str(tmp_path / "b_check.json")
        upload_bundle(b, None, dry_run=True, out=out_path)

        with open(out_path, encoding="utf-8") as f:
            content = f.read()

        expected = json.dumps(b, **BUNDLE_DUMPS_KWARGS)
        assert content == expected, "쓰인 파일 바이트가 BUNDLE_DUMPS_KWARGS 직렬화와 다르다"


# ---------------------------------------------------------------------------
# TestForbiddenRawPipelineIntegration — p2-A 통합 테스트
# ---------------------------------------------------------------------------

class TestForbiddenRawPipelineIntegration:
    """forbidden_raw가 upload_bundle_stage까지 실제로 전달되는지 검증 (p2-A).

    collect.py cmd_run이 assemble_forbidden_raw()를 수행한 뒤
    필터된 forbidden_raw를 upload_bundle에 전달하는 경로를 직접 검증.
    """

    # 4 토큰 이상인 sentinel — selfcheck 슬라이딩 윈도우 최솟값 충족
    _MULTI_WORD_SENTINEL = "위의 내용 진행해주되 먼저 linear로 티켓 만들고 그거 이용해서 하자"

    def test_sentinel_in_forbidden_raw_and_bundle_raises(self, tmp_path):
        """forbidden_raw에 multi-word sentinel이 있고 번들에 그 sentinel이 포함되면
        upload_bundle이 DeidLeakError를 raise해야 한다 (CODE-enforced de-id self-check).
        """
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        # 번들에 sentinel 직접 주입 (raw NL 누출 시뮬레이션)
        b["_leaked_user_prompt"] = self._MULTI_WORD_SENTINEL

        out_path = str(tmp_path / "bundle_sentinel.json")
        with pytest.raises(DeidLeakError):
            upload_bundle(
                b,
                None,
                dry_run=True,
                out=out_path,
                forbidden_raw=[self._MULTI_WORD_SENTINEL],
            )
        # 파일이 쓰이지 않았어야 한다 (전부-또는-전무)
        assert not os.path.exists(out_path), "DeidLeakError 후 파일이 쓰여서는 안 된다"

    def test_clean_bundle_with_sentinel_in_forbidden_raw_passes(self, tmp_path):
        """번들에 sentinel이 없으면(LLM 추상화 완료 상태) forbidden_raw에 sentinel이
        있어도 upload_bundle이 성공해야 한다.
        """
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        out_path = str(tmp_path / "bundle_clean_sentinel.json")
        result = upload_bundle(
            b,
            None,
            dry_run=True,
            out=out_path,
            forbidden_raw=[self._MULTI_WORD_SENTINEL],
        )
        assert result.ok
        assert os.path.exists(out_path)
        # 쓰인 파일에 sentinel 없음 확인
        with open(out_path, encoding="utf-8") as f:
            content = f.read()
        assert self._MULTI_WORD_SENTINEL not in content

    def test_short_token_entry_does_not_block_clean_bundle(self, tmp_path):
        """단어 수 < 4인 forbidden_raw 항목(예: 'ok')은 필터돼야 하며,
        번들에 'ok' 가 메타데이터로 포함돼도 차단하지 않아야 한다.
        그 판단은 collect.py 필터 로직에서 수행하므로, 여기서는 upload_bundle에
        filtered list(빈 리스트)를 전달해 통과를 확인한다.
        """
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        # 단어 수 < 4 항목만 filtered out되어 빈 리스트로 전달
        short_forbidden = [r for r in ["ok", "네", "B 형태로"] if len(r.split()) >= 4]
        assert short_forbidden == [], "단어 수 < 4 항목은 필터돼야 한다"

        out_path = str(tmp_path / "bundle_short_token.json")
        result = upload_bundle(
            b,
            None,
            dry_run=True,
            out=out_path,
            forbidden_raw=short_forbidden,
        )
        assert result.ok


# ---------------------------------------------------------------------------
# TestRound3Regression — p2 회귀 테스트 (Round 3)
# ---------------------------------------------------------------------------

class TestRound3Regression:
    """Round 3 P0 fix 회귀 테스트.

    (a) 100단어 초과 genuine user NL이 번들에 나타나면 DeidLeakError를 발생시킨다
        (Round 2의 ≤100 상한으로는 놓쳤던 케이스).
    (b) user_prompt가 intent.problem에 verbatim 포함돼도 plaintext_subtrees 제외 시
        DeidLeakError가 발생하지 않는다. plaintext_subtrees=None 시 발생한다(경계 문서화).
    (c) 위 두 테스트는 collect.FORBIDDEN_MIN_TOKENS 상수를 import해 하한 기준을 확인한다.
    """

    def _make_long_user_nl(self) -> str:
        """101개 단어의 genuine user NL 문자열을 생성한다."""
        # 실제 한국어 단어처럼 보이지만 식별 가능한 sentinel 포함
        words = ["단어"] * 50 + ["SENTINEL_LONG_NL"] + ["단어"] * 50
        return " ".join(words)  # 101 words

    def test_over100_word_user_nl_in_bundle_triggers_deid_error(self, tmp_path):
        """100단어 초과 genuine user NL 문자열이 번들에 직접 포함되면
        DeidLeakError가 발생해야 한다.

        Round 2에서는 ≤100 상한 필터로 이 문자열이 forbidden_raw에서 제외됐다.
        Round 3 수정: 상한 제거로 전달되므로 누출이 탐지된다.
        """
        long_nl = self._make_long_user_nl()
        # 101 단어 확인
        assert len(long_nl.split()) > 100, "테스트 픽스처가 101단어 이상이어야 한다"
        # FORBIDDEN_MIN_TOKENS 하한 충족
        assert len(long_nl.split()) >= FORBIDDEN_MIN_TOKENS

        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        # 번들에 긴 NL 직접 주입 (누출 시뮬레이션)
        b["_leaked_long_nl"] = long_nl

        out_path = str(tmp_path / "bundle_long.json")
        with pytest.raises(DeidLeakError, match="forbidden_raw 누출"):
            upload_bundle(
                b,
                None,
                dry_run=True,
                out=out_path,
                forbidden_raw=[long_nl],
            )
        # 파일이 쓰이지 않았어야 한다 (전부-또는-전무)
        assert not os.path.exists(out_path), "DeidLeakError 후 파일이 생성돼서는 안 된다"

    def test_user_prompt_verbatim_in_intent_no_error_when_excluded(self, tmp_path):
        """user_prompt 원문이 intent.problem에 verbatim 포함되더라도
        plaintext_subtrees=["tickets.plan.intent"]를 지정하면 DeidLeakError가
        발생하지 않아야 한다 (intent.*는 spec-plan AI 의역 — 비식별 대상 아님).

        이것이 p2-b 수정의 핵심 보장이다.
        """
        user_prompt = "위의 내용 진행해주되 먼저 linear로 티켓 만들고 그거 이용해서 하자"
        assert len(user_prompt.split()) >= FORBIDDEN_MIN_TOKENS

        # 번들에 user_prompt가 intent.problem에 verbatim 등장하도록 구성
        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        # tickets[0].plan.intent.problem에 user_prompt 삽입
        b["tickets"] = [{
            "ticket": "PRA-TEST",
            "repo": "test",
            "plan": {
                "intent": {
                    "problem": user_prompt,  # verbatim user_prompt in intent
                    "approach": "테스트 접근",
                    "why": None,
                },
                "gate_events": [],
                "skip_presearch": 0,
                "skip_gate2": 0,
                "readiness_flags": [],
                "risk_acks": [],
                "intent_history_len": 0,
                "plan_sha": "abc123def456",
            },
            "tasks": [],
            "manifest": None,
            "sessions": [],
            "user_input_characteristics": {},
            "evidence_ref": {"session_paths": [], "artifact_paths": []},
        }]

        out_path = str(tmp_path / "bundle_intent_excluded.json")

        # plaintext_subtrees로 intent.*를 NL-check에서 제외 → 통과해야 한다
        result = upload_bundle(
            b,
            None,
            dry_run=True,
            out=out_path,
            forbidden_raw=[user_prompt],
            plaintext_subtrees=["tickets.plan.intent"],
        )
        assert result.ok, "intent.* 제외 시 DeidLeakError가 발생하면 안 된다"
        assert os.path.exists(out_path)

    def test_user_prompt_verbatim_in_intent_raises_without_exclusion(self, tmp_path):
        """user_prompt 원문이 intent.problem에 verbatim 포함되고
        plaintext_subtrees를 지정하지 않으면 DeidLeakError가 발생해야 한다.

        이것은 경계(boundary)를 문서화한다: intent.* 제외 없이는 false-positive가 발생.
        """
        user_prompt = "위의 내용 진행해주되 먼저 linear로 티켓 만들고 그거 이용해서 하자"
        assert len(user_prompt.split()) >= FORBIDDEN_MIN_TOKENS

        b = serialize_bundle(
            _make_minimal_harvested(),
            {},
            generated_at=_GENERATED_AT,
        )
        b["tickets"] = [{
            "ticket": "PRA-TEST",
            "repo": "test",
            "plan": {
                "intent": {
                    "problem": user_prompt,  # verbatim user_prompt in intent
                    "approach": "테스트 접근",
                    "why": None,
                },
                "gate_events": [],
                "skip_presearch": 0,
                "skip_gate2": 0,
                "readiness_flags": [],
                "risk_acks": [],
                "intent_history_len": 0,
                "plan_sha": "abc123def456",
            },
            "tasks": [],
            "manifest": None,
            "sessions": [],
            "user_input_characteristics": {},
            "evidence_ref": {"session_paths": [], "artifact_paths": []},
        }]

        out_path = str(tmp_path / "bundle_intent_no_exclusion.json")

        # plaintext_subtrees=None(기본) → 전체 번들 검사 → DeidLeakError 발생
        with pytest.raises(DeidLeakError, match="forbidden_raw 누출"):
            upload_bundle(
                b,
                None,
                dry_run=True,
                out=out_path,
                forbidden_raw=[user_prompt],
                plaintext_subtrees=None,
            )
        assert not os.path.exists(out_path), "DeidLeakError 후 파일이 생성돼서는 안 된다"


# ---------------------------------------------------------------------------
# TestLegacySkipGrillCount — p2-B: schema-drift 신호 end-to-end
# ---------------------------------------------------------------------------

class TestLegacySkipGrillCount:
    """plan.skip_grill_count legacy indicator가 번들에 올바르게 반영되는지 검증.

    P1-1: legacy skip_grill_count는 schema-drift 신호다.
    bundle.py는 이 값을 plan.skip_grill_count로 emit해야 한다.
    """

    def _make_harvested_with_legacy_skip_grill(
        self,
        ticket: str = "PRA-LEGACY",
        skip_grill_count: int = 3,
    ) -> dict:
        """skip_grill_count를 포함한 plan_rec을 담은 harvested 구조."""
        return {
            "artifact_results": [
                {
                    "repo_path": "/tmp/legacy-repo",
                    "repo_name": "legacy-repo",
                    "by_ticket": {
                        ticket: {
                            "plan": {
                                "ticket": ticket,
                                "plan_path": f"/tmp/legacy-repo/.claude/plans/{ticket}/plan.md",
                                "intent": {
                                    "problem": "레거시 플랜 테스트",
                                    "approach": None,
                                    "why": None,
                                    "prd_ref": None,
                                },
                                "gate_events": [],
                                "skip_presearch": 0,
                                "skip_gate2": 0,
                                "readiness_flags": [],
                                "risk_acks": [],
                                "intent_history_len": 0,
                                "plan_sha": "def456",
                                # legacy indicator — harvest_artifacts가 보존해 전달
                                "skip_grill_count": skip_grill_count,
                            },
                            "tasks": [],
                            "manifest": None,
                        }
                    },
                    "ticketless": [],
                    "parse_errors": [],
                }
            ],
            "session_results": [],
        }

    def test_skip_grill_count_emitted_when_present(self):
        """plan에 skip_grill_count가 있으면 번들 plan.skip_grill_count에 값이 나타나야 한다."""
        harvested = self._make_harvested_with_legacy_skip_grill(
            ticket="PRA-LEGACY", skip_grill_count=3
        )
        b = serialize_bundle(harvested, {}, generated_at=_GENERATED_AT)

        entry = next(t for t in b["tickets"] if t["ticket"] == "PRA-LEGACY")
        plan = entry.get("plan")
        assert plan is not None, "plan 필드가 없다"
        assert "skip_grill_count" in plan, "plan에 skip_grill_count 필드가 없다"
        assert plan["skip_grill_count"] == 3, (
            f"skip_grill_count 값 불일치: 기대=3, 실제={plan['skip_grill_count']!r}"
        )

    def test_skip_grill_count_none_when_absent(self):
        """plan에 skip_grill_count가 없으면 번들 plan.skip_grill_count는 None이어야 한다."""
        # skip_grill_count 없는 일반 harvested (_make_harvested_with_ticket은 skip_grill_count 없음)
        b = serialize_bundle(
            _make_harvested_with_ticket("PRA-TEST"),
            _make_clean_characteristics("PRA-TEST"),
            generated_at=_GENERATED_AT,
        )
        entry = next(t for t in b["tickets"] if t["ticket"] == "PRA-TEST")
        plan = entry.get("plan")
        assert plan is not None
        # skip_grill_count 키가 없거나 None이어야 한다
        assert plan.get("skip_grill_count") is None, (
            f"skip_grill_count가 None이 아님: {plan.get('skip_grill_count')!r}"
        )

    def test_skip_grill_count_zero_is_preserved(self):
        """skip_grill_count=0인 경우도 보존되어야 한다 (absent와 구별)."""
        harvested = self._make_harvested_with_legacy_skip_grill(
            ticket="PRA-ZERO", skip_grill_count=0
        )
        b = serialize_bundle(harvested, {}, generated_at=_GENERATED_AT)

        entry = next(t for t in b["tickets"] if t["ticket"] == "PRA-ZERO")
        plan = entry.get("plan")
        assert plan is not None
        assert "skip_grill_count" in plan, "plan에 skip_grill_count 필드가 없다"
        assert plan["skip_grill_count"] == 0, (
            f"skip_grill_count=0이 보존되지 않음: {plan['skip_grill_count']!r}"
        )
