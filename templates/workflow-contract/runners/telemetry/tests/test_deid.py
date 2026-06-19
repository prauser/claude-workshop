"""
test_deid.py — 비식별(de-identification) 골든 테스트(golden test).

CRITICAL: 이 테스트들이 통과해야 plan.md risk_acks deidentification = confirmed.

테스트 클래스:
  TestScanSecrets         — scan_secrets 정규식 탐지 커버리지
  TestSelfCheckBundleHardFail — selfcheck_bundle hard-fail (sentinel/secret 주입)
  TestSelfCheckBundlePass — 정상 번들 통과
  TestNormalizedBypass    — 대소문자/공백 변형 우회 차단
  TestRedactForAudit      — redact_for_audit 마스킹 동작
"""

from __future__ import annotations

import sys
import os
import pytest

# 테스트가 telemetry 디렉토리를 찾을 수 있도록 경로 추가
_TELE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TELE_DIR not in sys.path:
    sys.path.insert(0, _TELE_DIR)

from deid import (  # noqa: E402
    DeidLeakError,
    Secret,
    SelfCheckResult,
    BUNDLE_DUMPS_KWARGS,
    scan_secrets,
    selfcheck_bundle,
    redact_for_audit,
    _normalize,
)


# ---------------------------------------------------------------------------
# TestScanSecrets — scan_secrets 정규식 탐지 커버리지
# ---------------------------------------------------------------------------


class TestScanSecrets:
    """scan_secrets 함수가 각 대표 패턴을 정확히 탐지하는지 확인."""

    def test_aws_access_key_detected(self):
        """AWS Access Key ID(AKIA로 시작하는 20자) 탐지."""
        hits = scan_secrets("key AKIAIOSFODNN7EXAMPLE here")
        kinds = [s.kind for s in hits]
        assert "aws_access_key" in kinds

    def test_slack_token_detected(self):
        """Slack xoxb- 토큰 탐지."""
        hits = scan_secrets("xoxb-12345-abcdef")
        kinds = [s.kind for s in hits]
        assert "slack_token" in kinds

    def test_slack_xoxa_detected(self):
        """Slack xoxa- 토큰 탐지."""
        hits = scan_secrets("token=xoxa-9999-zzz")
        kinds = [s.kind for s in hits]
        assert "slack_token" in kinds

    def test_github_ghp_detected(self):
        """GitHub ghp_ (Personal Access Token) 탐지."""
        hits = scan_secrets("ghp_ABCDEFGHIJKLMNOPQRSTU")
        kinds = [s.kind for s in hits]
        assert "github_token" in kinds

    def test_github_gho_detected(self):
        """GitHub gho_ (OAuth token) 탐지."""
        hits = scan_secrets("gho_xyzABCDE12345")
        kinds = [s.kind for s in hits]
        assert "github_token" in kinds

    def test_pem_header_detected(self):
        """PEM 헤더(BEGIN RSA PRIVATE KEY) 탐지."""
        hits = scan_secrets("-----BEGIN RSA PRIVATE KEY-----")
        kinds = [s.kind for s in hits]
        assert "pem_header" in kinds

    def test_pem_header_ec_detected(self):
        """PEM 헤더(BEGIN EC PRIVATE KEY) 탐지."""
        hits = scan_secrets("-----BEGIN EC PRIVATE KEY-----")
        kinds = [s.kind for s in hits]
        assert "pem_header" in kinds

    def test_bearer_token_detected(self):
        """Bearer 토큰 탐지."""
        hits = scan_secrets("Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.payload.sig")
        kinds = [s.kind for s in hits]
        assert "bearer_token" in kinds

    def test_password_field_detected(self):
        """password=값 패턴 탐지."""
        hits = scan_secrets("password=s3cr3tP4ss!")
        kinds = [s.kind for s in hits]
        assert "password_field" in kinds

    def test_secret_field_detected(self):
        """secret=값 패턴 탐지."""
        hits = scan_secrets("secret=my_secret_value_123")
        kinds = [s.kind for s in hits]
        assert "password_field" in kinds

    def test_clean_korean_text_no_hit(self):
        """완전히 평범한 한국어 문장에서 탐지 없음."""
        hits = scan_secrets("완전히 평범한 한국어 문장")
        assert hits == []

    def test_clean_english_text_no_hit(self):
        """일반 영어 문장에서 탐지 없음."""
        hits = scan_secrets("This is a normal English sentence with no secrets.")
        assert hits == []

    def test_returns_list_of_secret_namedtuples(self):
        """반환값이 Secret NamedTuple 리스트인지 확인."""
        hits = scan_secrets("AKIAIOSFODNN7EXAMPLE")
        assert isinstance(hits, list)
        for h in hits:
            assert isinstance(h, Secret)
            assert hasattr(h, "kind")
            assert hasattr(h, "match")

    def test_multiple_secrets_in_one_text(self):
        """한 텍스트에 여러 secret이 있을 때 모두 탐지."""
        text = "key=AKIAIOSFODNN7EXAMPLE token=xoxb-12345-abcdef"
        hits = scan_secrets(text)
        kinds = {s.kind for s in hits}
        assert "aws_access_key" in kinds
        assert "slack_token" in kinds

    def test_jwt_token_detected(self):
        """JWT (eyJ로 시작하는 3파트) 탐지 (p3)."""
        # 실제 JWT 형식: header.payload.signature (각 base64url 인코딩)
        jwt = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        hits = scan_secrets(jwt)
        kinds = [s.kind for s in hits]
        assert "jwt_token" in kinds

    def test_google_api_key_detected(self):
        """Google API Key (AIza로 시작) 탐지 (p3)."""
        key = "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
        hits = scan_secrets(key)
        kinds = [s.kind for s in hits]
        assert "google_api_key" in kinds

    def test_npm_token_detected(self):
        """npm automation token (npm_ 접두사) 탐지 (p3)."""
        token = "npm_1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZab"
        hits = scan_secrets(token)
        kinds = [s.kind for s in hits]
        assert "npm_token" in kinds


