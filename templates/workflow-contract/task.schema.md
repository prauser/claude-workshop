# Task Schema

> File: `.claude/tasks/pending/task-N-{name}.md`

A task file is the self-contained work order for one implementation unit.

Tasks are feature-level, not file-level. Keep each task small enough for one implementer pass and one reviewer pass.

## Filename

```text
task-{N}-{kebab-name}.md
```

Rules:

- `N` is a 1-based task number.
- `{kebab-name}` must be stable and descriptive.
- Result filename must append `-result` before `.md`.

## Required Sections

```markdown
# Task {N}: {feature 이름}

> Ticket: {TICKET}
> Phase: {N}
> Branch: feat/{TICKET}-{slug}
> Runner: in-session | headless-claude | headless-codex
> Plan: .claude/plans/{TICKET}/plan.md
> Depends on: {prior task ids 또는 none}

## 사용자 최초 프롬프트 원문

```
{spec-plan plan.md frontmatter의 user_prompt 원문 그대로 복사. 요약 금지.}
```

본 task가 plan.md의 어느 §Requirement / Phase 항목을 이행하는지 한 단락.

## 사전 준비

| 파일 | 읽는 목적 |
|---|---|
| {path} | {왜 읽어야 하는지} |

이전 task 산출물 (`.claude/tasks/done/...-result.md`)도 이 표에 명시.

## 작업 내용

{구체적 변경 지시. 파일 경로·시그니처·핵심 규칙을 박는다. 구현 디테일은 implementer에게 위임.}

## Acceptance Criteria

```bash
{실행 가능한 bash 검증 명령. 각 명령은 0 종료 = pass.}
```

## 주의사항

- **{X 하지 마라.}** 이유: {Y}.
- ...

## On completion

`.claude/tasks/done/task-{N}-{name}-result.md`를 result.schema.md에 따라 작성.
```

## Section Requirements

### 사용자 최초 프롬프트 원문 (Required)

`spec-plan`이 저장한 `plan.md` 최상단 YAML frontmatter의 `user_prompt` 값을 그대로 복사한다. 요약·정제 금지. task 간 일관성 확인의 기준이 된다.

### 사전 준비 (Required)

읽어야 할 파일 목록을 표로 명시. 이전 task 산출물(`.claude/tasks/done/...-result.md`)도 포함. implementer가 읽은 후 설계 의도를 이해하고 작업을 시작하도록 강제.

### 작업 내용 (Required)

구체적인 변경 지시. 파일 경로·시그니처·핵심 규칙을 명시. 구현 디테일은 implementer에게 위임.

### Acceptance Criteria (Required)

실행 가능한 bash 검증 명령. 각 명령은 zero exit = pass. 추상적 서술 금지 — 반드시 실행 가능한 커맨드.

Rules:

- Every promised command must appear in `test-output.log` or the task result.
- Every changed file in `diff.patch` must be covered by at least one AC check or task output declaration.

### 주의사항 (Required)

"X 하지 마라. 이유: Y" 형식으로 작성. 이유가 없거나 동어반복("out of scope", "not now")이면 무효.

### On completion (Required)

결과 파일 경로와 result.schema.md 링크 명시.

## Optional Sections

```markdown
## Quality Gates

## Review Notes

## Out of Scope
```

Use optional sections when they reduce ambiguity for the implementer or reviewer.

Note: "사용자 최초 프롬프트 원문" and "주의사항" are defined as Required above. The Optional Sections block does not include them.

## Minimal Example

```markdown
# Task 1: Parser fallback

> Ticket: OVDR-1234
> Phase: 1
> Branch: feat/OVDR-1234-parser-fallback
> Runner: in-session
> Plan: .claude/plans/OVDR-1234/plan.md
> Depends on: none

## 사용자 최초 프롬프트 원문

```
OVDR-1234 파서가 메타데이터 없을 때 throw 대신 빈 객체를 반환하도록 수정해줘.
```

본 task는 plan.md §Requirements P0 "파서 폴백 동작" 항목을 이행한다.

## 사전 준비

| 파일 | 읽는 목적 |
|---|---|
| `.claude/plans/OVDR-1234/plan.md` | 요구사항과 scope 확인 |
| `src/parser.ts` | 현재 파서 구현 파악 |
| `test/parser.test.ts` | 기존 테스트 패턴 확인 |

## 작업 내용

`src/parser.ts`의 `parseMetadata()` 함수가 메타데이터 필드 누락 시 throw 대신 빈 객체 `{}`를 반환하도록 수정.
`test/parser.test.ts`에 회귀 테스트 추가.

## Acceptance Criteria

```bash
npm test -- parser   # 모든 파서 테스트 통과
```

## 주의사항

- **기존 테스트를 비활성화하지 마라.** 이유: 폴백 동작 추가는 기존 동작을 깨면 안 된다.
- **`parseMetadata` 외 다른 함수를 수정하지 마라.** 이유: 이번 task의 scope는 폴백 동작 하나로 제한.

## On completion

`.claude/tasks/done/task-1-parser-fallback-result.md`를 result.schema.md에 따라 작성.
```
