# UE5 C++ Conventions

## Naming Prefixes
- `F` — plain structs and value types (e.g., `FVector`, `FMyData`)
- `U` — UObject-derived classes (e.g., `UMyComponent`)
- `A` — AActor-derived classes (e.g., `AMyCharacter`)
- `E` — enums (e.g., `EMyState`)
- `I` — interface classes (e.g., `IMyInterface`)
- `T` — template classes (e.g., `TArray`, `TMap`)

## UPROPERTY
- Always specify category: `UPROPERTY(EditAnywhere, Category="MyGame")`
- Use `BlueprintReadWrite` only when Blueprint access is required.
- Replicated properties: add `ReplicatedUsing=OnRep_VarName` and implement `OnRep_`.
- Never expose raw pointers to Blueprint; use `TObjectPtr<>` in UE5.

## UFUNCTION
- `BlueprintCallable` for actions; `BlueprintPure` for side-effect-free getters.
- RPCs: `Server` functions must be `Reliable` or `Unreliable` and `WithValidation`.
- `Client` RPCs only on Actor owned by that client.

## Garbage Collection
- Never store UObject raw pointers in non-UPROPERTY fields — GC will not track them.
- Use `UPROPERTY()` or `TWeakObjectPtr<>` for optional references.
- Do not store UObjects in `std::` containers; use `TArray`, `TMap`, `TSet`.

## Replication Basics
- Set `bReplicates = true` in constructor for replicated Actors.
- Implement `GetLifetimeReplicatedProps` and use `DOREPLIFETIME` / `DOREPLIFETIME_CONDITION`.
- Authority checks: `HasAuthority()` for server-only logic, `IsLocallyControlled()` for client-only.
