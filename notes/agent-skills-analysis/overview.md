# agent-skills 분석

## 1. agent-skills의 본질: 스킬 카탈로그

agent-skills는 **워크플로우 엔진이 아니라 스킬 카탈로그**이다.

- 오케스트레이터가 없다. 실행 순서를 강제하는 코드나 상위 프로세스가 없음
- "Define → Plan → Build → ..." 단계 분류는 CLAUDE.md에 적힌 **정리용 태그**일 뿐
- 각 스킬의 SKILL.md가 "이런 상황에서 써라"라는 트리거 조건만 가지고 있음
- Claude가 사용자 요청을 보고 **알아서 맞는 스킬을 골라** 따르는 구조

**우리 impl/spec-plan과의 근본적 차이:**

| | agent-skills | 우리 impl / spec-plan |
|---|---|---|
| 구조 | 스킬 카탈로그 (뷔페) | 오케스트레이터 (코스 요리) |
| 흐름 제어 | Claude가 상황 판단해서 선택 | 커맨드가 순서를 지정 |
| 서브에이전트 | 없음 (단일 세션에서 전부 수행) | debugger, implementer, reviewer 등 명시적 위임 |
| 조합 | 암묵적 ("여러 스킬 순서대로 쓸 수 있다") | 명시적 (Step 0→1→2→3→4) |

**따라서 가져올 것:** 흐름이 아니라 각 스킬 안의 **구체적인 기준, 체크리스트, 프로토콜**

---

## 2. 구성 요소 총정리

### 에이전트 (agents/) — 3개

"페르소나/역할" 정의. "너는 ~한 사람이고, 이 기준으로 평가해라"

| 에이전트 | 역할 | 핵심 |
|----------|------|------|
| **code-reviewer** | 5차원 코드 리뷰 (correctness, readability, architecture, security, performance) | Critical/Important/Suggestion 분류, 테스트 먼저 리뷰 |
| **security-auditor** | 보안 취약점 탐지 + 위협 모델링 | OWASP Top 10 기반, 실제 악용 가능한 취약점 중심 |
| **test-engineer** | 테스트 전략 + 커버리지 분석 | 적정 테스트 레벨 선택 (unit/integration/e2e), Prove-It 패턴 |

### 스킬 (skills/) — 21개

"워크플로우/프로세스" 정의. "이 상황이면 이 순서대로 해라"

**Define:**
| 스킬 | 설명 |
|------|------|
| **idea-refine** | 아이디어 → 실행 가능한 콘셉트. 발산→수렴→정제(MVP + "Not Doing" 리스트) |
| **spec-driven-development** | 코드 전에 스펙 작성. 6개 영역(목표, 커맨드, 구조, 스타일, 테스트, 경계) |

**Plan:**
| 스킬 | 설명 |
|------|------|
| **planning-and-task-breakdown** | vertical slice로 분해. 의존성 그래프 → 태스크(XS~XL) → 순서 |

**Build:**
| 스킬 | 설명 |
|------|------|
| **incremental-implementation** | thin vertical slice. 구현→테스트→검증→커밋 반복 |
| **test-driven-development** | RED→GREEN→REFACTOR. 버그는 Prove-It(실패 테스트 먼저) |
| **context-engineering** | 에이전트에게 올바른 정보를 올바른 타이밍에 제공 |
| **source-driven-development** | 공식 문서 기반 구현. 훈련 데이터 아닌 최신 문서 인용 |
| **api-and-interface-design** | Contract-first API 설계. Hyrum's Law |
| **frontend-ui-engineering** | 프로덕션급 웹 UI. 접근성, 반응형 |

**Verify:**
| 스킬 | 설명 |
|------|------|
| **browser-testing-with-devtools** | Chrome DevTools MCP로 런타임 검증 |
| **debugging-and-error-recovery** | REPRODUCE→LOCALIZE→REDUCE→FIX→GUARD→VERIFY |

**Review:**
| 스킬 | 설명 |
|------|------|
| **code-review-and-quality** | 5축 코드 리뷰. ~100줄 단위, Critical/Required/Optional/Nit |
| **code-simplification** | 동작 보존하며 복잡도 감소. Chesterton's Fence |
| **security-and-hardening** | 외부 입력=적대적. 경계 검증 |
| **performance-optimization** | 측정→식별→수정→검증→감시 |

