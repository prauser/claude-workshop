# MyGame

UE 5.5 action game.

## Build
- Build tool: UnrealBuildTool
- Launch editor: `UnrealEditor.exe MyGame.uproject`
- Live Coding: Ctrl+Alt+F11
- Full rebuild: `Build.bat MyGameEditor Win64 Development`

## Implementation Config
specs_path: Docs/Specs
prd_path: Docs/PRD
guidelines:
  - .claude/guidelines/ue-conventions.md
  - .claude/guidelines/debugging.md
  - .claude/guidelines/ue-testing.md
  - .claude/guidelines/ue-performance.md

## Quality Gates
- [ ] Compile succeeds (Development Editor, zero errors)
- [ ] Static Analysis passes (UnrealHeaderTool, no new warnings)
- [ ] Automation Tests pass (`MyGame.Unit.*` smoke suite)
- [ ] Cook succeeds (Win64, Development)
