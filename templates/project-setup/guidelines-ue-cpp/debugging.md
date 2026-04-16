# UE5 Debugging — Layer Tool Mapping

## Layer → Diagnostic Tools

| Layer | Tools |
|-------|-------|
| Presentation | Visual Logger (`UE_VLOG`), `PrintString`, Widget Reflector, BP breakpoints |
| Logic | `UE_LOG(LogCategory, Verbose/Warning/Error)`, `check()`, `ensure()`, `verify()`, C++ breakpoints |
| Data | SaveGame verification, DataTable integrity, `stat Memory`, GC object graph inspection |
| Build | UnrealBuildTool/UnrealHeaderTool errors, Live Coding failures (Ctrl+Alt+F11), `.uproject` parse errors |
| External | Dedicated server logs, platform SDK diagnostics, Online Subsystem logs |
| Networking | `LogNet` category, Replication Graph viewer, `stat Net`, `-NetTrace` |
| Physics | `p.VisualizePhysics 1`, collision trace debugging, `stat Physics` |

## Bisect Considerations

- If regression is in BP: check source control history for BP assets (binary diff not possible — check timestamps).
- If regression is in C++: standard `git bisect` with compile step.
- Live Coding patches are not captured in VCS — always verify with full recompile.

## Common UE Error Patterns

- `Accessed None` in BP → null object reference; check IsValid before access.
- `ensure()` failure → soft assertion; check log for callstack, fix before it becomes `check()`.
- PIE crash on play → often constructor-time code running before world is ready; defer to `BeginPlay`.
- Replication desync → check `HasAuthority()` guards and `DOREPLIFETIME` registration.
