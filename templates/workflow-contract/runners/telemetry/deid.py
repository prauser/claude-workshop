"""
deid.py — 비식별(de-identification) 런타임 게이트.

책임 범위:
  - scan_secrets: 정규식(regex) 기반 secret 탐지 (AWS/Slack/GitHub/PEM/Bearer/고엔트로피).
  - selfcheck_bundle: 업로드 직전 hard-fail 게이트.
    forbidden_raw 원문 + secret 적중 → DeidLeakError raise.
  - redact_for_audit: --dry-run 감사용 마스킹 (전부-또는-전무).

LLM 추상화는 이 모듈의 책임이 아니다. 추상화는 커맨드(wf-collect.md)가 담당하며
이 모듈은 그 결과를 검증(scan + self-check)하기만 한다.

외부 의존 0 — stdlib만 사용.
"""

from __future__ import annotations

import base64
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, NamedTuple


# ---------------------------------------------------------------------------
# 공개 예외(exception) 클래스
# ---------------------------------------------------------------------------


class DeidLeakError(Exception):
    """비식별 누출(de-id leak) 발견 시 hard-fail로 raise되는 예외."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


# ---------------------------------------------------------------------------
# Secret 탐지 — scan_secrets
# ---------------------------------------------------------------------------


class Secret(NamedTuple):
    """탐지된 secret 항목."""

    kind: str    # 탐지 규칙 이름 (예: "aws_access_key")
    match: str   # 탐지된 원본 문자열 (로그/감사용)
    start: int   # 원본 텍스트 내 시작 위치
    end: int     # 원본 텍스트 내 끝 위치


# 탐지 규칙 목록 — (kind, compiled_pattern)
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # AWS Access Key ID
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    # Slack 토큰(token) — xoxb, xoxa, xoxp, xoxr, xoxs
    ("slack_token", re.compile(r"xox[baprs]-[0-9A-Za-z\-]+")),
    # GitHub Personal Access Token / Fine-grained PAT
    ("github_token", re.compile(r"gh[pousr]_[0-9A-Za-z]{10,}")),
    # PEM 헤더
    ("pem_header", re.compile(r"-----BEGIN [A-Z ]{1,30}-----")),
    # Bearer 토큰(Authorization 헤더)
    ("bearer_token", re.compile(r"(?:Bearer\s+|Authorization:\s*Bearer\s+)[A-Za-z0-9\-_.~+/]+=*")),
    # Authorization: Basic / Token 계열
    ("auth_header", re.compile(r"Authorization:\s*(?:Basic|Token)\s+[A-Za-z0-9+/=]{8,}")),
    # password= / secret= 패턴 — 값이 6자 이상인 경우
    ("password_field", re.compile(r"(?:password|secret)\s*=\s*[^\s\"']{6,}", re.IGNORECASE)),
    # JWT — eyJ로 시작하는 3파트 구조 (header.payload.sig)
    ("jwt_token", re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
    # Google API Key
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    # npm automation token
    ("npm_token", re.compile(r"npm_[A-Za-z0-9]{36}")),
]

# 고엔트로피(high-entropy) 문자열 탐지용 임계값
_HIGH_ENTROPY_MIN_LEN = 32
_HIGH_ENTROPY_HEX_THRESHOLD = 3.8    # hex 32자 엔트로피
_HIGH_ENTROPY_B64_THRESHOLD = 4.5    # base64 32자 엔트로피

_HEX_PATTERN = re.compile(r"[0-9a-fA-F]{32,}")
_B64_PATTERN = re.compile(r"[A-Za-z0-9+/]{32,}={0,2}")


def _shannon_entropy(s: str) -> float:
    """섀넌(Shannon) 엔트로피 — 문자 빈도 기반 비트 수치."""
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    n = len(s)
    return -sum((cnt / n) * math.log2(cnt / n) for cnt in freq.values())


def _scan_high_entropy(text: str) -> list[Secret]:
    """고엔트로피 32+ hex/base64 스캔."""
    results: list[Secret] = []
    for m in _HEX_PATTERN.finditer(text):
        if _shannon_entropy(m.group()) >= _HIGH_ENTROPY_HEX_THRESHOLD:
            results.append(Secret("high_entropy_hex", m.group(), m.start(), m.end()))
    for m in _B64_PATTERN.finditer(text):
        # 이미 hex로 잡힌 구간은 skip
        val = m.group()
        if _shannon_entropy(val) >= _HIGH_ENTROPY_B64_THRESHOLD:
            results.append(Secret("high_entropy_b64", val, m.start(), m.end()))
    return results


def scan_secrets(text: str) -> list[Secret]:
    """정규식 기반 secret 탐지.

    text 안에서 AWS 키, Slack 토큰, GitHub PAT, PEM 헤더, Bearer/Authorization 토큰,
    고엔트로피 32+ hex/base64, password=/secret= 패턴을 스캔한다.

    Returns:
        탐지된 Secret 항목 리스트. 없으면 빈 리스트.
    """
    results: list[Secret] = []
    for kind, pattern in _SECRET_PATTERNS:
        for m in pattern.finditer(text):
            results.append(Secret(kind, m.group(), m.start(), m.end()))
    results.extend(_scan_high_entropy(text))
    return results


# ---------------------------------------------------------------------------
# 번들 직렬화 표준 kwargs (serialization invariant)
# ---------------------------------------------------------------------------

# T5(serialize_bundle)와 selfcheck_bundle이 동일 직렬화 바이트를 사용하도록
# 단일 canonical 상수로 관리한다. T5는 이 kwargs로 json.dumps를 호출해야 한다.
BUNDLE_DUMPS_KWARGS: dict = dict(ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# Self-check 결과 객체
# ---------------------------------------------------------------------------


@dataclass
class SelfCheckResult:
    """selfcheck_bundle 성공 시 반환되는 결과 객체."""

    ok: bool = True
    secret_count: int = 0         # 번들에서 발견된 secret 수 (통과 시 0)
    forbidden_hit_count: int = 0  # forbidden_raw 부분일치 수 (통과 시 0)


# ---------------------------------------------------------------------------
# 정규화 유틸리티 — NFKC + 공백·대소문자 폴딩
# ---------------------------------------------------------------------------

_WS_RE = re.compile(r"\s+")

# 제로폭(zero-width) 및 소프트 하이픈 문자 — verbatim 우회 방지용 제거 목록
# U+200B ZERO WIDTH SPACE, U+200C ZERO WIDTH NON-JOINER, U+200D ZERO WIDTH JOINER,
# U+FEFF ZERO WIDTH NO-BREAK SPACE (BOM), U+00AD SOFT HYPHEN
_ZERO_WIDTH_RE = re.compile(r"[​‌‍﻿­]")


def _normalize(s: str) -> str:
    """NFKC 유니코드(Unicode) 정규화 + 제로폭 문자 제거 + 공백 축약 + 소문자 변환."""
    normalized = unicodedata.normalize("NFKC", s)
    # 제로폭 문자 제거 — "hel​lo world" 형태의 verbatim 우회 방지
    no_zwc = _ZERO_WIDTH_RE.sub("", normalized)
    return _WS_RE.sub(" ", no_zwc).strip().lower()


# ---------------------------------------------------------------------------
# selfcheck_bundle — 업로드 직전 hard-fail 게이트
# ---------------------------------------------------------------------------

# 슬라이딩 윈도우(sliding-window) 최소 토큰 길이 (공백 기준 split 후 단어 수)
_WINDOW_MIN_TOKENS = 4


def _sliding_window_match(bundle_norm: str, raw_norm: str) -> bool:
    """슬라이딩 윈도우로 raw_norm의 부분 일치를 bundle_norm에서 탐색.

    raw_norm을 단어(word) 단위로 쪼개 _WINDOW_MIN_TOKENS 개 이상의 연속 윈도우가
    bundle_norm에 substring으로 존재하면 True를 반환한다.
    """
    words = raw_norm.split()
    if len(words) < _WINDOW_MIN_TOKENS:
        # 단어가 너무 적으면 단순 substring 검사로 처리
        return raw_norm in bundle_norm
    for start in range(len(words) - _WINDOW_MIN_TOKENS + 1):
        window = " ".join(words[start: start + _WINDOW_MIN_TOKENS])
        if window in bundle_norm:
            return True
    return False


def selfcheck_bundle(
    bundle_obj: object,
    forbidden_raw: list[str],
) -> SelfCheckResult:
    """업로드 직전 hard-fail 프라이버시 게이트(privacy gate).

    검사 항목:
      1. 직렬화된 번들 바이트에 forbidden_raw 원문이 substring 또는
         정규화(NFKC + 공백·대소문자 폴딩 + 슬라이딩 윈도우) 부분일치로 존재하면 FAIL.
      2. 직렬화된 번들 바이트에 scan_secrets 적중이 있으면 FAIL.

    Raises:
        DeidLeakError: 누출 탐지 시 hard-fail.

    Returns:
        SelfCheckResult: 통과 시 반환 (ok=True, secret_count=0, forbidden_hit_count=0).
    """
    bundle_json = json.dumps(bundle_obj, **BUNDLE_DUMPS_KWARGS)
    bundle_norm = _normalize(bundle_json)

    forbidden_hits: list[str] = []
    for raw in forbidden_raw:
        if not raw:
            continue
        # 단순 substring (원문 그대로)
        if raw in bundle_json:
            forbidden_hits.append(f"verbatim substring: {raw[:60]!r}")
            continue
        # 정규화 후 substring + 슬라이딩 윈도우
        raw_norm = _normalize(raw)
        if raw_norm and (raw_norm in bundle_norm or _sliding_window_match(bundle_norm, raw_norm)):
            forbidden_hits.append(f"normalized match: {raw[:60]!r}")

    secrets = scan_secrets(bundle_json)

    if forbidden_hits or secrets:
        parts: list[str] = []
        if forbidden_hits:
            parts.append("forbidden_raw 누출: " + "; ".join(forbidden_hits))
        if secrets:
            kinds = ", ".join(f"{s.kind}({s.match[:20]!r})" for s in secrets[:5])
            parts.append(f"secret 탐지({len(secrets)}건): " + kinds)
        raise DeidLeakError("; ".join(parts))

    return SelfCheckResult(ok=True, secret_count=0, forbidden_hit_count=0)


# ---------------------------------------------------------------------------
# redact_for_audit — --dry-run 감사용 전부-또는-전무 마스킹
# ---------------------------------------------------------------------------

_REDACT_PLACEHOLDER = "[REDACTED]"


def redact_for_audit(text: str) -> str:
    """--dry-run 감사(audit) 출력용 마스킹.

    전부-또는-전무(all-or-nothing) 정책: secret이 하나라도 탐지되면 전체 텍스트를
    [REDACTED]로 교체하고, 탐지된 항목 수를 함께 반환한다.
    탐지 없으면 원문을 반환한다 (verbatim absent 확인 목적으로만 사용).

    Returns:
        마스킹된 텍스트 (secret 없으면 원문 그대로).
    """
    secrets = scan_secrets(text)
    if secrets:
        kinds_summary = ", ".join(sorted({s.kind for s in secrets}))
        return f"{_REDACT_PLACEHOLDER} ({len(secrets)} secret(s): {kinds_summary})"
    return text