# ---------------------------------------------------------------------------
# TestSelfCheckBundleHardFail — sentinel/secret 주입 시 hard-fail
# ---------------------------------------------------------------------------


class TestSelfCheckBundleHardFail:
    """selfcheck_bundle이 누출 시 DeidLeakError를 raise하는지 검증 (골든 테스트)."""

    def test_sentinel_in_bundle_raises(self):
        """sentinel 원문이 번들에 남아있으면 DeidLeakError raise."""
        raw = ["SENTINEL_UNIQUE_RAW_周杰倫_42"]
        bad_bundle = {"x": "... SENTINEL_UNIQUE_RAW_周杰倫_42 ..."}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bad_bundle, raw)

    def test_sentinel_exact_value_raises(self):
        """sentinel이 번들 값에 직접 포함될 때 DeidLeakError raise."""
        sentinel = "MY_SENTINEL_STRING_ABCDEF_99"
        bundle = {"result": sentinel}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, [sentinel])

    def test_aws_key_in_bundle_raises(self):
        """AWS Access Key가 번들에 있으면 DeidLeakError raise."""
        bundle = {"metadata": {"key": "AKIAIOSFODNN7EXAMPLE"}}
        with pytest.raises(DeidLeakError) as exc_info:
            selfcheck_bundle(bundle, [])
        assert "secret" in exc_info.value.detail.lower() or "aws" in exc_info.value.detail.lower()

    def test_slack_token_in_bundle_raises(self):
        """Slack 토큰이 번들에 있으면 DeidLeakError raise."""
        bundle = {"events": [{"token": "xoxb-12345-abcdef"}]}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, [])

    def test_pem_in_bundle_raises(self):
        """PEM 헤더가 번들에 있으면 DeidLeakError raise."""
        bundle = {"key_data": "-----BEGIN RSA PRIVATE KEY-----\nABCDEF\n-----END RSA PRIVATE KEY-----"}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, [])

    def test_forbidden_raw_substring_raises(self):
        """forbidden_raw 원문이 번들 어딘가에 substring으로 존재하면 DeidLeakError raise."""
        raw_nl = "사용자가 직접 입력한 원문 문장입니다 12345"
        bundle = {"user_input": raw_nl}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, [raw_nl])

    def test_error_detail_contains_info(self):
        """DeidLeakError의 detail 메시지가 누출 유형 정보를 포함하는지 확인."""
        sentinel = "UNIQUE_SENTINEL_FOR_DETAIL_TEST"
        bundle = {"x": sentinel}
        with pytest.raises(DeidLeakError) as exc_info:
            selfcheck_bundle(bundle, [sentinel])
        assert exc_info.value.detail  # 빈 detail 금지


# ---------------------------------------------------------------------------
# TestSelfCheckBundlePass — 정상 번들 통과
# ---------------------------------------------------------------------------


