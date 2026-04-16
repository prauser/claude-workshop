# Spec Plan Mode

Planning only. Never write code or trigger implementation. All subagents are read-only.

**Usage**: `/spec-plan {TICKET}`

## On activation

1. Parse ticket ID from arguments.
2. Read `## Implementation Config` from CLAUDE.md → get `specs_path`, `prd_path`, `policies_path`, `log_repo`.
   - No config: skip Spec Agent and Context Agent, run Jira + Code only.

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

## Step 1 — Draft plan

Synthesize into:

```markdown
## Plan — {TICKET}: {feature name}

### Requirements
- P0: [items]
- P1: [items]

### Out of Scope
- [explicit "won't do" items for this ticket]

### Impact scope
- Files to modify: [list]
- Dependencies: [modules]
- Risks: [areas]

### Task breakdown
1. {task} — size: {XS/S/M/L/XL}, depends: {none or task N}

Sizing: XS: 1 file | S: 2-3 files | M: module-level | L: cross-module | XL: must split

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

### Open questions
- [decisions needed]
```

## Step 2 — Cross-review (3 rounds max)

Conflict types:

| Type | Pair | Trigger |
|------|------|---------|
| A | Code vs Spec | Code Agent flags high risk on a Spec Agent P0 item |
| B | Code vs Tests | edit order conflicts with existing test dependencies |
| C | Jira vs Code | deadline vs prerequisite refactoring |
| D | Test vs Code | Test Agent recommended level conflicts with Code Agent's identified coverage or risk assessment |

On conflict: pass opposing result to each agent → re-analyze. Max 3 rounds.
Unresolved after 3 rounds → present both opinions in Step 3.

## Step 3 — Human-in-the-Loop

Present plan summary. User can:
- Revise → update plan → re-confirm
- "Investigate more" → re-spawn relevant agent
- "OK" → Step 4
- "Cancel" → exit without saving

## Step 4 — Save plan

1. Save to `.claude/plans/{TICKET}/plan.md` in the project repo. If exists, save as `plan-v{N}.md`.
2. Tell user: "Plan saved. Run `/impl {TICKET}` when ready."

## Error handling

Missing config or PRD → skip the relevant agent and proceed with remaining data.