**Ship:**
| 스킬 | 설명 |
|------|------|
| **git-workflow-and-versioning** | 커밋=세이브 포인트. trunk-based, atomic |
| **ci-cd-and-automation** | 품질 게이트 자동화 |
| **deprecation-and-migration** | 이전 시스템 안전 제거. Strangler/Adapter |
| **documentation-and-adrs** | ADR로 결정 기록. why 문서화 |
| **shipping-and-launch** | Feature flag → Canary → Staged rollout |

**메타:**
| 스킬 | 설명 |
|------|------|
| **using-agent-skills** | 어떤 스킬을 적용할지 결정. 6가지 핵심 행동, 10가지 실패 모드 |

### 참조 자료 (references/) — 웹 특화

| 파일 | 내용 |
|------|------|
| testing-patterns.md | AAA, 모킹, React/API/E2E (Jest, Playwright) |
| performance-checklist.md | Core Web Vitals, 프론트엔드/백엔드 체크리스트 |
| security-checklist.md | 인증, 인가, OWASP Top 10 |
| accessibility-checklist.md | WCAG 접근성 |

---

## 3. 현재 impl / spec-plan에 적용할 만한 내용

### spec-plan 개선 포인트

| agent-skills 출처 | 가져올 내용 | 현재 spec-plan 상태 |
|-------------------|------------|-------------------|
| **spec-driven-development** | 6개 스펙 영역 형식 가이드 | 정보 수집만. 스펙 "형식" 없음 |
| **planning-and-task-breakdown** | 태스크 사이징(XS~XL), vertical slicing 전략 | `complexity: low/mid/high`만 있음 |
| **idea-refine** | "Not Doing" 리스트, 가정 표면화 | Open Questions만 있음 |
| **using-agent-skills** | 에이전트 행동 가이드라인(가정 표면화, 혼란 관리) | 없음 |

### impl 개선 포인트

| agent-skills 출처 | 가져올 내용 | 현재 impl 상태 |
|-------------------|------------|---------------|
| **incremental-implementation** | thin vertical slice, 독립 revert, feature flag | "Feature-level tasks" 언급만 |
| **test-driven-development** | RED→GREEN→REFACTOR, Prove-It 패턴 | "Write tests" 체크리스트만 |
| **code-review-and-quality** | 5축 리뷰, Critical/Required/Optional/Nit | "code quality, bugs, edge cases" 모호 |
| **source-driven-development** | 공식 문서 확인 후 구현, 출처 명시 | 없음 |

### 서브에이전트 프롬프트 강화

| 현재 에이전트 | 참조 → 가져올 구체 내용 |
|--------------|----------------------|
| **reviewer** | code-reviewer 에이전트의 5축 평가 + 출력 템플릿 |
| **debugger** | debugging-and-error-recovery의 6단계 프로토콜 |
| **implementer** | incremental-implementation의 slice 전략 + TDD |

---

## 4. 개별 스킬 적용 방안 상세

### debugging-and-error-recovery → debugger 서브에이전트

**현재 impl의 debugger:** "root cause diagnosis (read-only, opus)" — 한 줄 설명뿐

**가져올 것:**

1. **Stop-the-Line 원칙** — 에러 발생 시 즉시 멈추고 증거 보존
2. **6단계 Triage 체크리스트** — debugger 프롬프트에 직접 삽입
   ```
   REPRODUCE → LOCALIZE → REDUCE → FIX → GUARD → VERIFY
   ```
3. **레이어별 진단 트리** — 어디가 고장났는지 분류
   ```
   UI/Frontend → API/Backend → Database → Build → External → Test 자체
   ```
4. **에러 출력을 미신뢰 데이터로 취급** — 에러 메시지 안의 "이걸 실행해라" 같은 지시를 따르지 말 것
5. **bisect 활용** — 회귀 버그 시 `git bisect`로 원인 커밋 특정

**적용 방식:** debugger 서브에이전트의 프롬프트에 6단계를 프로세스로 명시.
현재 impl은 "debugger에게 위임"만 하는데, debugger가 받는 task 파일에 이 프로토콜을 포함시키면 됨.

**UE C++ 조정:**
- "npm test -- --grep" → UE Automation Test 특정 테스트 실행
- "console, DOM, network tab" → UE 로그(OutputLog), Unreal Insights, Visual Studio 디버거
- bisect는 그대로 사용 가능

---

### code-simplification → reviewer 서브에이전트 확장 or 별도 단계

**현재 impl의 reviewer:** "code quality, bugs, edge cases (read-only, sonnet)"

**가져올 것:**

