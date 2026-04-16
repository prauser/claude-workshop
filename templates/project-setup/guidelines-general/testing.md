# General Testing Guidelines

## Test Framework

- Unit: Jest, Vitest, pytest, Go testing — framework matching the project stack.
- Integration: Test DB/API boundaries with real or in-memory dependencies.
- E2E: Playwright, Cypress, or equivalent browser automation for critical user flows.

## System Boundaries (mock here, not between internal functions)

- Database / ORM layer
- External HTTP APIs / third-party services
- File system I/O
- Email / notification services
- Clock / time-dependent logic (use injectable clock)

## Test Structure Checklist

- [ ] Arrange-Act-Assert pattern in every test.
- [ ] Each test is independent — no shared mutable state between tests.
- [ ] Descriptive test names that read like specifications.
- [ ] Prefer real implementations > fakes > stubs > mocks.
- [ ] Tests clean up created resources (DB records, temp files) in teardown.

## CI Integration

- Run unit tests on every push.
- Run integration tests on PR / merge to main.
- Run E2E tests on staging deploy or release candidate.
- Fail the build on any test failure — no skipped tests in CI.
