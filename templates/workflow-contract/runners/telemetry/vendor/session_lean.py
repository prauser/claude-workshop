# vendored from agentlens/src/agentlens/parsers/session.py @ dc80c9d
# Dependency-light snapshot: stdlib only, no agentlens/pydantic import.
# Preserves parity rules: timestamp parsing fallback, token key mapping
# (cache_creation_input_tokens), and tool_use<->tool_result pairing logic.
"""
vendor/session_lean.py — agentlens session 파서의 stdlib-only lean snapshot.
외부 의존 0 — pydantic/agentlens 임포트 없음. dataclass + stdlib만 사용.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Lean 데이터 모델 — agentlens models.py의 경량화(lightweight) 버전
# ---------------------------------------------------------------------------

@dataclass
class TokenUsageLean:
    """토큰 사용량 집계 — 4종 카운터."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    def __add__(self, other: "TokenUsageLean") -> "TokenUsageLean":
        return TokenUsageLean(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_tokens=self.cache_creation_tokens + other.cache_creation_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
        )

    def total(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )


@dataclass
class ToolCallPairLean:
    """tool_use + tool_result 페어."""
    tool_use_id: str
    tool_name: str
    tool_input: Dict[str, Any]
    result_content: Any = None
    is_error: bool = False


@dataclass
class MessageLean:
    """세션 jsonl 한 줄 — user/assistant/system."""
    type: str                        # "user" | "assistant" | "system"
    content: Any                     # str | list
    timestamp: datetime
    usage: Optional[TokenUsageLean] = None
    model: Optional[str] = None
    cwd: Optional[str] = None
    is_tool_response: bool = False
    tool_pairs: List[ToolCallPairLean] = field(default_factory=list)
    is_meta: bool = False            # isMeta=True → 시스템 주입 컨텍스트 (CLAUDE.md 등) — human NL 아님
    user_type: Optional[str] = None  # userType 필드 (예: "external", "internal")


@dataclass
class ParseErrorLean:
    """jsonl 파싱 실패 레코드."""
    line_no: int
    raw: str
    reason: str


@dataclass
class SessionLean:
    """parse_session_lean 반환값."""
    session_id: str
    messages: List[MessageLean] = field(default_factory=list)
    total_tokens: TokenUsageLean = field(default_factory=TokenUsageLean)
    parse_errors: List[ParseErrorLean] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 내부 헬퍼 — agentlens session.py parity
# ---------------------------------------------------------------------------

def _parse_timestamp(ts_str: Optional[str]) -> datetime:
    """ISO 8601 타임스탬프 파싱 — 실패 시 epoch(UTC) 반환 (parity: fallback)."""
    if not ts_str:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return datetime.fromtimestamp(0, tz=timezone.utc)


def _parse_token_usage(usage_dict: Optional[Dict]) -> TokenUsageLean:
    """assistant message.usage dict → TokenUsageLean.
    parity: cache_creation_input_tokens 키 매핑 보존."""
    if not usage_dict:
        return TokenUsageLean()
    return TokenUsageLean(
        input_tokens=usage_dict.get("input_tokens", 0),
        output_tokens=usage_dict.get("output_tokens", 0),
        cache_creation_tokens=usage_dict.get("cache_creation_input_tokens", 0),
        cache_read_tokens=usage_dict.get("cache_read_input_tokens", 0),
    )


def _parse_message_entry(entry: Dict) -> Optional[MessageLean]:
    """raw jsonl entry dict → MessageLean.
    user/assistant/system만 처리 — 나머지는 None 반환."""
    msg_type = entry.get("type")
    if msg_type not in ("user", "assistant", "system"):
        return None

    timestamp = _parse_timestamp(entry.get("timestamp"))
    cwd: Optional[str] = entry.get("cwd")
    usage: Optional[TokenUsageLean] = None
    model: Optional[str] = None

    # isMeta=True → CLAUDE.md / 커맨드 정의 등 시스템 주입 컨텍스트 (human NL 아님)
    is_meta: bool = bool(entry.get("isMeta", False))
    user_type: Optional[str] = entry.get("userType")

    if msg_type == "assistant":
        msg_inner = entry.get("message", {})
        model = msg_inner.get("model")
        usage = _parse_token_usage(msg_inner.get("usage"))
        content = msg_inner.get("content", "")
    elif msg_type == "user":
        msg_inner = entry.get("message", {})
        content = msg_inner.get("content", "")
    else:
        content = entry.get("content", "")

    return MessageLean(
        type=msg_type,
        content=content,
        timestamp=timestamp,
        usage=usage,
        model=model,
        cwd=cwd,
        is_meta=is_meta,
        user_type=user_type,
    )


