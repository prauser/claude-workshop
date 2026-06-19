"""
harvest_sessions.py — 세션로그 메타 harvest + 이벤트 스트림 생성.

외부 의존 0 — stdlib만 사용. vendor/session_lean.py를 이용해 세션을 파싱하고
평문 이벤트 스트림(메타만)을 반환한다.

user 턴 텍스트 원문은 이벤트 스트림에 절대 포함하지 않는다.
raw_user_turns는 별도 반환값으로 로컬 전용이며, T4 비식별 처리 전 번들 직행 금지.
"""

from __future__ import annotations

import glob
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# sys.path 조정 — vendor 모듈 임포트를 위해 telemetry 디렉토리를 경로에 추가
# ---------------------------------------------------------------------------

def _ensure_vendor_path() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


_ensure_vendor_path()

from vendor.session_lean import (  # noqa: E402
    parse_session_lean,
    SessionLean,
    MessageLean,
    TokenUsageLean,
)


# ---------------------------------------------------------------------------
# A2 ticket 복원 — agentlens _extract_ticket 규칙 재사용
# ---------------------------------------------------------------------------

# /impl PRA-109, /spec-plan PRA-109, feat/PRA-109 등
_TICKET_RE = re.compile(
    r"(?:"
    r"(?:/impl|/spec-plan)\s+([A-Z][A-Z0-9]+-\d+)"   # /impl TICKET 또는 /spec-plan TICKET
    r"|"
    r"feat/([A-Z][A-Z0-9]+-\d+)"                        # feat/TICKET
    r")"
)


def _extract_ticket(text: str) -> Optional[str]:
    """user 턴 텍스트 또는 브랜치명에서 ticket ID를 추출.
    agentlens _extract_ticket 규칙 재사용.
    매치 실패 시 None 반환."""
    if not text:
        return None
    m = _TICKET_RE.search(text)
    if m:
        return m.group(1) or m.group(2)
    return None


# ---------------------------------------------------------------------------
# 이벤트 타입 정의
# Event = {
#   seq: int, ts: str,
#   type: "tool" | "user_turn" | "error" | "assistant",
#   # tool 이벤트 전용
#   tool_name: str | None,
#   path: str | None,
#   pattern_summary: str | None,
#   command_len: int | None,   # command 전체 아님 — 길이만
#   # error 이벤트 전용
#   error_class: str | None,
#   error_first_line: str | None,
#   # user_turn 이벤트 전용 (텍스트 내용 없음)
#   char_len: int | None,
#   token_count: int | None,
#   # tokens (assistant 이벤트 전용)
#   tokens: {in, out, cache_read, cache_creation} | None,
# }
# ---------------------------------------------------------------------------

Event = Dict[str, Any]


def _extract_path_from_input(tool_input: Dict[str, Any]) -> Optional[str]:
    """tool_input에서 경로 관련 인자 추출 — path/file_path/pattern 순."""
    for key in ("file_path", "path", "pattern", "glob"):
        val = tool_input.get(key)
        if val and isinstance(val, str):
            return val
    return None


def _extract_pattern_summary(tool_name: str, tool_input: Dict[str, Any]) -> Optional[str]:
    """tool_input에서 패턴/요약 정보 추출 — 전체 내용이 아닌 메타만."""
    # pattern 키가 있으면 우선
    if "pattern" in tool_input:
        return str(tool_input["pattern"])[:80]
    # command는 길이만 (전체 명령 금지)
    if "command" in tool_input:
        return None  # command_len 으로 처리
    return None


