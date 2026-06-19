"""
harvest_artifacts.py — 산출물 frontmatter harvest (드리프트 내성)
T2: plan/task/result/manifest frontmatter를 수집해 구조 메트릭을 반환한다.

외부 의존 0 — stdlib만 사용.
PyYAML / pydantic / requests 등 써선 안 된다(P0-1).

비식별(de-identification) 경계:
  이 모듈은 구조 메트릭만 수확한다. user_prompt verbatim / 세션 유저 턴 raw 텍스트를
  출력 번들에 포함하지 않는다. de-id 게이트는 T4에서 처리한다.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 경로 설정 — collect.py가 discover를 임포트하는 것과 동일한 방식
# ---------------------------------------------------------------------------

def _ensure_sys_path() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


_ensure_sys_path()

try:
    from discover import RepoCorpus  # type: ignore
except ImportError:
    RepoCorpus = None  # type: ignore


# ---------------------------------------------------------------------------
# 방어적 YAML frontmatter 파서 (P1-1, P1-3)
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """
    `---` 펜스로 둘러싼 첫 YAML 블록을 파싱해 (dict, body) 쌍으로 반환한다.

    - 펜스 없음 → ({}, text) 반환 (무crash).
    - YAML 파싱 오류 → {_parse_error: {error_class, msg}} 반환 (무crash).
    - 이 파서는 실코퍼스가 쓰는 YAML 부분집합(키:값, 리스트, `|` 블록 스칼라,
      `{...}` 인라인 매핑, 다중행 scalar)을 처리한다.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ({}, text)

    # 두 번째 "---" 펜스를 찾는다
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return ({}, text)

    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1:])

    try:
        result = _parse_yaml_subset("\n".join(fm_lines))
        return (result, body)
    except Exception as exc:  # noqa: BLE001
        return (
            {
                "_parse_error": {
                    "error_class": type(exc).__name__,
                    "msg": str(exc),
                }
            },
            body,
        )


# ---------------------------------------------------------------------------
# 내부 YAML 부분집합 파서
# ---------------------------------------------------------------------------

def _parse_yaml_subset(yaml_text: str) -> Dict[str, Any]:
    """
    실코퍼스 frontmatter에서 쓰이는 YAML 부분집합을 파싱한다.

    지원:
      - 단순 키: 값 (스칼라)
      - `|` 블록 스칼라 (literal block scalar)
      - 리스트 항목 (`- ...`)
      - 인라인 매핑 `{key: val, ...}`
      - 중첩 매핑 (들여쓰기)
      - 다중줄 문자열 (후행 공백 trim)
    """
    lines = yaml_text.splitlines()
    result, _ = _parse_block(lines, 0, 0)
    return result


def _get_indent(line: str) -> int:
    """줄의 들여쓰기(indentation) 칸 수를 반환한다."""
    return len(line) - len(line.lstrip(" "))


