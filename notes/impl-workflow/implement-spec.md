# /implement 커맨드 스펙

> 상위 문서: [design.md](design.md)
> graduation 대상: `claude-config/commands/implement.md`

## 개요

```
트리거: /implement {TICKET}
예시:   /implement OVDR-1234

입력: Jira 티켓 번호
출력: 확정된 플랜 → /orchestrate 자동 호출
```

---

## 전제 조건

- 프로젝트 CLAUDE.md에 `## Implementation Config` 섹션 존재
- MCP 서버 접근 가능: jira-tools (Jira 읽기), context-master (전사 지식)
- .claude/tasks/ 디렉토리 존재 (orchestrate가 사용)

---

## 커맨드 동작

### On activation

1. 티켓 번호 파싱
2. CLAUDE.md에서 Implementation Config 읽기
3. Step 0~4 순차 실행

### Step 0 — 컨텍스트 수집 (서브에이전트 4개 병렬)

```
메인 스레드:
  spawn 4 subagents in parallel:

  [Jira Agent]
    MCP(jira-tools)로 티켓 읽기
    수집: 상세, 수락 기준, 관련 이슈, 에픽 컨텍스트, 코멘트
    반환: 요구사항 요약

  [Spec Agent]
    Implementation Config의 prd_path, specs_path, policies_path에서 탐색
    Grep으로 기능명 키워드 검색 → 매칭 문서 Read
    반환: 구현 요구사항 목록, 우선순위, 미결 사항

  [Code Agent]
    현재 레포에서 영향 범위 분석
    Grep/Read로 관련 파일, 의존성, 기존 테스트 파악
    반환: 영향 파일, 의존성 맵, 리스크 영역, 테스트 커버리지

  [Context Agent]
    MCP(context-master)로 관련 지식 조회
    Implementation Config의 log_repo에서 과거 유사 작업 로그 탐색
    반환: 관련 지식, 과거 학습 사항
```

에이전트 모델: Code Agent만 opus (추론 난이도 높음), 나머지 sonnet.
에이전트 도구: 모두 읽기 전용 (Write/Edit 없음).

### Step 1 — 플랜 초안 생성

메인 스레드가 4개 결과를 합성:

```markdown
## 플랜 — {TICKET}: {기능명}

### 요구사항
- P0: [항목들]
- P1: [항목들]

### 영향 범위
- 수정 파일: [목록]
- 의존성: [모듈]
- 리스크: [영역]

### 태스크 분해
1. {태스크} — 복잡도: {low/mid/high}, 의존: {없음 또는 태스크 N}
2. ...

### 테스트 전략
- 단위: [대상]
- 통합: [대상]

### 미결 사항
- [결정 필요한 것들]
```

### Step 2 — 핑퐁 리뷰 (1회 하드리밋)

충돌 탐지:

| 유형 | 에이전트 쌍 | 탐지 조건 |
|------|-----------|----------|
| A | Code ↔ Spec | Code "어려움/리스크" vs Spec "P0 필수" |
| B | Code ↔ Code(테스트) | 수정 순서 vs 기존 테스트 영향 |
| C | Jira(일정) ↔ Code(선행작업) | 마감 vs 선행 리팩토링 필요 |

충돌 발견 시:
```
해당 에이전트 쌍에 상대 결과 전달 → 재분석 1회
  → 수렴: 플랜 업데이트
  → 미수렴: 양쪽 의견 병기 → Step 3에서 사용자 결정
```

충돌 없으면: Step 3으로.

### Step 3 — Human-in-the-Loop

사용자에게 플랜 핵심만 제시:

```
"{TICKET} 플랜:

태스크 {N}개:
  1. {태스크} — {복잡도}
  2. {태스크} — {복잡도} ← 리스크
  ...

불확실한 점:
  - {미수렴 항목 또는 미결 사항}

이대로 진행할까?"
```

사용자 피드백:
- 수정 → 플랜 업데이트 → 재확인
- "더 조사해봐" → 해당 에이전트 재스폰
- "OK" → Step 4

### Step 4 — orchestrate 위임

1. 플랜을 orchestrate 스펙 형식으로 변환 (bullet points)
2. 플랜을 파일로 저장: `{log_repo}/{repo_name}/{TICKET}/plan.md`
3. `/orchestrate` 자동 호출
4. orchestrate가 태스크 파일 생성 후 사용자 최종 승인 → 실행

---

## orchestrate 연동

implement는 orchestrate의 "On implementation request" 흐름을 트리거한다.
implement가 만든 스펙을 orchestrate가 받아서 태스크 분해 → 실행.

```
implement: "이 스펙으로 구현해줘"
orchestrate: "태스크 3개로 분해했어. 승인?"
사용자: "OK"
orchestrate: implementer → reviewer → integrator → 완료
```

implement는 orchestrate 실행 중에는 개입하지 않는다.
orchestrate 완료 후 Hook이 로그 동기화.

---

## 프로젝트별 Implementation Config

각 코드 레포의 CLAUDE.md에 추가하는 섹션:

```markdown
## Implementation Config

| 항목 | 값 |
|------|-----|
| specs_path | ../studio-docs/output/specs/ |
| prd_path | ../studio-docs/output/prd/ |
| policies_path | ../studio-docs/policies/ |
| test_command | (레포별 테스트 실행 명령) |
| lint_command | (레포별 린트 명령) |
| log_repo | ../impl-logs |
```

`/implement`는 이 테이블을 파싱하여 경로를 결정한다.
Config가 없으면: 경로 관련 에이전트(Spec, Context)를 생략하고 Jira + Code만 실행.

---

## 에러 처리

| 상황 | 대응 |
|------|------|
| Jira MCP 불가 | 사용자에게 티켓 정보 직접 입력 요청 |
| PRD/TechSpec 없음 | Spec Agent 생략, Code + Jira만으로 플래닝 |
| 충돌 미수렴 | 양쪽 의견 병기, 사용자 결정 요청 |
| 사용자 "취소" | 플랜 파일 저장하지 않고 종료 |