def _extract_error_info(content: Any) -> Tuple[Optional[str], Optional[str]]:
    """tool_result 내용에서 에러 클래스와 첫 줄 추출.

    de-id 경계 준수:
    - error_first_line은 개행 전까지 최대 80자로 제한한다.
    - 예외 클래스 토큰(e.g. FileNotFoundError, KeyError)이 존재하면
      error_first_line을 그 토큰으로만 대체해 사용자 입력 문자열 유출을 차단한다.
    - 파일 경로는 A4 / Intentional Exclusions 에 따라 평문 허용 — 별도 처리 없음.
    전체 내용(200자 이상 또는 멀티라인)은 포함하지 않는다."""
    if content is None:
        return None, None
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        # list of content blocks
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                break
    if not text:
        return None, None
    # 개행 전 첫 줄만, 80자 제한
    first_line = text.split("\n")[0][:80]
    # 에러 클래스 추출 시도 (e.g. "FileNotFoundError: ...")
    error_class: Optional[str] = None
    m = re.match(r"([A-Za-z][A-Za-z0-9_]*(?:Error|Exception|Warning|Fault))(?:\s*:|$)", first_line)
    if m:
        error_class = m.group(1)
        # 예외 클래스 토큰이 존재하면 error_first_line을 클래스 토큰으로만 제한 —
        # 콜론 뒤 사용자 공급 텍스트(NL arguments 등)를 제거해 유출 차단.
        error_first_line = error_class
    else:
        # 클래스 없으면 첫 줄 80자 그대로 (이미 개행·길이 제한됨)
        error_first_line = first_line
    return error_class, error_first_line


def build_event_stream(
    session_jsonl_path: str,
) -> Tuple[List[Event], List[str]]:
    """세션 jsonl 파일을 이벤트 스트림으로 변환.

    Returns:
        (events, raw_user_turns) 튜플.
        - events: 평문 이벤트 리스트. user_turn 이벤트에는 텍스트 내용이 없다.
        - raw_user_turns: user 턴 원문 텍스트 리스트(로컬 전용, T4 de-id 입력 — 번들 직행 금지).
    """
    session = parse_session_lean(session_jsonl_path)
    events: List[Event] = []
    raw_user_turns: List[str] = []
    seq = 0

    for msg in session.messages:
        ts_str = msg.timestamp.isoformat()

        if msg.type == "user" and not msg.is_tool_response:
            # user_turn 이벤트: 메타만 — 텍스트 원문 절대 미포함
            text = ""
            if isinstance(msg.content, str):
                text = msg.content
            elif isinstance(msg.content, list):
                # text 블록 내용 추출 (raw_user_turns용)
                parts: List[str] = []
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        parts.append(block)
                text = "\n".join(parts)

            raw_user_turns.append(text)
            token_count_approx = len(text.split()) if text else 0
            events.append({
                "seq": seq,
                "ts": ts_str,
                "type": "user_turn",
                "char_len": len(text),
                "token_count": token_count_approx,
                # 이하 필드 없음 — user 텍스트 내용 미포함
            })
            seq += 1

        elif msg.type == "assistant":
            # assistant 이벤트 (토큰 정보 포함)
            usage_dict: Optional[Dict[str, int]] = None
            if msg.usage:
                usage_dict = {
                    "in": msg.usage.input_tokens,
                    "out": msg.usage.output_tokens,
                    "cache_read": msg.usage.cache_read_tokens,
                    "cache_creation": msg.usage.cache_creation_tokens,
                }
            events.append({
                "seq": seq,
                "ts": ts_str,
                "type": "assistant",
                "tokens": usage_dict,
            })
            seq += 1

            # tool_use 이벤트 (페어에서 생성)
            for pair in msg.tool_pairs:
                tool_input = pair.tool_input or {}
                path_val = _extract_path_from_input(tool_input)
                pattern_val = _extract_pattern_summary(pair.tool_name, tool_input)
                command_len: Optional[int] = None
                if "command" in tool_input:
                    command_len = len(str(tool_input["command"]))

                if pair.is_error:
                    ec, el = _extract_error_info(pair.result_content)
                    events.append({
                        "seq": seq,
                        "ts": ts_str,
                        "type": "error",
                        "tool_name": pair.tool_name,
                        "path": path_val,
                        "error_class": ec,
                        "error_first_line": el,
                    })
                else:
                    events.append({
                        "seq": seq,
                        "ts": ts_str,
                        "type": "tool",
                        "tool_name": pair.tool_name,
                        "path": path_val,
                        "pattern_summary": pattern_val,
                        "command_len": command_len,
                    })
                seq += 1

    return events, raw_user_turns