def _pair_tool_calls(messages: List[MessageLean]) -> None:
    """tool_use ↔ tool_result 페어링 — agentlens _pair_tool_calls parity.
    assistant 메시지의 tool_use 블록과 이어지는 user 메시지의 tool_result를 매핑.
    메시지를 in-place로 변경한다."""
    for idx, msg in enumerate(messages):
        if msg.type != "assistant":
            continue
        if not isinstance(msg.content, list):
            continue

        # tool_use 블록 수집
        tool_use_map: Dict[str, Tuple[str, Dict]] = {}
        for block in msg.content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                tid = block.get("id", "")
                name = block.get("name", "")
                inp = block.get("input", {})
                tool_use_map[tid] = (name, inp)

        if not tool_use_map:
            continue

        # 다음 user 메시지에서 tool_result 수집
        result_map: Dict[str, Tuple[Any, bool]] = {}
        for scan_idx in range(idx + 1, len(messages)):
            scan_msg = messages[scan_idx]
            if scan_msg.type == "assistant":
                break
            if scan_msg.type != "user":
                continue
            if not isinstance(scan_msg.content, list):
                break
            has_non_tool_result = False
            for block in scan_msg.content:
                if not isinstance(block, dict):
                    has_non_tool_result = True
                    continue
                if block.get("type") == "tool_result":
                    tid = block.get("tool_use_id", "")
                    raw_content = block.get("content")
                    is_error = bool(block.get("is_error", False))
                    result_map[tid] = (raw_content, is_error)
                else:
                    has_non_tool_result = True
            if not has_non_tool_result:
                scan_msg.is_tool_response = True
            break

        # ToolCallPairLean 구성
        pairs: List[ToolCallPairLean] = []
        for tid, (name, inp) in tool_use_map.items():
            if tid in result_map:
                rc, ie = result_map[tid]
                pairs.append(ToolCallPairLean(
                    tool_use_id=tid,
                    tool_name=name,
                    tool_input=inp,
                    result_content=rc,
                    is_error=ie,
                ))
            else:
                pairs.append(ToolCallPairLean(
                    tool_use_id=tid,
                    tool_name=name,
                    tool_input=inp,
                    result_content=None,
                    is_error=False,
                ))
        msg.tool_pairs = pairs


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def parse_session_lean(session_path: str) -> SessionLean:
    """세션 jsonl 파일 → SessionLean.

    Args:
        session_path: .jsonl 세션 파일 경로.

    Returns:
        SessionLean — messages 리스트 + 토큰 집계 + parse_errors.
    """
    import os
    path = os.path.expanduser(session_path)
    session_id = os.path.splitext(os.path.basename(path))[0]

    messages: List[MessageLean] = []
    total_tokens = TokenUsageLean()
    parse_errors: List[ParseErrorLean] = []

    try:
        with open(path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    parse_errors.append(ParseErrorLean(
                        line_no=line_no,
                        raw=line[:200],
                        reason=str(exc),
                    ))
                    continue

                msg = _parse_message_entry(entry)
                if msg is None:
                    continue
                messages.append(msg)
                if msg.usage:
                    total_tokens = total_tokens + msg.usage

    except OSError as exc:
        parse_errors.append(ParseErrorLean(
            line_no=0,
            raw="",
            reason=f"OSError: {exc}",
        ))

    _pair_tool_calls(messages)

    return SessionLean(
        session_id=session_id,
        messages=messages,
        total_tokens=total_tokens,
        parse_errors=parse_errors,
    )


def collect_tool_names(session: SessionLean) -> set:
    """세션 내 모든 tool 이름 집합 반환 — parity 검증용."""
    names: set = set()
    for msg in session.messages:
        for pair in msg.tool_pairs:
            names.add(pair.tool_name)
    return names


def total_event_count(session: SessionLean) -> int:
    """tool_use 이벤트 총 수 (ToolCallPair 수 합) — parity 검증용."""
    count = 0
    for msg in session.messages:
        count += len(msg.tool_pairs)
    return count