def _parse_block(
    lines: List[str], start: int, base_indent: int
) -> Tuple[Dict[str, Any], int]:
    """
    start 줄부터 base_indent보다 큰 들여쓰기를 가진 블록을 파싱한다.
    (dict, 다음 시작 인덱스) 쌍을 반환한다.
    """
    result: Dict[str, Any] = {}
    i = start

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()

        # 빈 줄 또는 주석은 건너뛴다
        if not stripped or stripped.lstrip().startswith("#"):
            i += 1
            continue

        indent = _get_indent(stripped)

        # 현재 블록 들여쓰기보다 낮아졌으면 블록 종료
        if indent < base_indent:
            break

        # 리스트 항목은 상위 호출(caller)에서 처리해야 하지만, 최상위 레벨에서
        # 리스트 항목으로 시작하면 잘못된 상태 → 빈 dict 반환
        content = stripped.lstrip()
        if content.startswith("- ") or content == "-":
            # 최상위에서 리스트 항목이 나오면 잘못된 구조 — 상위로 넘긴다
            break

        # 키: 값 패턴
        colon_idx = content.find(":")
        if colon_idx < 0:
            # 키 없는 줄 — 다중행 scalar 연속일 수 있으니 건너뜀
            i += 1
            continue

        key = content[:colon_idx].strip()
        rest = content[colon_idx + 1:]

        # 블록 스칼라 (`|` 또는 `>`)
        if rest.strip() in ("|", "|2", ">", ">-", "|-"):
            block_indent = indent + 2
            i += 1
            block_lines = []
            while i < len(lines):
                bl = lines[i]
                bl_stripped = bl.rstrip()
                if not bl_stripped:
                    block_lines.append("")
                    i += 1
                    continue
                bl_indent = _get_indent(bl_stripped)
                if bl_indent < block_indent:
                    break
                block_lines.append(bl[block_indent:].rstrip())
                i += 1
            # 후행 빈 줄 제거 후 개행 결합
            while block_lines and block_lines[-1] == "":
                block_lines.pop()
            result[key] = "\n".join(block_lines)
            continue

        rest_stripped = rest.strip()

        # 다음 줄이 더 깊은 들여쓰기 → 중첩 매핑 또는 리스트
        if not rest_stripped:
            # 다음 실제 줄을 확인
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines):
                result[key] = None
                i += 1
                continue
            next_content = lines[j].lstrip()
            next_indent = _get_indent(lines[j])
            if next_indent > indent and (
                next_content.startswith("- ") or next_content == "-"
            ):
                # 리스트 파싱
                val, i = _parse_list(lines, j, next_indent)
                result[key] = val
                continue
            elif next_indent > indent:
                # 중첩 매핑 파싱
                val, i = _parse_block(lines, j, next_indent)
                result[key] = val
                continue
            else:
                result[key] = None
                i += 1
                continue

        # 인라인 매핑 `{...}`
        if rest_stripped.startswith("{"):
            result[key] = _parse_inline_mapping(rest_stripped)
            i += 1
            continue

        # 인라인 리스트 `[...]`
        if rest_stripped.startswith("["):
            result[key] = _parse_inline_list(rest_stripped)
            i += 1
            continue

        # 단순 스칼라
        result[key] = _parse_scalar(rest_stripped)
        i += 1

    return result, i


def _parse_list(
    lines: List[str], start: int, base_indent: int
) -> Tuple[List[Any], int]:
    """리스트 항목(`- ...`)을 파싱해 (list, 다음 인덱스) 반환."""
    result: List[Any] = []
    i = start

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()
        if not stripped:
            i += 1
            continue
        indent = _get_indent(stripped)
        if indent < base_indent:
            break
        content = stripped.lstrip()
        if not (content.startswith("- ") or content == "-"):
            break

        item_text = content[2:].strip() if content.startswith("- ") else ""

        # 인라인 매핑 `{...}`
        if item_text.startswith("{"):
            result.append(_parse_inline_mapping(item_text))
            i += 1
            continue

        # 빈 항목이거나 다음 줄이 더 깊게 들여쓰인 경우 → 중첩 블록
        if not item_text:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and _get_indent(lines[j].rstrip()) > indent:
                sub, i = _parse_block(lines, j, _get_indent(lines[j].rstrip()))
                result.append(sub)
                continue
            result.append(None)
            i += 1
            continue

        # `- key: val` 형식의 인라인 매핑 — 이후 줄이 더 깊이 들여쓰여 추가 키가 있을 수 있다
        # 예: `  - flag: foo\n    detail: bar`
        if ":" in item_text:
            # 첫 줄을 초기 dict로 파싱
            item_indent = indent + 2  # "- " 다음의 콘텐츠 들여쓰기
            # 다음 줄 확인: 현재 줄보다 깊게 들여쓰여 있으면 연속 매핑 항목
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines):
                next_stripped = lines[j].rstrip()
                next_indent = _get_indent(next_stripped)
                next_content = next_stripped.lstrip()
                # 다음 줄이 더 깊거나 같은 들여쓰기이고 "- "로 시작하지 않으면
                # 현재 리스트 항목의 연속 키-값 쌍
                if (
                    next_indent > indent
                    and not (next_content.startswith("- ") or next_content == "-")
                ):
                    # 현재 줄의 item_text를 가상의 첫 키-값으로 만들어 블록 파싱
                    # 방식: 현재 줄부터 같은 블록에 속하는 줄까지를 임시 블록으로 구성
                    sub_lines = [" " * item_indent + item_text]
                    k = j
                    while k < len(lines):
                        kl = lines[k].rstrip()
                        if not kl:
                            k += 1
                            continue
                        ki = _get_indent(kl)
                        kc = kl.lstrip()
                        # 현재 리스트 항목보다 들여쓰기가 낮아지거나 새 리스트 항목이면 종료
                        if ki <= indent:
                            break
                        if ki == indent and (kc.startswith("- ") or kc == "-"):
                            break
                        sub_lines.append(kl)
                        k += 1
                    sub, _ = _parse_block(sub_lines, 0, item_indent)
                    result.append(sub)
                    i = k
                    continue

        result.append(_parse_scalar(item_text))
        i += 1

    return result, i