# ---------------------------------------------------------------------------
# A2 correlation: ticket 복원
# ---------------------------------------------------------------------------

def _correlate_session(
    session_jsonl_path: str,
    session_dir: str,
) -> Tuple[Optional[str], List[Event], List[str], List[Dict]]:
    """단일 세션에서 ticket 복원 + 이벤트 스트림 빌드.

    Returns:
        (ticket, events, raw_user_turns, parse_errors) 튜플.
    """
    session = parse_session_lean(session_jsonl_path)
    events, raw_user_turns = build_event_stream(session_jsonl_path)

    # ticket 복원: 첫 번째 user 턴 텍스트에서 추출
    ticket: Optional[str] = None
    for msg in session.messages:
        if msg.type == "user" and not msg.is_tool_response:
            text = ""
            if isinstance(msg.content, str):
                text = msg.content
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text += block.get("text", "")
                    elif isinstance(block, str):
                        text += block
            ticket = _extract_ticket(text)
            if ticket:
                break

    # gitBranch 에서도 ticket 추출 시도 (ticket 미발견 시)
    if not ticket:
        try:
            with open(session_jsonl_path, encoding="utf-8") as f:
                import json as _json
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = _json.loads(line)
                        branch = d.get("gitBranch", "")
                        if branch:
                            t = _extract_ticket(branch)
                            if t:
                                ticket = t
                                break
                    except Exception:
                        continue
        except OSError:
            pass

    parse_errors = [
        {"line_no": e.line_no, "raw": e.raw, "reason": e.reason}
        for e in session.parse_errors
    ]

    return ticket, events, raw_user_turns, parse_errors


def correlate(
    corpus: Any,
    event_streams: Optional[Dict[str, List[Event]]] = None,
) -> Dict[str, Any]:
    """A2 join=ticket: corpus(RepoCorpus)의 세션을 ticket으로 그룹화.

    Returns:
        {
          by_ticket: {ticket: [{session_id, events, parse_errors}]},
          ticketless: [{session_id, parse_errors}],
          parse_errors: [전체 parse error 레코드],
        }
    """
    by_ticket: Dict[str, List[Dict]] = {}
    ticketless: List[Dict] = []
    all_parse_errors: List[Dict] = []

    session_dir = getattr(corpus, "session_dir", None)
    if not session_dir or not os.path.isdir(session_dir):
        return {
            "by_ticket": by_ticket,
            "ticketless": ticketless,
            "parse_errors": all_parse_errors,
        }

    jsonl_paths = sorted(glob.glob(os.path.join(session_dir, "*.jsonl")))

    for jsonl_path in jsonl_paths:
        session_id = os.path.splitext(os.path.basename(jsonl_path))[0]
        ticket, events, _raw, parse_errors = _correlate_session(jsonl_path, session_dir)

        if parse_errors:
            for pe in parse_errors:
                pe["session_id"] = session_id
                all_parse_errors.append(pe)

        record = {
            "session_id": session_id,
            "event_count": len(events),
            "parse_errors": parse_errors,
        }

        if ticket:
            if ticket not in by_ticket:
                by_ticket[ticket] = []
            by_ticket[ticket].append(record)
        else:
            ticketless.append(record)

    return {
        "by_ticket": by_ticket,
        "ticketless": ticketless,
        "parse_errors": all_parse_errors,
    }


def harvest_sessions_for_repo(corpus: Any) -> Dict[str, Any]:
    """단일 RepoCorpus에서 세션 harvest 수행.
    T2 harvest_artifacts와 동일한 반환 형태:
    {by_ticket, ticketless, parse_errors}."""
    return correlate(corpus)
