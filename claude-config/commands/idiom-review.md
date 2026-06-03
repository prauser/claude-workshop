# idiom-review

pool에 누적된 미처리 어휘 후보를 사람이 1건씩 검토해 GLOSSARY 등록, preamble §9 inline 예시 추가, 또는 아카이브(archive) 처리한다.

**Usage**: `/idiom-review` (인자 없음)

## Pool schema

`~/.claude/idiom-pool.yaml` 의 구조 (SSOT — 런타임 자동 생성, 워크숍 repo 에는 파일 자체 없음):

```yaml
# ~/.claude/idiom-pool.yaml
version: 1
entries:
  - term: stale
    count: 5
    last_ctx: "캐시가 오래된(stale) 상태일 때 ..."
    first_seen: 2026-06-01T00:00:00+09:00
    last_seen: 2026-06-04T00:00:00+09:00
    status: open  # open | archived
```

**필드 설명**:

| 필드 | 타입 | 설명 |
|---|---|---|
| `version` | int | 스키마 버전. 현재 1 고정. |
| `term` | string | 영어 어휘 (소문자, 단수형 권장) |
| `count` | int | preamble §9 룰 4 위반 누적 횟수 |
| `last_ctx` | string | 가장 최근 사용 맥락 한 줄 |
| `first_seen` | ISO 8601 | 첫 등장 타임스탬프 |
| `last_seen` | ISO 8601 | 최근 등장 타임스탬프 |
| `status` | enum | `open` (검토 대상) \| `archived` (이전 검토에서 보류 처리됨) |

**자동 생성 규칙**: preamble §9 룰 4 에서 `idiom_candidates:` 슬롯에 처음 append 할 때 파일이 없으면 자동 생성. `~/.claude/` 디렉터리는 사전 존재 가정.

**reset/archive 규칙** (R-pool-bloat 대응):

- `g` (GLOSSARY 등록) / `p` (preamble §9 inline 추가) 처리 후 → entry 삭제 (reset).
- `a` (archive) 처리 후 → `status: archived` 마킹 (다음 임계 알림에서 제외).
- `s` (skip) 처리 후 → 변경 없음 (다음 임계 알림에서 다시 등장).

## On activation

1. `~/.claude/idiom-pool.yaml` 읽기.
   - 파일이 없으면: "pool 비어 있음. 종료." 후 stop.
   - 파일은 있으나 `entries:` 가 비거나 `status: open` 항목이 0건이면: "처리 대상 항목 없음. 종료." 후 stop.

2. 임계(threshold) 이상 entries 추출: **term별 `count` ≥ 3** 이고 `status: open` 인 항목. 없으면 "임계(≥3) 미달 항목 없음. 종료." 후 stop.

3. LLM 이 각 term 을 분류 + 한글 풀이 후보 draft:
   - 분류 A: 한국어 자연 대응어가 있음 → preamble §9 inline 예시 후보
   - 분류 B: 자연 대응어 없음 / 도메인 고유어 → GLOSSARY 등록 후보

4. 사람에게 1건씩 제시:

   ```
   term {영어 term} (count N)
   풀이 draft: {한글 풀이 또는 "괄호 병기" 제안}
   분류: {A — preamble §9 inline 후보 / B — GLOSSARY 등록 후보}
   맥락: {last_ctx}

   응답 → g=GLOSSARY 등록 / p=preamble §9 inline 추가 / s=skip / a=archive
   ```

5. **`g` 응답** (GLOSSARY 등록):
   - CLAUDE.md `## Implementation Config` 의 `glossary_path:` 가 가리키는 GLOSSARY 파일에 entry append.
   - 형식: `## {영어 term}\n\n{한글 풀이 한 줄}` (기존 GLOSSARY 형식 준수).
   - `glossary_path` 미설정 또는 파일 미존재 시: 사용자에게 경로 입력 요청.
   - pool entry 삭제 (reset).

6. **`p` 응답** (preamble §9 inline 추가):

   **[cwd 가드]** `p` 응답 처리 전, `templates/workflow-contract/preamble.md` 가 현재 cwd 기준으로 존재하는지 확인:
   - 파일이 없으면: "현재 디렉터리에서 `templates/workflow-contract/preamble.md` 를 찾을 수 없습니다. workshop repo 절대 경로를 입력하거나(예: `/home/user/claude-workshop`) `p` 를 비활성화하려면 `n` 을 입력하세요:" 라고 요청.
     - 사용자가 절대 경로를 입력하면: `{입력경로}/templates/workflow-contract/preamble.md` 로 경로 재시도. 그래도 없으면 `p` disabled — pool entry 변경 없음.
     - 사용자가 `n` 을 입력하면: `p` disabled — pool entry 변경 없음.
   - (`~/` 하드코딩 금지 — 경로는 항상 사용자 제공 또는 cwd 기반으로만 결정.)

   **[분류별 분기]**
   - **분류 A** (한국어 자연 대응어 있음): §9 룰 1 한글표기 표에 행 추가하는 patch draft 를 화면에 표시.
   - **분류 B** (도메인 고유어 / 자연 대응어 없음): `p` 대신 GLOSSARY(`g`) 등록이 적합한 term 입니다. 강제로 preamble §9 룰 1 표에 추가하려면 `py` 를 입력하세요 (권장하지 않음). `py` 입력 시 §9 룰 1 표가 아닌 룰 2 설명 아래 예시 위치에 `{영어 term} (= {한글 풀이 또는 "도메인 고유어, 번역 없음")` 형태로 patch draft 를 표시.
   - 사용자에게 `y/n` 확인 (분류 B 의 경우 `py` 이미 확인됨):
     - `y` → 파일 수정 적용. 완료 후 "deploy.sh 를 실행해 ~/.claude/ 에 반영하세요." 안내.
     - `n` → 취소. pool entry 는 변경 없음 (다음 임계 알림에서 다시 등장).
   - `y` 처리 후 pool entry 삭제 (reset).

7. **`a` 응답** (archive):
   - pool entry `status` 를 `archived` 로 변경. 다음 `/idiom-review` 임계 알림에서 제외.

8. **`s` 응답** (skip):
   - pool entry 변경 없음. 다음 `/idiom-review` 호출 시 다시 제시.

9. 모든 임계 항목 처리 후 요약 출력:

   ```
   처리 완료: g={N}건, p={N}건, a={N}건, s={N}건
   pool 잔여 open 항목: {N}건
   ```

## Rules

- **자동 등록 금지**: 모든 entry 는 사람 응답 1건당 처리. 일괄 자동 등록 없음 (R6 정합).
- **preamble §9 patch 는 draft only**: `y` 응답 후에만 파일 수정. `n` 시 취소.
- **수정 가능 파일 범위**: GLOSSARY(`glossary_path`) 와 workshop preamble(`templates/workflow-contract/preamble.md`) 만. 그 외 파일 수정 금지 (scope 잠금). preamble 경로는 cwd 기준으로 결정 — `~/` 하드코딩 금지. cwd 에 파일이 없으면 step 6 cwd 가드 절차 적용.
- **임계값 고정**: count ≥ 3. 변경 불가 (OQ6 결정 — 고정 3, 가변화는 데이터 누적 후 Phase 2b).
- **L1 hook 금지**: SessionEnd → telemetry 자동화 없음 (plan §Intentional Exclusions).
