# General Debugging — Layer Tool Mapping

## Layer → Diagnostic Tools

| Layer | Tools |
|-------|-------|
| Presentation | Browser DevTools (console, DOM inspector, network tab), framework dev tools (React/Vue devtools) |
| Logic | Application logs, debugger breakpoints, `console.log` / structured logging |
| Data | Database query logs, ORM debug mode, data integrity checks, migration status |
| Build | Compiler/bundler output, dependency resolution logs, `npm/yarn` error output |
| External | HTTP client logs, API response inspection, rate limit headers, service health endpoints |

## Bisect Considerations

- Standard `git bisect` for all regression bugs.
- For monorepo: narrow the bisect scope to the affected package.
- For flaky tests: run bisect with multiple iterations per commit (`git bisect run` with retry logic).

## Common Error Patterns

- `TypeError: Cannot read property of undefined` → null reference; trace data flow upstream.
- CORS errors → check server CORS config, not client code.
- Import/module not found → check exports, paths, and package.json `main`/`exports` fields.
- Build passes locally, fails in CI → check Node/runtime version, env vars, caching.