def _parse_inline_mapping(text: str) -> Dict[str, Any]:
    """
    `{key: val, key2: val2}` 형식의 인라인 매핑을 파싱한다.
    nested brace를 지원하지 않는 단순 구현 — 실코퍼스 gate_events 형식에 충분하다.
    """
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    result: Dict[str, Any] = {}
    # 쉼표로 분리 (단, 따옴표 내 쉼표는 무시)
    parts = _split_inline(text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        colon_idx = part.find(":")
        if colon_idx < 0:
            continue
        k = part[:colon_idx].strip()
        v = part[colon_idx + 1:].strip()
        result[k] = _parse_scalar(v)
    return result


def _parse_inline_list(text: str) -> List[Any]:
    """
    `[val1, val2, ...]` 형식의 인라인 리스트를 파싱한다.
    """
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if not text.strip():
        return []
    parts = _split_inline(text)
    return [_parse_scalar(p.strip()) for p in parts if p.strip()]


def _split_inline(text: str) -> List[str]:
    """
    쉼표로 분리하되 따옴표 내 쉼표는 무시한다.
    """
    parts = []
    current = []
    in_quote = False
    quote_char = ""
    for ch in text:
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
            current.append(ch)
        elif in_quote and ch == quote_char:
            in_quote = False
            current.append(ch)
        elif ch == "," and not in_quote:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def _parse_scalar(text: str) -> Any:
    """
    YAML 스칼라 값을 Python 기본형으로 변환한다.
    bool, int, float, null, 따옴표 문자열, 날짜 형식 포함.
    """
    text = text.strip()
    if not text:
        return None
    # null
    if text in ("null", "~", "Null", "NULL"):
        return None
    # bool
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    # 따옴표 문자열
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]
    # 정수
    try:
        return int(text)
    except ValueError:
        pass
    # 부동소수점
    try:
        return float(text)
    except ValueError:
        pass
    # 그 외 → 문자열 그대로
    return text


# ---------------------------------------------------------------------------
# plan.md user_prompt 추출 (비식별 로컬 전용)
# ---------------------------------------------------------------------------

def get_plan_user_prompt(plan_path: str) -> Optional[str]:
    """plan.md frontmatter에서 user_prompt 원문을 반환한다.

    이 함수의 반환값은 로컬 전용이다 — 번들에 직렬화하지 않는다.
    T4 비식별 게이트의 forbidden_raw 조립에만 사용한다.

    Returns:
        user_prompt 원문 문자열, 없거나 파싱 실패 시 None.
    """
    try:
        text = _read_file(plan_path)
    except OSError:
        return None

    fm, _ = parse_frontmatter(text)
    if "_parse_error" in fm:
        return None

    val = fm.get("user_prompt")
    if not val:
        return None
    return str(val)


