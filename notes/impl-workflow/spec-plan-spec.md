# /spec-plan 커맨드 스펙

> 상위 문서: [design.md](design.md)
> graduation 대상: `claude-config/commands/spec-plan.md`

## 개요

```
/spec-plan {TICKET}
입력: Jira 티켓 번호
출력: plan.md 저장 → 사용자가 /impl 수동 호출
```

---

## 전제 조건

- CLAUDE.md에 `## Implementation Config` (없으면 Jira + Code만)
- `jira-tools` CLI 설치됨
- `.claude/tasks/` 디렉토리 존재

---

## Step 0 — 컨텍스트 수집 (서브에이전트 4개 병렬)

| 에이전트 | 모델 | 소스 | 반환 |
|----------|------|------|------|
| Jira | sonnet | `jira-tools get {TICKET}` | 요구사항 요약 |
| Spec | sonnet | prd_path, specs_path, policies_path | 구현 요구사항, 우선순위 |
| Code | opus | 현재 레포 Grep/Read | 영향 파일, 의존성, 리스크 |
| Context | sonnet | log_repo 과거 로그 | 관련 지식, 학습 사항 |

Config 없으면 Spec, Context 생략. jira-tools 실패 시 사용자에게 티켓 정보 직접 입력 요청.

## Step 1 — 플랜 초안

4개 결과를 합성: 요구사항(P0/P1), 영향 범위, 태스크 분해, 테스트 전략, 미결 사항.

## Step 2 — 핑퐁 리뷰 (3회 하드리밋)

충돌 유형:
- Code vs Spec: "리스크" vs "P0 필수"
- Code vs Tests: 수정 순서 vs 테스트 영향
- Jira(일정) vs Code(선행작업)

충돌 시 상대 결과 전달 → 재분석. 3회 미수렴 → 양쪽 의견 병기.

## Step 3 — Human-in-the-Loop

플랜 핵심 제시 → 사용자 피드백:
- 수정 → 플랜 업데이트 → 재확인
- "더 조사해봐" → 해당 에이전트 재스폰
- "OK" → Step 4
- "취소" → 저장 없이 종료

## Step 4 — 플랜 저장

1. `{log_repo}/{repo_name}/{TICKET}/plan.md`에 저장. 기존 파일 있으면 `plan-v{N}.md`.
2. 안내: "플랜 저장 완료. `/impl {TICKET}`으로 구현 시작."
3. 종료. 구현 트리거하지 않음.

---

## impl 연동

```
spec-plan: plan.md 저장 → 종료
사용자: /impl OVDR-1234
impl: plan.md 읽기 → 태스크 분해 → 실행
```

사용자의 명시적 행위로 연결. 플랜 수정/중단의 브레이크 포인트.

---

## Implementation Config

CLAUDE.md에 추가하는 섹션:

| 항목 | 용도 |
|------|------|
| specs_path | TechSpec 경로 |
| prd_path | PRD 경로 |
| policies_path | 정책 문서 경로 |
| format_command | 커밋 Hook용 포맷터 |
| build_command | PR Hook용 빌드 |
| test_command | PR Hook용 테스트 |
| log_repo | impl-logs 경로 |
