# 실험 5: 언리얼 C++ 레포 Hook 성능 체감

> 전제: 실험 1~4가 sandbox에서 완료된 상태
> 실행 위치: 언리얼 C++ 프로젝트 레포
> 목적: Hook에 걸 수 있는 체크의 실질적 상한선 확인

---

## 사전 준비

1. 실험 1~3에서 확인된 Hook 환경변수/matcher 문법을 반영한 settings.json 준비
2. 레포의 CLAUDE.md에 Implementation Config 추가:

```markdown
## Implementation Config

| 항목 | 값 |
|------|-----|
| format_command | (아래 실험에서 결정) |
| build_command | (아래 실험에서 결정) |
| test_command | (아래 실험에서 결정) |
| log_repo | ../impl-logs |
```

---

## 실험 A: clang-format (커밋 Hook 후보)

### 가설
clang-format은 충분히 빠르므로 PreToolUse(git commit)에 넣어도 체감 지연이 없을 것.

### 실행

1. `.clang-format` 파일이 있는지 확인 (없으면 프로젝트 기본 설정 사용)

2. staged 파일만 체크하는 스크립트 작성:
```bash
#!/bin/bash
# .claude/hooks/pre-commit-format.sh
STAGED=$(git diff --cached --name-only --diff-filter=ACMR -- '*.cpp' '*.h')
if [ -z "$STAGED" ]; then exit 0; fi

echo "[Hook] clang-format 체크 중..."
FAILED=0
for f in $STAGED; do
  if ! clang-format --dry-run --Werror "$f" 2>/dev/null; then
    echo "  포맷 오류: $f"
    FAILED=1
  fi
done

if [ $FAILED -ne 0 ]; then
  echo "[Hook] clang-format 실패 — 커밋 차단" >&2
  exit 2  # exit 2 = Claude Code에서 도구 차단
fi
echo "[Hook] clang-format 통과"
```

3. settings.json에 등록:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(git commit*)",
            "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-commit-format.sh"
          }
        ]
      }
    ]
  }
}
```

4. 테스트: .cpp 파일 하나 수정 → git commit 시도 → 시간 측정

### 기록

| 항목 | 값 |
|------|-----|
| 파일 수 | |
| 소요 시간 | |
| 체감 지연 | 없음 / 살짝 / 거슬림 |
| 판정 | Hook 적합 / 부적합 |

---

## 실험 B: 컴파일 체크 (PR Hook / 태스크 완료 후보)

### 가설
UE 프로젝트 컴파일은 수십 초~수 분이므로 커밋 Hook에는 부적합.
PR 생성 전 최종 게이트 또는 태스크 완료 시점에 적합할 것.

### 실행

1. 프로젝트의 빌드 명령 확인:
```bash
# 예시 — 프로젝트에 맞게 수정
# UBT (Unreal Build Tool) 사용
UnrealBuildTool {Target} {Platform} Development

# 또는 UAT (Unreal Automation Tool)
RunUAT.sh BuildCookRun -project={.uproject 경로} -platform=Linux -build
```

2. 빌드 시간 측정 (변경 없이 incremental):
```bash
time {빌드 명령}
```

3. 빌드 시간 측정 (.cpp 1개 수정 후 incremental):
```bash
# 파일 하나 수정
time {빌드 명령}
```

### 기록

| 항목 | 값 |
|------|-----|
| incremental (변경 없음) | |
| incremental (.cpp 1개) | |
| 판정 | 커밋 Hook 적합 / PR Hook만 / 태스크 완료만 |

---

## 실험 C: UE Automation Test (참고용)

> 이번에는 "어떻게 걸 수 있는지"만 확인. 실제 적용은 추후.

### 확인 항목

1. **CLI에서 Automation Test 실행 방법**:
```bash
# 예시 — 프로젝트에 맞게 수정
{UE_Editor} {.uproject} -ExecCmds="Automation RunTests {TestName}" -game -unattended -nopause -log
```

2. **에디터 기동 없이 실행 가능한가?**
   - [ ] commandlet 모드 가능
   - [ ] 에디터 기동 필수 → Hook에 넣기 비현실적

3. **특정 테스트만 필터링 가능한가?**
   - [ ] 테스트 이름/태그 필터
   - [ ] 모듈 단위 필터

4. **소요 시간 (간단한 테스트 1개)**:
   - 에디터 기동: ___초
   - 테스트 실행: ___초
   - 합계: ___초

### 결론 템플릿

```
UE Automation Test 적용 방식:
  - [ ] PR Hook (빌드와 함께)
  - [ ] impl 마지막 단계 (integrator가 실행)
  - [ ] CI에서만 (Claude Code 워크플로우 밖)
```

---

## 종합 판단

실험 완료 후 아래 표를 채워서 Implementation Config 값을 확정:

| 체크 | 명령 | 실행 시점 | 비고 |
|------|------|----------|------|
| format_command | | 커밋 Hook | |
| build_command | | PR Hook / 태스크 완료 | |
| test_command | | PR Hook / 태스크 완료 | |
| UE Automation | | 추후 결정 | |
