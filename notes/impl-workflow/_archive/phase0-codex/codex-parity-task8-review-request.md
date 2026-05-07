# Codex Parity Phase 0 Task 8 — Review Request

> Branch: `codex/phase0-claude-adapter-alignment`
> Base: `codex/workflow-contract-phase0` (3 commits: `9452a51`, `54f51fb`, `b1b4d0d`)
> Status: reviewed — Option B applied, awaiting merge decision
> Date: 2026-04-27

## Summary

Phase 0 Task 8 (Claude adapter alignment) — Claude-native 워크플로우가 Phase 0 artifact contract를 만족하도록 4개 prompt 파일에 *최소* 변경. XML body 형식과 핵심 행동은 보존, frontmatter와 manifest 작성 책임만 추가.

## Changes (4 files)

| 파일 | 변경 |
|---|---|
| `claude-config/commands/impl.md` | `LOCAL-{YYYYMMDD-HHMMSS}` synthetic ticket ID 부여 규칙 / `.claude/runs/{TICKET}/` run artifact 디렉토리 / 기대 산출물 3개 명시 / 태스크 템플릿에 frontmatter 예시 |
| `claude-config/agents/implementer.md` | XML body 앞에 필수 YAML frontmatter 명시 + 예시 블록 |
| `claude-config/agents/reviewer.md` | 동일 (role/status는 reviewer용) |
| `claude-config/agents/integrator.md` | 동일 + Step 6 신설 (`manifest.yaml`을 scratch부터 작성) + Stop hook 의존 금지 룰 |

## Acceptance Criteria 점검 (handoff 기준)

| 기준 | 상태 |
|---|---|
| 기존 Claude agent body XML 유지 | ✓ |
| 모든 result-writing role에 frontmatter 명시 | ✓ |
| Integrator의 manifest 최종 작성 책임 명시 | ✓ |
| `/impl`이 run artifact 디렉토리 지정 | ✓ |
| Provider-specific Stop hook 도입 없음 | ✓ |
| 변경 범위 좁음 | ✓ (4 파일, ~50줄 추가) |

## md-reviewer Findings

전 4개 파일 `needs trimming` 판정. 합계 약 36줄 감축 가능.

### Apply now (기계적, 안전)

- [x] **F1** — `impl.md` L20 `should treat` → `Agents write all run artifacts to ...` (modal 강화, 1줄)
- [x] **F2** — 4개 파일의 dangling transition `Then write the existing XML body:` 제거 또는 prose 흡수 (4줄)
- [x] **F3** — `impl.md` "Run artifacts" 섹션을 activation Step 4로 흡수, 단독 섹션 삭제 (배치 정정, 위치 모호 해소)

### Defer / decision needed

- [ ] **F4** — **YAML 블록 인라인 vs 포인터화**: 같은 ~12줄 YAML 블록이 4곳(implementer/reviewer/integrator/impl.md task template)에 중복. 4-way sync hazard. 포인터화 시 ~36줄 회수 + schema가 single source of truth로 정착.
  - 인라인 유지 사유: agent invocation 시점 가독성, 누락 위험 낮음
  - 포인터 사유: 압축 원칙, 변경시 1곳만 수정
  - **권장: 포인터화**. 각 agent의 prose에 role-discriminating 필드(role/status)만 인라인, 나머지는 `result.schema.md` 참조

### Out of scope (handoff scope 외)

- [ ] **F5** — `impl.md` 태스크 템플릿의 `## Context` 등이 코드블록 내부 가짜 heading. *기존 형식이라 별도 결정사항*

## Phase 0 Review와 같이 발견된 사소한 충돌

- [x] **G1** — `integrator.md` frontmatter 예시 `task: integration` ↔ `result.schema.md` strict 정의 위반.
  - 처리: `result.schema.md`에 한 줄 추가 — `for integrator, use task: integration when no per-task slug applies`. 또는 schema에서 `task` 필드를 integrator에 옵션화.
  - 권장: 첫 번째 (3분 작업)

## Recommended commit plan

세 가지 옵션:

### Option A — 현재 그대로 커밋, follow-up으로 정리
```
Align Claude-native agents with Phase 0 artifact contract
```
- 장점: scope 좁음, 빠름
- 단점: md-reviewer 지적 즉시 후속 commit 필요

### Option B — 안전 항목만 적용 후 커밋  ★ 권장
F1, F2, F3, G1 적용 → 1개 커밋으로 정리. F4(인라인 vs 포인터)는 별도 커밋 또는 follow-up.
- 장점: 기계적 정리분만 같이 처리, scope 여전히 좁음
- 단점: 약간의 추가 작업

### Option C — md-reviewer 전부 반영 후 커밋
F1~F4 + G1 모두 적용. 2개 커밋으로 분리(alignment / md-reviewer cleanup).
- 장점: contract 정렬 + 압축 한 번에
- 단점: F4는 판단 필요한 변경이라 같은 PR에 묶으면 리뷰 부담↑

## Open items (검증 단계로 미룸)

- **S3** — Codex CLI surface 점검 (Task 5 Codex runner prototype 직전)
- **F5** — task template의 가짜 heading 처리 (Phase 0 외)
- **F4** — 포인터화 결정이 Option C로 가지 않으면 별도 follow-up

## Applied Decision

Option B was applied:

- F1, F2, F3, and G1 were fixed in the Task 8 branch.
- F4 remains deferred as a follow-up because it changes prompt compression strategy rather than artifact contract alignment.
- Unticketed `/impl` runs keep the existing confirmation flow; after confirmation, runs without an external ticket use `LOCAL-{YYYYMMDD-HHMMSS}`.
- Deploy is deferred until the Claude-native validation run, so Task 4 auditor and Task 5 Codex runner work can proceed without changing the active `~/.claude/` config.

## Post-merge: 다음에 풀리는 것

`codex-parity-roadmap.md` L85 dependency note 기준:

```
Task 6 (validation) ← Task 4 (auditor script) + Task 5 (Codex runner) + Task 8 (this)
```

Task 8 머지 후:
- Task 4 (auditor 스크립트, `templates/workflow-contract/auditor/`) — 병렬 가능
- Task 5 (Codex runner prototype, `templates/workflow-contract/runners/codex/`) — S3 사전점검 후 진입
- Task 6 (validation run) — Task 4·5 완료 시 진입

## Suggested next session prompt

```
Branch: codex/phase0-claude-adapter-alignment
Read codex-parity-task8-review-request.md.
Decide commit option (A/B/C). If B (recommended), apply F1, F2, F3, G1 then commit.
Do not include unrelated worktree items (deploy.sh, init-project.sh, untracked notes).
```