# ---------------------------------------------------------------------------
# plan.md harvest
# ---------------------------------------------------------------------------

def _harvest_plan_from_path(plan_path: str) -> Dict[str, Any]:
    """
    단일 plan.md 파일 경로로부터 구조 메트릭 dict를 반환한다.
    harvest_plan / harvest_plans_from_dir 의 공통 구현.

    비식별 경계: intent.problem은 AI 생성 필드이므로 평문 OK.
    user_prompt verbatim은 이 함수에서 수집하지 않는다.
    """
    try:
        text = _read_file(plan_path)
    except OSError as exc:
        return {
            "_parse_errors": [
                {"path": plan_path, "error_class": type(exc).__name__, "msg": str(exc)}
            ]
        }

    fm, _ = parse_frontmatter(text)

    if "_parse_error" in fm:
        return {
            "_parse_errors": [
                {
                    "path": plan_path,
                    "error_class": fm["_parse_error"].get("error_class", "ParseError"),
                    "msg": fm["_parse_error"].get("msg", ""),
                }
            ]
        }

    # legacy skip_grill_count 정규화 (P1-1)
    skip_presearch, skip_gate2 = _normalize_skip_counts(fm)

    # intent 필드 추출 — user_prompt는 수집하지 않는다 (비식별 경계)
    intent_raw = fm.get("intent") or {}
    if isinstance(intent_raw, str):
        intent_raw = {}
    intent = {
        "problem": intent_raw.get("problem"),
        "approach": intent_raw.get("approach"),
        "why": intent_raw.get("why"),
        "prd_ref": intent_raw.get("prd_ref"),
    }

    gate_events = fm.get("gate_events") or []
    if not isinstance(gate_events, list):
        gate_events = []

    readiness_flags = fm.get("readiness_flags") or []
    if not isinstance(readiness_flags, list):
        readiness_flags = []

    risk_acks = fm.get("risk_acks") or []
    if not isinstance(risk_acks, list):
        risk_acks = []

    intent_history = fm.get("intent_history") or []
    intent_history_len = len(intent_history) if isinstance(intent_history, list) else 0

    ticket = fm.get("ticket")

    # plan_sha — git hash-object로 working tree blob 해시 계산
    plan_sha = _git_hash_object(plan_path)

    return {
        "ticket": ticket,
        "plan_path": plan_path,
        "intent": intent,
        "gate_events": gate_events,
        "skip_presearch": skip_presearch,
        "skip_gate2": skip_gate2,
        "readiness_flags": readiness_flags,
        "risk_acks": risk_acks,
        "intent_history_len": intent_history_len,
        "plan_sha": plan_sha,
    }


def harvest_plans_from_dir(plans_dir: str) -> List[Dict[str, Any]]:
    """
    plans_dir 아래 모든 plan.md를 수집해 레코드 목록을 반환한다 (p2 fix).

    탐색 순서:
      1. plans_dir/plan.md 가 직계에 있으면 단독 레코드로 반환 (single-plan/legacy).
      2. plans_dir/{TICKET}/plan.md 형식의 모든 ticket 서브디렉토리를 정렬 후 수집.
         → 실코퍼스: LOCAL-20260503-225201, PRA-66, PRA-109, WORKFLOW-GLOSSARY-P2 등.
    """
    if not plans_dir or not os.path.isdir(plans_dir):
        return []

    records: List[Dict[str, Any]] = []

    # 1. 직계 plan.md (single-plan / legacy 경로)
    direct = os.path.join(plans_dir, "plan.md")
    if os.path.isfile(direct):
        records.append(_harvest_plan_from_path(direct))
        return records

    # 2. 모든 ticket 서브디렉토리의 plan.md
    try:
        entries = sorted(os.listdir(plans_dir))
    except OSError:
        return []

    for entry in entries:
        candidate = os.path.join(plans_dir, entry, "plan.md")
        if os.path.isfile(candidate):
            records.append(_harvest_plan_from_path(candidate))

    return records


