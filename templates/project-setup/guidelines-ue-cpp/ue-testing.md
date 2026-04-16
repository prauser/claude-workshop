# UE5 Testing Guidelines

## System Boundaries (mock here, not between internal functions)

- World/Level context (use test world or minimal map)
- Asset loading (use mock assets or preloaded test fixtures)
- Subsystems (GameInstance, Online, etc.)
- Network replication (use simulated net driver)
- Platform services (input, save system, achievements)

## Automation Test Framework
- Use `IMPLEMENT_SIMPLE_AUTOMATION_TEST` for unit-level tests.
- Use `IMPLEMENT_COMPLEX_AUTOMATION_TEST` for parameterized or data-driven tests.
- Register tests with category path: `"MyGame.Unit.ComponentName"`.
- Test flags: combine `EAutomationTestFlags::EditorContext | SmokeFilter` etc. to control when tests run.
- Run via: Session Frontend > Automation tab, or CLI: `UE4Editor-Cmd ... -ExecCmds="Automation RunTests MyGame"`.

## Test Categories (flag guidance)
- `SmokeFilter` — fast (<1s), always run, no editor dependency.
- `EngineFilter` — requires full engine; run in CI.
- `ProductFilter` — end-to-end, slow; run pre-release only.

## Live Coding Limits
- Does not recompile shaders, reload assets, or pick up new UPROPERTY/UFUNCTION/class hierarchy changes.
- After Live Coding patch: re-run affected Automation Tests. Full recompile if structural changes.

## Test Structure Checklist
- [ ] Each test has a single clear assertion target.
- [ ] Tests do not share mutable global state.
- [ ] Tests clean up spawned Actors in `TearDown` or use `ADD_LATENT_AUTOMATION_COMMAND`.
- [ ] Latent tests use `FAutomationTestLatentCommand` for async operations.
- [ ] New features require at least one smoke test before merge.
