# UE5 Performance Guidelines

## Review Criteria (reviewer agent uses these)

- No heavy computation in Tick without throttling or timer.
- No per-frame memory allocation in gameplay loops.
- No unbounded TArray iteration in hot paths — cache or use spatial structures.
- No missing LODs on meshes visible at distance.
- No BP-heavy paths without profiling (`stat Blueprints`).

## Frame Time Targets
- 60 fps: <16.6ms total frame budget.
- 30 fps: <33.3ms total frame budget.
- Game thread must stay under 8ms for 60fps headroom.
- Render thread target: <10ms for typical PC builds.

## Draw Call Limits
- Mobile: <200 draw calls per frame.
- PC/Console: <2000 draw calls per frame.
- Merge static meshes where possible; use Instanced Static Mesh (ISM/HISM) for repeated geometry.

## GC Hitch Prevention
- Avoid large object graphs being created/destroyed per frame.
- Pool frequently spawned/despawned UObjects and Actors.
- Use `FTimerManager` for deferred cleanup instead of immediate `Destroy()` in tight loops.
- Profile GC with: `stat GC` and `gc.TimeBetweenPurgingPendingKillObjects`.

## Key Stat Commands
- `stat FPS` — frame rate and frame time overlay.
- `stat Unit` — Game/Draw/GPU thread breakdown.
- `stat SceneRendering` — draw calls, triangles, shadow counts.
- `stat Memory` — allocated pools and texture memory.
- `stat Particles` — particle system CPU cost.
- `ProfileGPU` — single-frame GPU capture (requires -d3ddebug or RenderDoc).

## Performance Checklist (per feature)
- [ ] No tick-heavy components running on non-ticking Actors.
- [ ] Async tasks used for heavy computation (>1ms); not blocking game thread.
- [ ] LODs configured for all meshes visible at distance.
- [ ] No unbounded TArray searches in Tick; cache or use index structures.
- [ ] Blueprint-heavy paths profiled with `stat Blueprints`.
