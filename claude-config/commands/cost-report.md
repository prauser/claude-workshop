Read `C:\Users\isutal\.claude\statusline-history.json` and generate a usage report.

## Rules
- Dates: convert `last_update` to **KST (UTC+9)**
- Exclude idle sessions (cost=0 AND tokens=0)
- Cost: USD 2dp | Tokens: K units | API time: human-readable (e.g., 2m 30s)
- Workspace name: last path segment (e.g., `C:\SBX\client` → `client`)

## Sections

### 1. Summary by period
Table: Period | Sessions | Cost | Tokens | API Time — for Today, Last 7 days, Last 30 days

### 2. Daily breakdown (last 7 days)
Table: Date | Sessions | Cost | Tokens | API Time — descending, skip empty days

### 3. Cost by workspace
Table: Workspace | Sessions | Cost | Tokens — descending by cost

### 4. Cost by model
Table: Model | Sessions | Cost | Tokens | Avg Cost/Session — descending by cost

### 5. Top 5 sessions by cost
Table: Model | Workspace | Cost | Tokens | API Time
