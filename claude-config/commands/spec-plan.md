# Spec Plan Mode

Planning only. Never write code or trigger implementation. All subagents are read-only.

**Usage**: `/spec-plan {TICKET}`

## On activation

1. Parse ticket ID from arguments.
2. Read `## Implementation Config` from CLAUDE.md → get `specs_path`, `prd_path`, `policies_path`, `log_repo`.
   - No config: skip Spec Agent and Context Agent, run Jira + Code only.
3. Capture `user_prompt`: the exact natural-language text the user typed when invoking `/spec-plan`. Do not summarize or paraphrase. If the invocation has no text beyond the ticket ID, ask once: "원문이 비었습니다 — 이 task를 시작하게 된 한 문장을 입력하세요." Record the response verbatim.

## Iterative search protocol (max 3 cycles)

Used by Spec Agent and Code Agent:
1. DISPATCH: search target paths with feature keywords
2. EVALUATE: score results 0.0–1.0 for relevance, identify gaps
3. REFINE: use discovered terms to broaden search (codebase may use different terminology)
4. LOOP: repeat until sufficient coverage or 3 cycles reached

## Step 0 — Context gathering (parallel)

Spawn 5 read-only subagents in parallel:

**[Jira Agent]** (sonnet)
- `jira-tools get {TICKET}` via Bash (returns JSON)
- Collect: description, acceptance criteria, related issues, epic context
- If fails: ask user to paste ticket details

**[Spec Agent]** (sonnet) — skip if no config
- Search `prd_path`, `specs_path`, `policies_path` using iterative search protocol
- Return: requirements, priorities (P0/P1), open questions

**[Code Agent]** (opus)
- Search codebase files matching ticket keywords using iterative search protocol
- Return: affected files, dependency map, risk areas, test coverage

**[Context Agent]** (sonnet) — skip if no config
- Search `log_repo` for past similar work logs
- Return: related knowledge, past learnings

**[Test Agent]** (sonnet) — spawn `test-engineer` in Strategy mode; return its `<test-plan>` output

## Gate 1 — Requirements

> **STOP**: Do not proceed to Gate 2 without explicit user approval ("OK", "수정", or scope reclassification).
> Saying "진행해" alone is sufficient approval; silence is not.

Synthesize Step 0 output into **Requirements only** (no Impact scope, no Task breakdown, no Test Strategy yet):

```markdown
### Requirements
- P0: [items]
- P1: [items]

### Intentional Exclusions

| 제외 항목 | 이유 |
|---|---|
| {item} | {비용 X / 위험 Y / 타이밍 Z 중 하나를 명시 — "우선순위 낮음", "out of scope", "not now" 같은 동어반복 금지} |

> 운영 규칙: 이유 컬럼이 비어 있거나 동어반복("out of scope", "not now", "우선순위 낮음" 등)이면
> Gate 2로 진행하지 않는다. 각 항목에 비용/위험/타이밍 근거를 반드시 명시한다.

### Open Questions
- [decisions needed — items that can be decided during implementation without breaking task decomposition]
```

Present Gate 1 output. Wait for user decision:
- **"OK"** → proceed to Gate 2
- **"수정"** → revise in-place, re-present Gate 1, wait again
- **"투자/제외 재분류"** → move item between P0/P1/Intentional Exclusions, re-present Gate 1, wait again

**사용자 승인 없이는 Gate 2로 진행하지 않는다.**

## Gate 2 — Plan + Ambiguities

> **STOP**: Do not proceed to Gate 3 until the user has explicitly resolved every item in the Ambiguities table.
> Items may be resolved all at once ("일괄 결정") but each decision must be stated explicitly.

Using the Gate 1 approved Requirements, synthesize Impact Scope, Task Breakdown, Risks, and Ambiguities:

