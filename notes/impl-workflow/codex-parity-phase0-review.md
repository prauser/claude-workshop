# Codex Parity Phase 0 Review

> Status: living review — update items as they are resolved
> Date: 2026-04-27
> Branch: `codex/workflow-contract-phase0`
> Reviewed commit: `9452a51 Add workflow artifact contract draft`
> Related:
> - `codex-parity-runner-strategy.md`
> - `codex-parity-roadmap.md`
> - `templates/workflow-contract/{contract,roles,task.schema,result.schema,manifest.schema}.md`

## Summary

브랜치는 머지 가능 상태. 이전 단계에서 락을 건 4개 결정과 정합하고, contract 자체에 구조적 결함은 없음.

실행 단계에서 부딪힐 6개 포인트가 있었고, #1~#6은 본 브랜치에서 계약 문서 또는 로드맵에 반영됨. 남은 실행 전 확인 사항은 S3 Codex CLI surface 점검.

## Resolved

이전 리뷰에서 락을 건 4개 결정이 contract 문서들에 일관되게 반영됨.

| 결정 | 반영 위치 | 상태 |
|---|---|---|
| Role prompt canonical = `claude-config/agents/*.md` | `roles.md` 헤더, 각 role의 "Canonical prompt" 항목 | ✓ |
| Manifest 작성 = integrator | `manifest.schema.md` 헤더, `contract.md` §Run Manifest | ✓ |
| Codex runner 위치 = `templates/workflow-contract/runners/codex/` | `codex-parity-roadmap.md` §5 | ✓ |
| Audit/improvement 두 제안서 deferral | `codex-parity-roadmap.md` §Existing Documents And Status | ✓ |

문서간 정합성 점검:
- `contract.md` plan 섹션 7개 = `claude-config/commands/spec-plan.md` plan 템플릿 ✓
- `task.schema.md` required sections = `claude-config/commands/impl.md` task template ✓
- `manifest.schema.md` quality_gates 구조 = `integrator.md` `<gate>` 구조와 호환 ✓

## Review issues

진행 시 상단 status 박스를 갱신:
- `[ ]` open · `[~]` in-progress · `[x]` resolved · `[-]` deferred (사유 명시)

---

### #1 — result body format이 현재 에이전트와 충돌  ★ 가장 큰 이슈

- Status: `[x]` resolved
- Severity: high
- Affects: `result.schema.md`, `claude-config/agents/{implementer,reviewer,integrator}.md`

**현황**

`result.schema.md`는 markdown section 본문(`## Status`, `## Files Changed`, `## Tests`, `## Decisions`, `## Handoff` 등)을 요구. 현재 canonical 에이전트는 **XML 태그**(`<result>`, `<review>`, `<integration-result>`)를 출력. Phase 0의 "Keep Claude-native workflow behavior unchanged" 원칙과 충돌.

**선택지**

- (a) 스키마는 *target*, 에이전트는 그대로. 검증 시 XML→markdown 변환기로 정합화.
- (b) implementer/reviewer/integrator를 한 번에 schema 형식으로 갱신.
- (c) **권장**: frontmatter만 추가, body는 XML 유지. 스키마의 markdown body를 "*recommended* body when starting fresh"로 톤다운, XML도 valid한 result로 명시.

**Decision / notes**

> Decision: (c) 채택. Frontmatter는 Phase 0 validation result에 필수로 두되, body는 기존 canonical XML 출력도 valid로 명시. Markdown body는 fresh adapter 권장 형식으로 톤다운.

---

### #2 — `status` enum이 role 간 혼합

- Status: `[x]` resolved
- Severity: low
- Affects: `result.schema.md`

**현황**

```
status: success | failure | approved | needs-fix | partial
```

`success/failure/partial`은 implementer/integrator용, `approved/needs-fix`는 reviewer용인데 한 필드에 섞여 있음. Auditor가 `status == success`를 reviewer 결과에 적용하면 의미 없어짐.

**권장 조치**

role별 enum 분리:
```
implementer/integrator: success | failure | partial
reviewer:                approved | needs-fix
```

5분 분량. 본 브랜치에 같이 반영 권장.

**Decision / notes**

> Decision: `result.schema.md`에서 role별 status enum을 분리하고, auditor가 role 기준으로 해석하도록 명시.

---

### #3 — `audit.status: warning` 의미 미정의

- Status: `[x]` resolved
- Severity: low
- Affects: `manifest.schema.md`

