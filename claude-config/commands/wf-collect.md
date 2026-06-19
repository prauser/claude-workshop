# /wf-collect — 워크플로 텔레메트리 수집기

이 커맨드(command)는 `~/sbx-work/*` 아래에 있는 레포들의 워크플로 텔레메트리(telemetry)
(plan/result/manifest frontmatter + 세션로그 메타)를 수확(harvest)하고, 비식별(de-identification)
처리 후 번들(bundle)로 직렬화해 공유 레포에 업로드한다.

**핵심 속성**: 명시 실행만(opt-in only). 외부 설치 의존 0(stdlib만). 비식별 후 업로드.

## 파이프라인 스테이지

| 순서 | 스테이지 | 설명 | 구현 |
|------|---------|------|------|
| 1 | **discover** | `~/sbx-work/*` 디스커버리: `.claude/` 보유 레포 열거, 세션로그 slug 역매핑 | 구현: task-1 |
| 2 | **harvest-artifacts** | 각 레포 `.claude/{plans,tasks,runs}` frontmatter 수집. 드리프트(drift) 내성 방어적 파싱 | 구현: task-2 |
| 3 | **harvest-sessions** | 세션로그 메타 수집 → 평문(plain-text) 이벤트 스트림(tool/path/pattern/error/seq/tokens). vendored lean 파서 사용 | 구현: task-3 |
| 4 | **de-id** | 유저 raw 자연어 인풋(NL input) LLM 추상화(특성 보존·verbatim 제거) + secret 스캔 + 런타임 self-check hard-fail. LLM 추상화는 이 커맨드가 수행 | 구현: task-4 |
| 5 | **bundle** | 번들 직렬화(버전드 스키마) + git 업로드. `--dry-run` 시 업로드 없이 감사(audit)만 | 구현: task-5 |

## 사용법 (placeholder — task-5에서 확정)

```
/wf-collect
/wf-collect --dry-run
```

실행 예시(python3 직접 호출):

```bash
# 전체 파이프라인 (bundle까지)
python3 ~/.claude/templates/workflow-contract/runners/telemetry/collect.py discover

# 드라이런(dry-run) — 업로드 없이 번들 내용 확인 (task-5 이후)
python3 ~/.claude/templates/workflow-contract/runners/telemetry/collect.py --dry-run bundle

# 특정 티켓만
python3 ~/.claude/templates/workflow-contract/runners/telemetry/collect.py --ticket PRA-109 discover
```

## 비식별(De-identification) 스테이지 계약

> 이 섹션은 스테이지 4(de-id)의 LLM 추상화 계약을 정의한다. 결정론적(deterministic)
> Python 검증(`deid.py`)과 LLM 추상화(이 커맨드)의 책임 경계를 명확히 한다.

### 비식별 책임 분리

| 책임 | 담당 |
|------|------|
| 유저 raw NL 추상화 (verbatim → 특성) | **이 커맨드(LLM)** |
| secret 스캔 + 런타임 self-check hard-fail | **`deid.py` (결정론적 Python)** |

### LLM 추상화 입력/출력 계약

**입력** (이 커맨드가 받는 것):
- `plan.user_prompt` — plan.md의 유저 raw 자연어 프롬프트 원문
- `raw_user_turns` — 세션로그에서 추출한 유저 턴 원문 리스트

**출력** (이 커맨드가 생성하는 것):
- `user_input_characteristics` 객체 — 특성(feature)만 보존, verbatim(원문) 제거

```json
{
  "user_input_characteristics": {
    "length_band": "S|M|L",
    "has_ticket_ref": true,
    "request_shape": "feature|bugfix|question|refactor|config|other",
    "specificity": "low|med|high",
    "mentions_external_tool": false,
    "language": "ko|en|mixed"
  }
}
```

**금지 사항**:
- 원문 문장 복붙(verbatim copy) 금지 — 특성/카테고리만
- 부분 인용(partial quote), 패러프레이즈(paraphrase)도 금지 — 특성으로 추상화
- `path/code/diff/intent.*` 필드는 비식별 대상이 아님 — 평문 그대로

### 추상화 후 self-check 호출 (필수)

이 커맨드는 추상화 완료 후 반드시 `deid.selfcheck_bundle`을 호출해야 한다.
**사람 승인 게이트 없이** 진행한다 — 자체검열(self-censorship)은 측정 무결성(목표 #2)을 훼손한다.
프라이버시는 자동 self-check(hard-fail)가 담당한다.

```python
# 추상화 후 번들 조립 예시 (의사코드)
bundle = {
    "user_input_characteristics": abstracted_characteristics,
    # ... 기타 평문 필드
}

# forbidden_raw 조립: plan user_prompt + 모든 session raw_user_turns
# collect.assemble_forbidden_raw(artifact_results, session_results) 사용
forbidden_raw = collect.assemble_forbidden_raw(artifact_results, session_results)

# self-check — 실패 시 DeidLeakError raise (전체 업로드 차단)
from deid import selfcheck_bundle, BUNDLE_DUMPS_KWARGS
selfcheck_bundle(bundle, forbidden_raw)

# T5 직렬화 시 반드시 BUNDLE_DUMPS_KWARGS를 사용해 동일한 바이트를 생성해야 한다
import json
bundle_bytes = json.dumps(bundle, **BUNDLE_DUMPS_KWARGS)
```

self-check 실패 시 `DeidLeakError`가 raise되어 번들 업로드 전체가 차단된다(전부-또는-전무).

### T5 직렬화 불변성 (serialization invariant)

> **T5 필수 사항**: T5(bundle 직렬화 + git 업로드) 는 번들을 `json.dumps(bundle, **BUNDLE_DUMPS_KWARGS)` 로
> 직렬화해야 한다. `BUNDLE_DUMPS_KWARGS = dict(ensure_ascii=False, sort_keys=True)`.
>
> 이유: `selfcheck_bundle`이 이 kwargs로 직렬화한 바이트를 검사한다.
> T5가 다른 kwargs를 쓰면 self-check된 바이트와 실제 업로드 바이트가 달라질 수 있다.
> `deid.BUNDLE_DUMPS_KWARGS`를 import해 사용하면 두 직렬화가 항상 동일하다.

## 주의사항

- 이 커맨드는 **명시 실행**만 한다. 자동/백그라운드/스케줄 트리거 없음.
- raw 로그는 머신 밖으로 반출하지 않는다. Tier-2 드릴다운(drill-down)은 로컬 raw에만 접근.
- 업로드 직전 런타임 self-check가 hard-fail하면 번들 전체가 업로드되지 않는다(전부-또는-전무).
- 비식별 대상: 유저 raw 자연어 인풋(`user_prompt` + 세션 유저 턴)만. 경로/코드/diff는 평문.
