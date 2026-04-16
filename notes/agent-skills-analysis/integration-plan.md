# agent-skills 통합 플랜 (최종)

## 설계 원칙

1. **공통 프로세스는 에이전트 프롬프트에 인라인** — 별도 guideline 파일 불필요
2. **환경 특화 내용만 프로젝트 .claude/guidelines/에** — 자동 로드 안 됨, task에 명시된 것만 읽음
3. **rules/에는 5~15줄 핵심만** — 항상 로드되니까 최소화
4. **오케스트레이터(impl, spec-plan)가 참조를 결정** — 서브에이전트가 스스로 고르지 않음
5. **AI용 압축** — 설명 산문, 코드 예제, 동기부여 제거. 단계/금지/체크리스트만

## 변경 파일 목록

### Phase 1: 에이전트 신규 생성 (3개)

| 파일 | 목적 | ~줄 수 |
|------|------|--------|
| `claude-config/agents/debugger.md` | 버그 진단. 6단계 프로토콜 인라인 (REPRODUCE→LOCALIZE→REDUCE→FIX→GUARD→VERIFY), 레이어 진단 트리, bisect, 에러 미신뢰 | ~50줄 |
| `claude-config/agents/implementer.md` | 구현+테스트. slice 순환, TDD RED→GREEN→REFACTOR, Save Point, atomic commit, Change Summary 전부 인라인 | ~70줄 |
| `claude-config/agents/test-engineer.md` | 테스트 전략/커버리지. 2모드: Strategy(spec-plan용) + Coverage(독립 호출용). 테스트 레벨 판단, 시나리오 매트릭스 | ~50줄 |

각 에이전트에 공통 행동 규칙 5줄 인라인:
```
- 가정 있으면 명시하고 확인
- 혼란 시 멈추고 질문. 추측 진행 금지
- 범위 밖 수정 금지
- 검증 없이 완료 선언 금지 (증거 필요)
- 단순한 해법 우선
```

### Phase 2: 기존 에이전트 강화 (2개)

| 파일 | 변경 내용 | ~줄 수 |
|------|----------|--------|
| `claude-config/agents/reviewer.md` | 5축 리뷰(correctness/readability/architecture/security/performance) 인라인, 3단계 심각도(Critical/Important/Suggestion), Chesterton's Fence, "테스트 먼저 리뷰" | ~50줄 |
| `claude-config/agents/integrator.md` | 품질 게이트 개념 추가. 게이트 목록은 task 파일에서 받음. 출력에 gate pass/fail | ~35줄 |

### Phase 3: 커맨드 수정 (2개)

**`claude-config/commands/spec-plan.md` 변경:**
- Step 0에 **[Test Agent]** 추가 (5번째 병렬 에이전트)
  - test-engineer를 strategy 모드로 호출
  - 결과: 테스트 접근법, 레벨별 타겟, 리스크 영역
- plan 템플릿 확장:
  - `### Out of Scope` 섹션 추가 (명시적 "하지 않을 것" 리스트)
  - 태스크 사이징 `low/mid/high` → `XS/S/M/L/XL`
    ```
    XS: 파일 1개 | S: 2-3개 | M: 모듈 수준 | L: 크로스모듈 | XL: 분할 필요
    ```
  - `### Test Strategy` 섹션 (Test Agent 결과 반영)
  - `### Quality Gates` 섹션 (프로젝트 config에서 읽거나 기본값)
- Cross-review에 Type D 추가: Test vs Code 충돌

**`claude-config/commands/impl.md` 변경:**
- task 파일 템플릿에 `## Reference Guidelines` 섹션 추가
  - 오케스트레이터가 CLAUDE.md의 `guidelines:` 목록을 읽어서 삽입
  - 환경 특화 파일만 여기에 들어감 (공통 프로세스는 에이전트에 인라인이니까)
  ```markdown
  ## Reference Guidelines
  - .claude/guidelines/ue-conventions.md
  - .claude/guidelines/ue-performance.md
  ```
- Agents 섹션 업데이트:
  - debugger: "6단계 triage 프로토콜 (read-only, opus)"
  - implementer: "incremental slice + TDD + atomic commits (sonnet)"
  - test-engineer 추가: "테스트 전략/커버리지 분석 (read-only, sonnet)"
- integrator에 Quality Gates 전달 (plan.md에서 가져옴)

### Phase 4: deploy.sh 수정

현재 commands/ + agents/만 배포.
- integrator.md가 agents/에 없으면 추가 대상
- guidelines/는 프로젝트별이라 deploy 대상 아님 (공통 guideline 파일 없음)

### Phase 5: 프로젝트 템플릿 (templates/)