**현황**

`audit.status: not-run | pass | fail | warning`에서 `warning`이 `fail`과 어떻게 다른지 정의 없음. Phase 0 audit이 "advisory until validation"이라 모든 실패가 warning일 수도, 아닐 수도 있음.

**권장 조치**

한 줄 추가:
```
warning: 객관 체크에서 모호하거나 false-positive 의심.
fail:    하드 위반 (예: 결과 파일 누락, schema 깨짐).
```

3분 분량. 본 브랜치에 같이 반영 권장.

**Decision / notes**

> Decision: `manifest.schema.md`에 `warning`과 `fail`의 차이를 정의. `warning`은 모호한 증거/false-positive 의심, `fail`은 missing result/schema break/scope violation 같은 hard violation.

---

### #4 — gap analysis 부재

- Status: `[x]` resolved
- Severity: medium (실행 효율)
- Affects: `codex-parity-roadmap.md`

**현황**

contract는 *목표 상태*만 기술. *Claude 현재 상태와의 차이*를 한눈에 보여주는 표가 없어 검증 작업자가 매번 양 문서를 대조해야 함.

**권장 조치**

roadmap §"Phase 0 Tasks" 직전에 표 1개 추가:

| Artifact | Claude 현재 | Contract 요구 | gap |
|---|---|---|---|
| plan.md 섹션 | 7개 모두 ✓ | 동일 | 없음 |
| task 파일 구조 | 동일 ✓ | 동일 | 없음 |
| result frontmatter | 없음 | 8필드 필수 | implementer/reviewer/integrator 수정 |
| result body | XML | markdown 섹션 (또는 #1 결정) | #1에 따라 |
| diff.patch | 자동 저장 안 함 | 필수 | wrapper 또는 integrator 추가 |
| test-output.log | 표준화 안 됨 | 필수 | 동일 |
| manifest.yaml | 없음 | 필수 | integrator가 생성 |

3분 분량. 본 브랜치에 같이 반영 권장.

**Decision / notes**

> Decision: `codex-parity-roadmap.md`에 Current Claude Gap Analysis 표 추가. #1 결정에 맞춰 result body gap은 "XML valid, markdown recommended"로 기록.

---

### #5 — Claude 측 manifest stub 생성 시점 모호

- Status: `[x]` resolved
- Severity: medium
- Affects: `codex-parity-roadmap.md` §2, 향후 `claude-config/agents/integrator.md` 또는 `commands/impl.md`

**현황**

`manifest.schema.md`는 "integrator finalizes; runner may create the initial stub" 분리. 하지만 Claude 측에서 *누가 stub을 만드는가* 미정.

- `/impl` 슬래시 커맨드가 시작 시? → `commands/impl.md` 수정 필요
- 첫 task의 implementer? → 부적절 (manifest는 ticket 단위)
- integrator가 처음부터? → `runner may create stub`이 사실상 Codex만 해당하는 비대칭

**권장 조치**

Claude 어댑터에서는 **integrator가 처음부터 작성**으로 단순화. Codex만 wrapper에서 stub→integrator finalize의 두 단계 비대칭 허용. roadmap §2에 한 줄 명시.

별도 결정 메모로 처리. *Phase 0 Task 8 (Claude adapter alignment)* 신설하여 이런 어댑터-쪽 합의 사항을 모으는 것이 깔끔.

**Decision / notes**

> Decision: Claude adapter는 integrator가 `manifest.yaml`을 처음부터 작성. Codex validation wrapper만 stub 생성 후 integrator finalize 가능. `codex-parity-roadmap.md` §2와 Phase 0 Task 8에 반영.

---

### #6 — `roles.md`에 `md-reviewer`, `test-engineer` 누락 미설명

- Status: `[x]` resolved
- Severity: low
- Affects: `templates/workflow-contract/roles.md`

**현황**

`claude-config/agents/`에는 7개인데 `roles.md`는 5개만 다룸. 의도적 생략(md-reviewer는 메타 prompt review, test-engineer는 spec-plan Strategy 모드)이지만 명시되지 않음.

**권장 조치**

`roles.md` 끝에 한 줄 추가:
> *Out of Phase 0 scope:* `md-reviewer` (meta prompt review), `test-engineer` (spec-plan strategy mode).

2분 분량. 본 브랜치에 같이 반영 권장.

**Decision / notes**

> Decision: `roles.md`에 Out of Phase 0 scope 항목으로 `md-reviewer`, `test-engineer`를 명시.

---

## Sub-decisions

contract 결함은 아니지만 검증 시점에 막히지 않도록 미리 결정해두면 좋은 항목들.

### S1 — Auditor 구현 위치: agentlens 확장 vs 신규 스크립트

- Status: `[x]` resolved
- 현재 roadmap §4가 양쪽 옵션을 보류

**권장**: Phase 0은 `templates/workflow-contract/auditor/audit.py` (또는 sh) 작은 스크립트로 시작 → Phase 1에서 agentlens로 흡수. 검증 *속도* 우선. roadmap §4 본문에 "preference: small script for first validation; migrate to agentlens in Phase 1"로 한 줄 명시.

**Decision / notes**

> Decision: Phase 0 first validation은 `templates/workflow-contract/auditor/`의 작은 스크립트로 시작하고, 반복 실행 가치가 확인되면 Phase 1에서 agentlens로 흡수.

### S2 — 검증 티켓 선택: 실제 티켓 vs 합성 task

- Status: `[x]` resolved
- roadmap §6이 "one small ticket or synthetic task" 양쪽 허용

**권장**: 합성 task로 시작. 이유: (1) 실제 jira-tools 의존 제거, (2) `Out of Phase 0 scope` 항목과 격리, (3) 비교 노이즈 최소화. 합성 task 1개 정의서를 `experiments/workflow-improvement/`에 같이 둠.

**Decision / notes**

> Decision: 첫 validation은 synthetic task로 시작. Jira/tooling dependency와 product-ticket noise를 제거한다.

### S3 — Codex CLI 가용 surface 확인

- Status: `[ ]` open
- strategy/roadmap 모두 `codex exec` 가용을 가정

**필요 확인 사항**:
- `codex exec` 실제 명령 형태 (system prompt / instruction 입력 방식)
- 멀티턴 vs 단일턴
- session_id 노출 여부 (`manifest.yaml`의 session_id 필드 채울 수 있는가)
- 도구 권한 / sandbox 설정
- 토큰 사용량 보고 가능 여부

Codex prototype 시작 전 30분~1시간 분량의 사전 점검.

**Decision / notes**

> _여기에 결정 기록_

---

## Recommended next steps

본 브랜치에서 마무리:
- [x] #2 status enum role별 분리 (`result.schema.md`)
- [x] #3 audit warning vs fail 정의 (`manifest.schema.md`)
- [x] #4 gap analysis 표 추가 (`codex-parity-roadmap.md`)
- [x] #6 roles.md scope 한 줄 (`roles.md`)

별도 결정 메모로 처리 후 진입:
- [x] #1 result body format 경로 결정 (a/b/c) → roadmap §3에 1~2 문장
- [x] #5 Claude manifest stub 생성 주체 결정 → roadmap §2에 1줄

Phase 0 Task 8 (Claude adapter alignment) 신설:
- [ ] `claude-config/agents/integrator.md`에 manifest 작성 1~2줄 추가
- [ ] (필요 시) implementer/reviewer에 frontmatter 추가 1~2줄
- [ ] `commands/impl.md`에 `.claude/runs/{TICKET}/` 디렉토리 생성 책임 명시

Sub-decisions:
- [x] S1 — Auditor 구현 위치 (작은 스크립트 권장)
- [x] S2 — 검증 티켓 (합성 권장)
- [ ] S3 — Codex CLI surface 사전 점검

Document hygiene from md-reviewer pass:
- [x] Weak directive modal cleanup in contract docs and roadmap
- [x] Roadmap dependency note before Phase 0 tasks
- [x] `hard Stop` casing fix
- [-] Larger roadmap diet deferred until after first validation

검증 진입 직전:
- [ ] `experiments/workflow-improvement/{YYYYMMDD}-codex-parity-validation.md` 생성, 합성 task 정의 포함
- [ ] Claude 한 번 + Codex 한 번 실행
- [ ] 양 run에 같은 auditor 적용
- [ ] Validation report 4개 축(contract sufficiency / result quality / cost / recommendation) 분리 기록

---

## Update log

| Date | Change | By |
|---|---|---|
| 2026-04-27 | Initial review draft | reviewer |
| 2026-04-27 | Resolved #1-#6, S1, S2 in contract docs and roadmap | codex |
| 2026-04-27 | Applied safe md-reviewer hygiene pass; deferred structural trimming | codex |
