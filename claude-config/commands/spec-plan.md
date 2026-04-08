# Spec Plan Mode

Create an implementation plan from a Jira ticket. Never write code — planning only.

**Usage**: `/spec-plan {TICKET}`

## On activation

1. Parse ticket ID from arguments.
2. Read `## Implementation Config` from CLAUDE.md → get `specs_path`, `prd_path`, `policies_path`, `log_repo`.
   - No config: skip Spec Agent and Context Agent, run Jira + Code only.

## Step 0 — Context gathering (parallel)

Spawn 4 read-only subagents in parallel:

**[Jira Agent]** (sonnet)
- `jira-tools get {TICKET}` via Bash (returns JSON)
- Collect: description, acceptance criteria, related issues, epic context
- If fails: ask user to paste ticket details

**[Spec Agent]** (sonnet) — skip if no config
- Grep `prd_path`, `specs_path`, `policies_path` with feature keywords
- Return: requirements, priorities (P0/P1), open questions

**[Code Agent]** (opus)
- Analyze impact in current repo: related files, dependencies, existing tests
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
| A | Code vs Spec | "risky" vs "P0 required" |
| B | Code vs Tests | edit order vs test dependencies |
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
| jira-tools fails | Ask user to paste ticket details |
| PRD/TechSpec not found | Skip Spec Agent, plan with Code + Jira only |
| No Implementation Config | Skip Spec and Context agents |

## Rules
- Never write code. Planning only.
- All subagents are read-only.
- Do not trigger implementation.