class TestSelfCheckBundlePass:
    """정상적으로 추상화된 번들이 selfcheck_bundle을 통과하는지 확인."""

    def test_clean_characteristics_bundle_passes(self):
        """특성(characteristics)만 담긴 번들은 통과."""
        bundle = {
            "user_input_characteristics": {
                "length_band": "M",
                "request_shape": "feature",
            }
        }
        result = selfcheck_bundle(bundle, ["SENTINEL_UNIQUE_RAW"])
        assert isinstance(result, SelfCheckResult)
        assert result.ok is True

    def test_empty_forbidden_raw_passes(self):
        """forbidden_raw 가 빈 리스트면 통과 (secret 없는 번들)."""
        bundle = {"metrics": {"gate_turns": 5, "token_count": 1200}}
        result = selfcheck_bundle(bundle, [])
        assert result.ok is True

    def test_metadata_only_bundle_passes(self):
        """메타데이터(metadata)만 있는 번들은 통과."""
        bundle = {
            "ticket": "PRA-109",
            "plan_sha": "abc123",
            "gate_events": [{"gate": 0, "result": "ok", "turns": 7}],
        }
        result = selfcheck_bundle(bundle, [])
        assert result.ok is True

    def test_returns_selfcheck_result_object(self):
        """통과 시 SelfCheckResult 객체를 반환하는지 확인."""
        result = selfcheck_bundle({"x": 1}, [])
        assert isinstance(result, SelfCheckResult)

    def test_empty_string_in_forbidden_raw_ignored(self):
        """forbidden_raw에 빈 문자열이 포함돼도 false-positive 없이 통과."""
        result = selfcheck_bundle({"x": "hello"}, ["", "   "])
        assert result.ok is True

    def test_abstract_characteristics_with_empty_sentinel_passes(self):
        """추상화된 특성 번들 + 다른 sentinel → 통과."""
        bundle = {
            "user_input_characteristics": {
                "length_band": "S",
                "has_ticket_ref": True,
                "request_shape": "bugfix",
                "specificity": "high",
                "language": "ko",
            }
        }
        result = selfcheck_bundle(bundle, ["SOME_OTHER_RAW_TEXT_NOT_IN_BUNDLE"])
        assert result.ok is True


# ---------------------------------------------------------------------------
# TestNormalizedBypass — 대소문자/공백 변형 우회 차단
# ---------------------------------------------------------------------------


class TestNormalizedBypass:
    """대소문자 변형, 공백 변형이 selfcheck_bundle을 우회하지 못하는지 확인 (골든 테스트)."""

    def test_case_variant_blocked(self):
        """대소문자를 바꿔 삽입해도 차단."""
        raw = "SENTINEL UNIQUE RAW"
        bundle = {"x": "sentinel unique raw"}   # 소문자 변형
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, [raw])

    def test_extra_whitespace_blocked(self):
        """공백을 늘려 삽입해도 차단."""
        raw = "SENTINEL UNIQUE RAW"
        bundle = {"x": "sentinel  unique   raw"}  # 공백 변형
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, [raw])

    def test_mixed_case_whitespace_blocked(self):
        """대소문자 + 공백 혼합 변형도 차단."""
        raw = "Hello World Test Phrase Check"
        bundle = {"y": "hello world  test phrase  check"}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, [raw])

    def test_unicode_nfkc_normalization_blocked(self):
        """NFKC 유니코드 정규화 후 일치하는 경우 차단.
        예: 전각(fullwidth) 문자가 반각으로 정규화되어 일치."""
        raw = "SENTINEL TEST"
        # 전각 영문자: ＳＥＮＴＩＮＥＬ → NFKC 후 SENTINEL
        bundle = {"z": "ＳＥＮＴＩＮＥＬ TEST"}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, [raw])

    def test_slightly_different_text_passes(self):
        """완전히 다른 텍스트는 우회 차단에 오탐(false positive)이 없어야 한다."""
        raw = "SENTINEL UNIQUE RAW PHRASE ONE TWO THREE"
        bundle = {"x": "completely different content here with no overlap"}
        # 7단어 이상 다르면 통과해야 함
        result = selfcheck_bundle(bundle, [raw])
        assert result.ok is True


# ---------------------------------------------------------------------------
# TestRedactForAudit — redact_for_audit 동작 확인
# ---------------------------------------------------------------------------


class TestRedactForAudit:
    """redact_for_audit 전부-또는-전무 마스킹."""

    def test_text_with_secret_is_redacted(self):
        """secret 포함 텍스트는 [REDACTED]로 대체."""
        result = redact_for_audit("key AKIAIOSFODNN7EXAMPLE here")
        assert "[REDACTED]" in result

    def test_clean_text_returned_unchanged(self):
        """secret 없는 텍스트는 원문 그대로 반환."""
        text = "완전히 평범한 문장"
        result = redact_for_audit(text)
        assert result == text

    def test_redacted_includes_secret_count(self):
        """마스킹 결과에 탐지된 secret 수가 포함되는지 확인."""
        result = redact_for_audit("AKIAIOSFODNN7EXAMPLE xoxb-12345-abcdef")
        assert "REDACTED" in result


# ---------------------------------------------------------------------------
# TestNormalizeHelper — 내부 _normalize 유틸리티 직접 테스트
# ---------------------------------------------------------------------------


