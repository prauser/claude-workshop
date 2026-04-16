# General Performance Guidelines

## Review Criteria

- No N+1 query patterns — batch or join instead.
- No unbounded data fetching — paginate list endpoints.
- No synchronous blocking in async paths.
- No large object allocations in hot loops (per-request, per-event).
- No missing indexes on frequently queried columns.

## Measurement Tools

| Area | Tools |
|------|-------|
| API latency | Request logging with p50/p95/p99, APM (Datadog, New Relic, etc.) |
| Database | Query EXPLAIN plans, slow query logs, connection pool metrics |
| Frontend | Lighthouse, Web Vitals (LCP, CLS, INP), Chrome Performance tab |
| Memory | Heap snapshots, memory profiler, leak detection in long-running processes |
| Bundle | Bundle analyzer (webpack-bundle-analyzer, source-map-explorer) |

## Performance Checklist (per feature)

- [ ] List endpoints have pagination with reasonable default limit.
- [ ] Database queries use appropriate indexes.
- [ ] No sequential awaits where parallel execution is possible.
- [ ] Cache strategy defined for frequently-read, rarely-written data.
- [ ] Load tested with realistic data volume (not just empty DB).
