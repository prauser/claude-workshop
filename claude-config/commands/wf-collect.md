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

## 사용법

```
/wf-collect                            # dry-run 기본, 샘플 번들 출력
/wf-collect --no-dry-run --target PATH  # 실제 git push (명시 옵션 필수)
```

실행 예시(python3 직접 호출):

```bash
# 전체 파이프라인 — dry-run (기본): 번들 파일 생성, push 없음
python3 ~/.claude/templates/workflow-contract/runners/telemetry/collect.py \
  run --roots ~/sbx-work --dry-run \
  --generated-at "$(date -Iseconds)" \
  --out ~/.claude/runs/PRA-109/bundle.sample.json

# 특정 티켓만 dry-run
python3 ~/.claude/templates/workflow-contract/runners/telemetry/collect.py \
  run --roots ~/sbx-work --ticket PRA-109 --dry-run \
  --generated-at "$(date -Iseconds)"

# 실제 업로드 (--no-dry-run + --target 모두 명시 필요)
python3 ~/.claude/templates/workflow-contract/runners/telemetry/collect.py \
  run --roots ~/sbx-work --no-dry-run \
  --target /path/to/shared-telemetry-repo \
  --generated-at "$(date -Iseconds)"

# 또는 env로 타깃 설정
WF_COLLECT_TARGET=/path/to/shared-telemetry-repo \
python3 ~/.claude/templates/workflow-contract/runners/telemetry/collect.py \
  run --roots ~/sbx-work --no-dry-run \
  --generated-at "$(date -Iseconds)"
```

### 번들 생성 타임스탬프 주입 (`--generated-at`)

번들 결정성(determinism) 보장을 위해 타임스탬프는 **반드시 외부에서 주입**한다.
수집기 코드 내부에서 `datetime.now()`를 호출하지 않는다.

```bash
--generated-at "$(date -Iseconds)"        # 셸 주입 권장
--generated-at 2026-06-19T00:00:00+09:00  # 재현(replay) 테스트 용
```

### self-check hard-fail 시 동작

1. `deid.selfcheck_bundle`이 번들 바이트에서 secret이나 forbidden_raw 원문을 탐지하면
   `DeidLeakError`를 raise한다.
2. `upload_bundle`은 이 에러를 잡지 않고 상위로 전파한다.
3. 번들 파일(dry-run `--out`)은 쓰이지 않는다 — **전부-또는-전무**.
4. collect.py는 오류 메시지를 stderr에 출력하고 exit code 1로 종료한다.

```
[ERROR] upload_bundle 실패 (self-check hard-fail 포함): forbidden_raw 누출: ...
```

이 경우 원인을 분석해 T4 LLM 추상화 품질을 확인한다.

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

**비식별 대상 (단 하나)**:
- `user_prompt` (plan.md 유저 raw NL 인풋) + 세션 유저 턴 원문만 비식별 대상이다 (plan P0-2).
- `intent.problem/approach/why`는 spec-plan이 생성한 AI 의역 내러티브이며 유저 raw NL이 아니다.
  비식별 대상이 아니므로 평문으로 번들에 포함한다 (plan Open Questions '`intent.*` 평문 권장' 결정).

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

> **CLI `collect.py run` 동작**: `collect.py run` CLI도 `assemble_forbidden_raw()`로 조립한
> forbidden_raw를 **필터링**(단어 수 ≥ 4 토큰) 후 `upload_bundle`에 전달한다.
> 즉, CLI 경로에서도 verbatim 누출 자동 차단이 CODE로 강제된다(문서 전용이 아님).
> 전체 LLM 추상화 파이프라인은 `/wf-collect` 커맨드를 통해 실행한다.

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