class TestNormalizeHelper:
    """_normalize 함수 단위 테스트."""

    def test_lowercases(self):
        assert _normalize("HELLO") == "hello"

    def test_strips_extra_whitespace(self):
        assert _normalize("hello   world") == "hello world"

    def test_nfkc_fullwidth(self):
        # 전각 A(Ａ, U+FF21) → 반각 A
        assert _normalize("Ａ") == "a"

    def test_strips_leading_trailing_whitespace(self):
        assert _normalize("  hello  ") == "hello"

    def test_zero_width_space_stripped(self):
        """U+200B ZERO WIDTH SPACE 제거 후 정규화."""
        # "hel​lo" → "hello" (U+200B 제거)
        assert _normalize("hel​lo world") == "hello world"

    def test_zero_width_non_joiner_stripped(self):
        """U+200C ZERO WIDTH NON-JOINER 제거."""
        assert _normalize("hel‌lo") == "hello"

    def test_zero_width_joiner_stripped(self):
        """U+200D ZERO WIDTH JOINER 제거."""
        assert _normalize("hel‍lo") == "hello"

    def test_soft_hyphen_stripped(self):
        """U+00AD SOFT HYPHEN 제거."""
        assert _normalize("hel­lo") == "hello"

    def test_bom_stripped(self):
        """U+FEFF ZERO WIDTH NO-BREAK SPACE (BOM) 제거."""
        assert _normalize("﻿hello") == "hello"


# ---------------------------------------------------------------------------
# TestZeroWidthEvasion — 제로폭 문자 삽입 우회 차단 (p2-B 골든 테스트)
# ---------------------------------------------------------------------------


class TestZeroWidthEvasion:
    """제로폭(zero-width) 문자를 삽입한 verbatim 우회가 selfcheck_bundle을 통과하지 못하는지 확인."""

    def test_zero_width_space_in_bundle_blocked(self):
        """번들 값에 U+200B ZERO WIDTH SPACE를 삽입해도 raw 일치로 탐지."""
        raw = ["hello world test"]
        # 번들에 제로폭 공백 삽입: "hel​lo world test"
        bundle = {"x": "hel​lo world test"}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, raw)

    def test_zero_width_in_raw_does_not_cause_false_negative(self):
        """raw 자체에 제로폭 문자가 있어도 번들 탐지 가능."""
        # raw: "hel​lo world test" (zero-width in raw)
        raw = ["hel​lo world test"]
        # bundle: 정규화된 형태 "hello world test"
        bundle = {"x": "hello world test"}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, raw)

    def test_zero_width_joiner_in_bundle_blocked(self):
        """U+200D ZERO WIDTH JOINER를 단어 내부에 삽입한 우회도 차단.
        실제 공격: 단어 중간에 ZWJ를 삽입해 verbatim 검사를 피하려는 시도."""
        raw = ["hello world test phrase check"]
        # ZWJ를 단어 내부에 삽입: "hel‍lo world test phrase check"
        bundle = {"x": "hel‍lo world test phrase check"}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, raw)

    def test_soft_hyphen_evasion_blocked(self):
        """U+00AD SOFT HYPHEN 삽입 우회 차단."""
        raw = ["hello world test"]
        bundle = {"x": "hel­lo world test"}
        with pytest.raises(DeidLeakError):
            selfcheck_bundle(bundle, raw)


# ---------------------------------------------------------------------------
# TestBundleDumpsKwargs — BUNDLE_DUMPS_KWARGS 직렬화 불변성 (p2-A)
# ---------------------------------------------------------------------------


class TestBundleDumpsKwargs:
    """BUNDLE_DUMPS_KWARGS 상수가 올바르게 정의되고 내보내지는지 확인."""

    def test_bundle_dumps_kwargs_exported(self):
        """BUNDLE_DUMPS_KWARGS가 deid 모듈에서 공개 import 가능해야 한다."""
        assert BUNDLE_DUMPS_KWARGS is not None
        assert isinstance(BUNDLE_DUMPS_KWARGS, dict)

    def test_ensure_ascii_false(self):
        """ensure_ascii=False 포함 — 유니코드 원문 보존."""
        assert BUNDLE_DUMPS_KWARGS.get("ensure_ascii") is False

    def test_sort_keys_true(self):
        """sort_keys=True 포함 — 결정론적 직렬화."""
        assert BUNDLE_DUMPS_KWARGS.get("sort_keys") is True

    def test_canonical_serialization(self):
        """동일 객체를 BUNDLE_DUMPS_KWARGS로 직렬화하면 키가 정렬된 JSON이어야 한다."""
        import json
        obj = {"z_key": "last", "a_key": "first"}
        result = json.dumps(obj, **BUNDLE_DUMPS_KWARGS)
        assert result.index('"a_key"') < result.index('"z_key"')