| 파일 | 내용 |
|------|------|
| `templates/project-setup/rules/core.md` | 프로젝트에 복사할 핵심 규칙 (~10줄) |
| `templates/project-setup/guidelines-ue-cpp/ue-conventions.md` | UPROPERTY, GC, F/U/A 네이밍, 리플리케이션 (~25줄) |
| `templates/project-setup/guidelines-ue-cpp/ue-testing.md` | UE Automation Test, Live Coding 검증 (~20줄) |
| `templates/project-setup/guidelines-ue-cpp/ue-performance.md` | 프레임타임, 드로콜, GC 히치, Stat 명령어 (~20줄) |
| `templates/project-setup/CLAUDE-ue-example.md` | UE 프로젝트 CLAUDE.md 예시 (Implementation Config + guidelines 경로) |

## 전체 로드 구조

```
에이전트 호출 시 로드되는 것:

  agents/implementer.md (~70줄)     ← 공통 프로세스 인라인
  + CLAUDE.md (~15줄)               ← 프로젝트 기본정보 (항상 로드)
  + rules/core.md (~10줄)           ← 핵심 규칙 (항상 로드)
  + task 파일 (~30줄)               ← 목표, 컨텍스트, Reference Guidelines
  + ue-conventions.md (~25줄)       ← task에 명시된 것만 (환경 특화)
  ─────────────────────────────
  합계: ~150줄 (에이전트당)
```

## 참조 흐름 (최종)

```
/spec-plan TASK-123
  │
  ├─ [Jira Agent]       ─┐
  ├─ [Spec Agent]        ─┤
  ├─ [Code Agent]        ─┤ 병렬
  ├─ [Context Agent]     ─┤
  └─ [Test Agent] ★      ─┘  test-engineer (strategy 모드)
  │
  ▼ plan.md 생성
    - Requirements (P0/P1)
    - Out of Scope ★
    - Impact scope
    - Task breakdown (XS~XL 사이징) ★
    - Test Strategy ★
    - Quality Gates ★
    - Open questions

/impl TASK-123
  │
  ├─ plan.md 로드
  ├─ CLAUDE.md에서 guidelines: 경로 읽음
  │
  ├─ 버그? → debugger (프로토콜 인라인)
  │
  ├─ 구현 → task 파일 생성 (Reference Guidelines 포함)
  │        → implementer (프로세스 인라인 + 환경 특화 파일 참조)
  │        → reviewer (리뷰 기준 인라인 + 환경 특화 파일 참조)
  │        → 반복 (max 3)
  │
  └─ 통합 → integrator (Quality Gates from plan.md)

독립 호출:
  @test-engineer → coverage 모드 (impl 후 커버리지 분석)
```

## 프로젝트 CLAUDE.md 예시 (UE C++)

```markdown
# MyGame

UE 5.5 기반 액션 게임.

## Build
- 빌드: UnrealBuildTool
- 에디터 실행: UnrealEditor.exe MyGame.uproject
- Live Coding: Ctrl+Alt+F11

## Implementation Config
specs_path: Docs/Specs
prd_path: Docs/PRD
guidelines:
  - .claude/guidelines/ue-conventions.md
  - .claude/guidelines/ue-testing.md
  - .claude/guidelines/ue-performance.md

## Quality Gates
- [ ] 컴파일 성공 (Development Editor)
- [ ] Static Analysis 통과
- [ ] Automation Tests 통과
- [ ] Cook 성공 (Win64)
```

## 프로젝트 .claude/ 구조

```
{프로젝트}/
  CLAUDE.md                        ← ~20줄 (항상 로드)
  .claude/
    rules/
      core.md                      ← ~10줄 (항상 로드)
    guidelines/                    ← 자동 로드 안 됨
      ue-conventions.md            ← task에 명시될 때만 읽힘
      ue-testing.md
      ue-performance.md
```

## 실행 순서

| 순서 | Phase | 파일 수 | 내용 |
|------|-------|--------|------|
| 1 | 에이전트 신규 | 3개 | debugger, implementer, test-engineer |
| 2 | 에이전트 강화 | 2개 | reviewer, integrator |
| 3 | 커맨드 수정 | 2개 | spec-plan, impl |
| 4 | deploy.sh | 1개 | 필요 시 |
| 5 | 템플릿 | 5개 | rules/core, UE guidelines, CLAUDE 예시 |

총 ~13개 파일. Phase 1-2는 병렬 가능.

## 이전 분석 참조

- 전체 분석: `notes/agent-skills-analysis/overview.md`
- 번역본: `notes/agent-skills-analysis/translations/`
