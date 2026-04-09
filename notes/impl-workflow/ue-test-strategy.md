# 언리얼 C++ 테스트 전략

> 2026-04-09 | impl-workflow에서의 테스트 계층 설계

## 테스트 프레임워크 3계층

| 프레임워크 | 에디터 필요 | 속도 | 워크플로우 위치 |
|-----------|-----------|------|----------------|
| **LLT** | NO | 초 단위 | implementer 단계 (TDD 가능) |
| **Automation Test** | YES (headless) | 분 단위 | PR Hook / integrator |
| **Gauntlet** | 외부 오케스트레이터 | 시간 단위 | CI/CD (워크플로우 밖) |

---

## LLT (Low Level Tests)

에디터 없이 독립 실행파일로 돌아감. Catch2 스타일 문법.

### 테스트 가능

- UE 값 타입: FString, FName, TArray, TMap, TSet, FVector, FQuat, FTransform
- 직렬화: FMemoryWriter/Reader, FJsonSerializer, 커스텀 Serialize()
- 네트워크 메시지 구조체: NetSerialize 레벨 (넷 드라이버 아님)
- 커스텀 알고리즘: 해싱, 압축, 파싱, 메모리 풀

### 테스트 불가 (경계)

UObject, UWorld, GEngine, 에셋 로딩, GConfig 필요하면 LLT 불가.

### 실행

```bash
UnrealBuildTool <Project>Editor Win64 Development -LowLevelTests
<Project>Tests.exe --reporter=console
<Project>Tests.exe "[Math]"  # 태그 필터
```

### implementer에서의 사용

프로젝트 레포 CLAUDE.md에서 지시 (implementer.md는 범용 유지):

```markdown
## Implementation Config
test_framework: LLT

## implementer 지침
- LLT 테스트 가능한 코드는 TDD로: 테스트 작성(RED) → 구현(GREEN) → 리팩토링
- LLT 불가 코드는: .h 인터페이스 → .cpp 구현 → 컴파일 확인 → 커밋
```

---

## Automation Test

에디터 headless 실행 (`-NullRHI -Unattended`). 에디터 기동 30초~수 분.

### 용도

- 맵 로드 → 액터 스폰 → 동작 검증 (기능 테스트)
- 에셋 전수 검증 (머티리얼 컴파일, 깨진 참조)
- 스크린샷 회귀 비교
- 단일 프로세스 리플리케이션 (PIE listen server)
- 에디터 워크플로우 (BP 생성/컴파일)
- 퍼포먼스 벤치마크

### 워크플로우 내 위치

`pre-pr-validate.sh`의 `test_command`에 넣으면 현재 구조에서 동작:

```bash
# Implementation Config
test_command: UnrealEditor-Cmd.exe Project.uproject -ExecCmds="Automation RunTests Game.Smoke" -NullRHI -Unattended -NoSound
```

또는 integrator가 태스크 전체 완료 후 실행.

---

## Gauntlet

외부 C# 오케스트레이터. 멀티프로세스 관리.

### 용도

- 데디케이티드 서버 + N 클라이언트 동시 테스트
- 플랫폼 인증 (서스펜드/리줌, 컨트롤러 분리)
- 장시간 안정성 테스트 (크래시/메모리 릭 감지)
- 로그 파싱 기반 pass/fail

### 워크플로우와의 관계

**스코프 밖.** CI/CD (Jenkins, BuildGraph)에서 nightly로 별도 실행.
Claude Code 세션 하나로 멀티프로세스 오케스트레이션 불가.

---

## 판단 기준

```
UObject/UWorld 필요?
  ├─ NO → LLT (implementer TDD, 초 단위)
  └─ YES → 멀티프로세스 필요?
              ├─ NO → Automation Test (PR Hook / integrator, 분 단위)
              └─ YES → Gauntlet (CI/CD, 워크플로우 밖)
```

---

## 관련 문서

- [experiment-5-ue-hooks.md](../../experiments/impl-workflow/experiment-5-ue-hooks.md) — UE Hook 성능 실험 (미실행)
- [hooks-spec.md](hooks-spec.md) — pre-pr-validate.sh에 test_command 설정
