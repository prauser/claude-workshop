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

Spawn 4 read-only subagents in parallel:

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

## Step 1 — Draft plan

Synthesize into:

```markdown
## Plan — {TICKET}: {feature name}

### Requirements
- P0: [items]
- P1: [items]

### Impact scope
- Files to modify: [list]
- Dependencies: [modules]
- Risks: [areas]

### Task breakdown
1. {task} — complexity: {low/mid/high}, depends: {none or task N}

### Test strategy
- Unit: [targets]
- Integration: [targets]

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

| Situation | Response |
|-----------|----------|
| PRD/TechSpec not found | Skip Spec Agent, plan with Code + Jira only |
| No Implementation Config | Skip Spec and Context agents |