def harvest_plan(plans_dir: str) -> Optional[Dict[str, Any]]:
    """
    plans_dir 아래 plan.md를 찾아 단일 구조 메트릭을 반환한다 (하위 호환 API).

    NOTE: plans_dir이 여러 ticket 서브디렉토리를 포함하는 컨테이너인 경우
    첫 번째 plan만 반환한다. 모든 plan을 수집하려면
    harvest_plans_from_dir()을 사용한다.

    반환 키:
      ticket, intent (problem/approach/why/prd_ref), gate_events,
      skip_presearch, skip_gate2, readiness_flags, risk_acks,
      intent_history_len, plan_sha, _parse_error(있으면)
    """
    records = harvest_plans_from_dir(plans_dir)
    if not records:
        return None
    return records[0]


def _normalize_skip_counts(fm: Dict[str, Any]) -> Tuple[int, int]:
    """
    skip_presearch / skip_gate2 를 추출한다.
    legacy skip_grill_count는 skip_presearch와 skip_gate2 키가 모두 없을 때만
    skip_presearch로 복사한다(key-presence guard, P1-1).
    """
    # 현행 필드
    skip_presearch = fm.get("skip_presearch", 0)
    skip_gate2 = fm.get("skip_gate2", 0)

    # legacy 정규화 (P1-1) — key-presence guard: 현행 키가 없을 때만 적용
    legacy = fm.get("skip_grill_count")
    if legacy is not None and "skip_presearch" not in fm and "skip_gate2" not in fm:
        try:
            skip_presearch = int(legacy)
        except (TypeError, ValueError):
            skip_presearch = 0
        skip_gate2 = 0

    try:
        skip_presearch = int(skip_presearch) if skip_presearch is not None else 0
    except (TypeError, ValueError):
        skip_presearch = 0

    try:
        skip_gate2 = int(skip_gate2) if skip_gate2 is not None else 0
    except (TypeError, ValueError):
        skip_gate2 = 0

    return skip_presearch, skip_gate2


# ---------------------------------------------------------------------------
# tasks harvest
# ---------------------------------------------------------------------------

def harvest_tasks(tasks_dirs: List[str]) -> List[Dict[str, Any]]:
    """
    done/pending/failed 디렉토리의 task·result 파일 frontmatter를 수집한다.

    반환 항목 키:
      task_id, status, role, plan_deviations_count, risk_acks,
      round_count, path, _parse_errors(있으면)
    """
    records: List[Dict[str, Any]] = []

    for tasks_dir in tasks_dirs:
        if not os.path.isdir(tasks_dir):
            continue
        try:
            entries = sorted(os.listdir(tasks_dir))
        except OSError:
            continue

        for fname in entries:
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(tasks_dir, fname)
            try:
                text = _read_file(fpath)
            except OSError as exc:
                records.append(
                    {
                        "path": fpath,
                        "_parse_errors": [
                            {
                                "path": fpath,
                                "error_class": type(exc).__name__,
                                "msg": str(exc),
                            }
                        ],
                    }
                )
                continue

            fm, body = parse_frontmatter(text)

            if "_parse_error" in fm:
                records.append(
                    {
                        "path": fpath,
                        "_parse_errors": [
                            {
                                "path": fpath,
                                "error_class": fm["_parse_error"].get(
                                    "error_class", "ParseError"
                                ),
                                "msg": fm["_parse_error"].get("msg", ""),
                            }
                        ],
                    }
                )
                continue

            # plan_deviations 개수
            plan_devs = fm.get("plan_deviations") or []
            if isinstance(plan_devs, list):
                plan_deviations_count = len(plan_devs)
            else:
                plan_deviations_count = 0

            # risk_acks
            risk_acks = fm.get("risk_acks") or []
            if not isinstance(risk_acks, list):
                risk_acks = []

            # 라운드 수 — body에서 "Round N" 패턴 카운트
            round_count = _count_rounds(body)

            records.append(
                {
                    "path": fpath,
                    "task_id": fm.get("task") or fm.get("task_id"),
                    "ticket": fm.get("ticket"),
                    "status": fm.get("status"),
                    "role": fm.get("role"),
                    "plan_deviations_count": plan_deviations_count,
                    "risk_acks": risk_acks,
                    "round_count": round_count,
                }
            )

    return records