```markdown
### Impact Scope
- Files to modify: [list]
- Dependencies: [modules]
- Risks: [areas]

### Task Breakdown
1. {task} — size: {XS/S/M/L/XL}, depends: {none or task N}

Sizing: XS: 1 file | S: 2-3 files | M: module-level | L: cross-module | XL: must split

### Ambiguities (require decision before tasks freeze)

> Ambiguities는 "지금 결정하지 않으면 task 분해가 무너진다".
> Open Questions(Gate 1)는 "구현 중 결정해도 무방"한 항목.
> Ambiguities와 Open Questions를 혼용하지 말 것.

| # | 논의점 | 옵션 A | 옵션 B | 결정자가 알아야 할 trade-off |
|---|---|---|---|---|
| 1 | {모호한 결정 지점} | {A안 + 한줄 결과} | {B안 + 한줄 결과} | {둘 중 어느 쪽이 비용/시간/위험에 어떻게 영향} |
```

Present Gate 2 output. Each Ambiguity must be decided before proceeding:
- User resolves Ambiguities (one by one or all at once, but each decision must be explicit)
- After all Ambiguities resolved: **"OK"** → proceed to Gate 3

**사용자 승인 없이는, 그리고 Ambiguities가 하나라도 미결인 상태에서는 Gate 3으로 진행하지 않는다.**

## Gate 3 — Test Strategy

> **STOP**: Do not proceed to Step 2 (Cross-review) without explicit user approval.

Using Gate 2's task-level AC and risk areas, incorporate the Test Agent's `<test-plan>` output:

```markdown
### Test Strategy
- Unit: [targets from Test Agent]
- Integration: [targets from Test Agent]
- E2E: [critical user flows from Test Agent]
- Risk areas: [high-priority test targets]

### Quality Gates
- [ ] All tests pass
- [ ] No regressions in affected modules
- [ ] Coverage maintained or improved on changed files
- [ ] Build succeeds
```

Present Gate 3 output. Wait for user:
- **"OK"** → proceed to Step 2 (Cross-review)
- **"수정"** → revise Test Strategy, re-present Gate 3, wait again

**사용자 승인 없이는 Step 2(Cross-review)로 진행하지 않는다.**

> **Shortcut**: If the user explicitly requests "건너뛰기" or "skip gates", all three gates may be combined into a single output. Default behavior is 3 separate gates.

## Step 2 — Cross-review (3 rounds max)

Conflict types:

| Type | Pair | Trigger |
|------|------|---------|
| A | Code vs Spec | Code Agent flags high risk on a Spec Agent P0 item |
| B | Code vs Tests | edit order conflicts with existing test dependencies |
| C | Jira vs Code | deadline vs prerequisite refactoring |
| D | Test vs Code | Test Agent recommended level conflicts with Code Agent's identified coverage or risk assessment |

On conflict: pass opposing result to each agent → re-analyze. Max 3 rounds.
Unresolved after 3 rounds → present both opinions in Final Review.

## Final Review (post cross-review)

Present consolidated plan summary (all gates + cross-review results). User can:
- Revise → update plan → re-confirm
- "Investigate more" → re-spawn relevant agent
- "OK" → Step 4
- "Cancel" → exit without saving

## Step 4 — Save plan

1. Save to `.claude/plans/{TICKET}/plan.md` in the project repo. If exists, save as `plan-v{N}.md`.
2. The plan.md file must begin with the following YAML frontmatter:

```markdown
---
ticket: {TICKET}
created_at: {ISO 8601 with timezone}
user_prompt: |
  {사용자가 /spec-plan을 호출하며 입력한 최초 프롬프트 전문 — indent 보존. 요약·정제 금지.}
---

# Plan — {TICKET}: {feature name}
...
```

3. `user_prompt` must be the verbatim original text captured in "On activation" step 3. Summarization or paraphrasing is forbidden.
4. Note for `/impl`: when `/impl` issues task files from this plan, it must copy the same `user_prompt` value to the top of each task file's metadata. (Implementation of this copy behavior is handled in the task format update phase; this spec establishes the intent.)
5. Tell user: "Plan saved. Run `/impl {TICKET}` when ready."

## Error handling

Missing config or PRD → skip the relevant agent and proceed with remaining data.