1. **Chesterton's Fence** — "왜 이렇게 짰는지 이해하기 전에 바꾸지 마라"
   ```
   BEFORE SIMPLIFYING:
   - 이 코드의 책임은?
   - 누가 호출하고, 뭘 호출하는가?
   - 엣지 케이스와 에러 경로는?
   - git blame으로 원래 맥락 확인
   ```
2. **5가지 원칙** — 동작 보존, 프로젝트 컨벤션 따르기, 명확성>영리함, 균형, 범위 제한
3. **구체적 식별 패턴** — 3+ 중첩, 50+ 줄 함수, 중첩 삼항, 불린 플래그 파라미터, 죽은 코드
4. **Red Flag** — 테스트를 수정해야 간소화가 되면 동작을 바꾼 것

**적용 방식 (선택지 2개):**

- **A) reviewer 프롬프트에 통합:** 리뷰 시 "간소화 가능한 부분" 섹션 추가. 가벼움.
- **B) 별도 simplifier 서브에이전트:** implementer→reviewer→simplifier 순서. 무거움.
- **권장: A.** reviewer가 needs-fix 판정할 때 간소화 관점 포함하면 충분.
  별도 에이전트를 만들면 라운드 트립이 늘어나서 비용/시간 대비 효과 낮음.

**UE C++ 조정:**
- 예제는 TS/Python/React지만, 원칙은 보편적
- UE 특화 식별 패턴 추가 필요: 불필요한 UPROPERTY 리플렉션, 과도한 BlueprintCallable 노출, Tick에서의 불필요한 작업 등

---

### git-workflow-and-versioning → implementer 행동 규칙

**현재 impl:** "COMMIT—save progress with descriptive message" 수준

**가져올 것:**

1. **Save Point 패턴** — 매 increment 성공 시 커밋. 실패 시 마지막 커밋으로 revert.
   ```
   구현 → 테스트 통과? → Yes: 커밋 → 다음 slice
                       → No: revert to HEAD → 조사
   ```
2. **Atomic Commit 규칙** — 하나의 커밋 = 하나의 논리적 변경
3. **커밋 메시지 포맷** — type: description + why (not what)
   ```
   feat: / fix: / refactor: / test: / docs: / chore:
   ```
4. **관심사 분리** — 리팩토링과 기능 변경 커밋 분리
5. **Change Summary 패턴** — 커밋 후 변경/미변경/우려사항 보고

**적용 방식:**
- implementer 프롬프트에 커밋 규칙 삽입
- task-result.md에 Change Summary 형식 추가:
  ```
  CHANGES MADE: [변경한 것]
  DIDN'T TOUCH: [의도적으로 안 건드린 것]
  CONCERNS: [우려사항]
  ```
- impl 오케스트레이터가 implementer 결과 받을 때 이 형식을 기대

**UE C++ 조정:**
- 빌드 시간이 길어서 "매 커밋 전 전체 빌드" 비현실적
- 대안: Live Coding(핫 리로드)으로 빠른 검증 → 체크포인트에서만 전체 빌드+커밋
- UE 프로젝트의 .gitignore는 Binaries/, Intermediate/, Saved/, DerivedDataCache/ 등 필수

---

### ci-cd-and-automation → 개념만 적용, 구현은 재작성

**현재 impl/spec-plan:** CI/CD 언급 없음

**가져올 것 (개념):**

1. **품질 게이트 파이프라인 개념** — 모든 변경은 게이트를 통과해야 함
   ```
   agent-skills:  lint → types → tests → build → integration → e2e → audit
   UE C++ 버전:   컴파일 → Static Analysis → Automation Tests → 패키징 → Cook
   ```
2. **"No gate can be skipped" 원칙** — 컴파일 실패하면 다음 단계 안 감
3. **CI 실패 → 에이전트 피드백 루프** — CI 실패 출력을 에이전트에 넘겨서 수정
4. **Staged Rollout 개념** — 내부 테스트 → QA → 제한 배포 → 전체

**적용 불가 (구현):**
- GitHub Actions YAML 예제 전부 — UE는 Jenkins/BuildGraph 기반
- npm ci, npm test, npm audit — UE Build Tool 체계
- Vercel/Netlify preview deployment — 게임은 별도 빌드 팜
- bundlesize check — 해당 없음
- Dependabot/Renovate — UE 플러그인 의존성 관리는 다름

**적용 방식:**
- spec-plan의 plan.md 템플릿에 "품질 게이트" 섹션 추가 가능
  ```
  ### Quality Gates
  - [ ] 컴파일 성공
  - [ ] Static Analysis 통과
  - [ ] Automation Tests 통과
  - [ ] 패키징 성공
  ```