def _count_rounds(body: str) -> int:
    """
    result body에서 "Round N" 또는 "Round N/M" 패턴을 세어 라운드 횟수를 반환한다.
    """
    matches = re.findall(r"##\s+Round\s+(\d+)", body, re.IGNORECASE)
    if not matches:
        return 1
    return max(int(m) for m in matches)


# ---------------------------------------------------------------------------
# manifest harvest
# ---------------------------------------------------------------------------

def harvest_manifest(runs_dir: str) -> Optional[Dict[str, Any]]:
    """
    runs_dir 아래 모든 manifest.yaml을 찾아 구조 메트릭을 반환한다.
    단일 manifest가 있으면 그 레코드를, 없으면 None을 반환한다.
    """
    if not runs_dir or not os.path.isdir(runs_dir):
        return None

    manifests = []
    try:
        entries = sorted(os.listdir(runs_dir))
    except OSError:
        return None

    # 직계 하위에 manifest.yaml 또는 하위 티켓 디렉토리 안에 manifest.yaml 탐색
    for fname in entries:
        fpath = os.path.join(runs_dir, fname)
        if fname == "manifest.yaml" and os.path.isfile(fpath):
            rec = _parse_manifest_file(fpath)
            if rec:
                manifests.append(rec)
        elif os.path.isdir(fpath):
            mpath = os.path.join(fpath, "manifest.yaml")
            if os.path.isfile(mpath):
                rec = _parse_manifest_file(mpath)
                if rec:
                    manifests.append(rec)

    if not manifests:
        return None
    if len(manifests) == 1:
        return manifests[0]
    return {"manifests": manifests}


def _parse_manifest_file(path: str) -> Optional[Dict[str, Any]]:
    """단일 manifest.yaml 파일을 파싱해 구조 메트릭 dict를 반환한다."""
    try:
        text = _read_file(path)
    except OSError as exc:
        return {
            "_parse_errors": [
                {"path": path, "error_class": type(exc).__name__, "msg": str(exc)}
            ]
        }

    # manifest.yaml은 --- 펜스가 있을 수도 없을 수도 있다
    # 펜스 없는 plain YAML도 시도한다
    if text.strip().startswith("---"):
        fm, _ = parse_frontmatter(text)
    else:
        try:
            fm = _parse_yaml_subset(text)
        except Exception as exc:  # noqa: BLE001
            fm = {
                "_parse_error": {
                    "error_class": type(exc).__name__,
                    "msg": str(exc),
                }
            }

    if "_parse_error" in fm:
        return {
            "_parse_errors": [
                {
                    "path": path,
                    "error_class": fm["_parse_error"].get("error_class", "ParseError"),
                    "msg": fm["_parse_error"].get("msg", ""),
                }
            ]
        }

    status = fm.get("status")
    quality_gates = fm.get("quality_gates") or []
    if not isinstance(quality_gates, list):
        quality_gates = []

    workflow_runs = fm.get("workflow_runs") or []
    if not isinstance(workflow_runs, list):
        workflow_runs = []

    ticket = fm.get("ticket")

    return {
        "path": path,
        "ticket": ticket,
        "status": status,
        "quality_gates": quality_gates,
        "workflow_runs": workflow_runs,
    }


# ---------------------------------------------------------------------------
# 레포 단위 harvest 집계
# ---------------------------------------------------------------------------

def harvest_repo(corpus: Any) -> Dict[str, Any]:
    """
    RepoCorpus 하나를 받아 ticket → {plan, tasks, manifest} 형식으로 묶어 반환한다.

    A2 결정: correlation key = ticket.
    ticketless 산출물은 "ticketless" 버킷에 분리한다.

    plans_dir 아래 모든 ticket 서브디렉토리의 plan.md를 수집한다 (p2 fix).
    """
    parse_errors: List[Dict[str, Any]] = []

    # --- plan harvest (ALL ticket subdirs) ---
    plan_recs: List[Dict[str, Any]] = []
    if corpus.plans_dir:
        plan_recs = harvest_plans_from_dir(corpus.plans_dir)
        for plan_rec in plan_recs:
            if "_parse_errors" in plan_rec:
                parse_errors.extend(plan_rec["_parse_errors"])

    # --- task harvest ---
    task_recs = harvest_tasks(corpus.tasks_dirs)
    for rec in task_recs:
        if "_parse_errors" in rec:
            parse_errors.extend(rec["_parse_errors"])

    # --- manifest harvest ---
    manifest_rec: Optional[Dict[str, Any]] = None
    if corpus.runs_dir:
        manifest_rec = harvest_manifest(corpus.runs_dir)
        if manifest_rec and "_parse_errors" in manifest_rec:
            if isinstance(manifest_rec["_parse_errors"], list):
                parse_errors.extend(manifest_rec["_parse_errors"])

    # --- ticket 기준 그룹핑 (A2) ---
    by_ticket: Dict[str, Any] = {}
    ticketless: List[Dict[str, Any]] = []

    # 모든 plan을 ticket 버킷에 배치
    for plan_rec in plan_recs:
        if "_parse_errors" in plan_rec:
            continue
        plan_ticket = plan_rec.get("ticket")
        if plan_ticket:
            _upsert_ticket(by_ticket, plan_ticket)
            by_ticket[plan_ticket]["plan"] = plan_rec
        else:
            ticketless.append({"type": "plan", "record": plan_rec})

    # manifest를 ticket 버킷에 배치
    if manifest_rec and "_parse_errors" not in manifest_rec:
        if isinstance(manifest_rec, dict) and "manifests" in manifest_rec:
            for m in manifest_rec["manifests"]:
                mt = m.get("ticket")
                if mt:
                    _upsert_ticket(by_ticket, mt)
                    by_ticket[mt].setdefault("manifests", []).append(m)
                else:
                    ticketless.append({"type": "manifest", "record": m})
        else:
            mt = manifest_rec.get("ticket")
            if mt:
                _upsert_ticket(by_ticket, mt)
                by_ticket[mt]["manifest"] = manifest_rec
            else:
                ticketless.append({"type": "manifest", "record": manifest_rec})

    # task records를 ticket 버킷에 배치
    for rec in task_recs:
        if "_parse_errors" in rec:
            continue
        tt = rec.get("ticket")
        if tt:
            _upsert_ticket(by_ticket, tt)
            by_ticket[tt].setdefault("tasks", []).append(rec)
        else:
            ticketless.append({"type": "task", "record": rec})

    return {
        "repo_path": corpus.repo_path,
        "repo_name": corpus.name,
        "by_ticket": by_ticket,
        "ticketless": ticketless,
        "parse_errors": parse_errors,
    }


def _upsert_ticket(by_ticket: Dict[str, Any], ticket: str) -> None:
    """ticket 버킷이 없으면 기본값으로 생성한다."""
    if ticket not in by_ticket:
        by_ticket[ticket] = {"plan": None, "tasks": [], "manifest": None}


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------

def _read_file(path: str) -> str:
    """파일을 UTF-8로 읽는다. 실패 시 OSError를 전파한다."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _git_hash_object(path: str) -> Optional[str]:
    """
    git hash-object로 working tree blob SHA를 계산한다.
    git 없거나 실패 시 None 반환 (무crash).
    """
    try:
        result = subprocess.run(
            ["git", "hash-object", path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    return None