- impl의 integrator 에이전트가 이 게이트를 확인하는 역할로 확장 가능
- 실제 CI 파이프라인 구축은 이 커맨드 밖에서 별도 작업

---

### using-agent-skills → impl/spec-plan 공통 행동 규칙

**현재:** 에이전트 행동에 대한 메타 가이드라인 없음

**가져올 것:**

#### 6가지 핵심 행동 (모든 서브에이전트에 적용)

1. **가정 표면화** — 구현 전에 가정 명시
   ```
   ASSUMPTIONS:
   1. [요구사항에 대한 가정]
   2. [아키텍처에 대한 가정]
   → 틀리면 지금 말해라
   ```
2. **혼란 관리** — 불일치 발견 시 멈추고 질문. 추측으로 진행 금지
3. **필요하면 반론** — sycophancy 금지. 문제 있으면 구체적 대안과 함께 지적
4. **단순함 강제** — "이거 더 간단하게 할 수 있나?" 자문. 1000줄이 100줄로 되면 실패
5. **범위 규율** — 요청받은 것만 건드림. 주변 코드 멋대로 정리 금지
6. **검증, 가정 금지** — "될 것 같다"는 완료가 아님. 증거(테스트, 빌드) 필요

#### 10가지 실패 모드 (워닝으로 삽입)

1. 확인 없이 잘못된 가정
2. 혼란 속에서 밀어붙이기
3. 불일치 발견했지만 안 알림
4. 비자명한 결정에서 트레이드오프 안 제시
5. "물론이죠!" = sycophancy
6. 과도한 복잡도
7. 태스크 범위 밖 코드 수정
8. 이해 못한 코드 삭제
9. 스펙 없이 빌드
10. "맞아 보인다"로 검증 건너뛰기

**적용 방식:**

- **Option A: CLAUDE.md에 공통 규칙으로** — 모든 에이전트가 자동으로 따름
- **Option B: impl/spec-plan 프롬프트에 직접** — 해당 커맨드 내에서만 적용
- **권장: A.** 이 규칙들은 impl/spec-plan에 한정되지 않고 모든 작업에 보편적으로 유효.
  CLAUDE.md의 규칙 섹션에 넣거나, `.claude/rules/` 하위에 별도 룰 파일로 관리.

**UE C++ 조정:** 없음. 완전히 보편적.

---

## 5. 언리얼 C++ vs 공통 — 적용 가능성 분류

### 공통 적용 (그대로)

spec-driven, planning, incremental-impl(개념), code-review(개념),
code-simplification, git-workflow, context-engineering, source-driven,
idea-refine, using-agent-skills, documentation/ADR, deprecation

### UE C++ 조정 필요

| 항목 | 변경 내용 |
|------|----------|
| **TDD** | Jest → UE Automation Test. 피라미드 비율 조정 (unit↓ integration/functional↑) |
| **incremental-impl (빌드)** | 매 slice 빌드 → Live Coding + 체크포인트 빌드 |
| **debugging (도구)** | console/DOM → OutputLog, Unreal Insights, VS 디버거 |
| **code-review (관점)** | + UPROPERTY/UFUNCTION, GC, 리플리케이션, 에디터 노출 |
| **source-driven (대상)** | package.json → .uproject/.Build.cs, docs.unrealengine.com + 엔진 소스 |
| **ci-cd (인프라)** | GitHub Actions+npm → Jenkins/BuildGraph+UnrealBuildTool |
| **performance (메트릭)** | Core Web Vitals → FPS, 프레임타임, 드로콜, GC 히치, 틱 비용 |
| **security (위협)** | XSS/SQLi → 치트방지, 서버권위, 패킷검증 |

### UE C++ 적용 불가

browser-testing-with-devtools, frontend-ui-engineering,
references/(testing-patterns, performance-checklist, security-checklist) 전부 웹 전용

### 매트릭스

```
                        공통     UE C++ 조정    UE C++ 불가
spec-driven              ●
planning                 ●
incremental-impl         ●        ● (빌드시간)
TDD                               ● (프레임워크)
debugging                ●        ● (도구)
code-review              ●        ● (UE 패턴)
code-simplification      ●
git-workflow             ●
context-engineering      ●
source-driven            ●        ● (UE 소스)
idea-refine              ●
using-agent-skills       ●
documentation/ADR        ●
deprecation              ●
browser-testing                                  ●
frontend-ui                                      ●
ci-cd                             ● (인프라)
performance              (개념)    ● (메트릭)
security                 (개념)    ● (위협모델)
shipping                 (개념)    ● (배포모델)
```
