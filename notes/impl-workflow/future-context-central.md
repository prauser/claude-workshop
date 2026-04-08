# 향후 작업: context-central 연동

> 상태: 아이디어 | 2026-04-08

## 개요

중앙 지식관리 Agent(`context-central`)에게 컨텍스트를 질의하는 방식으로,
개별 소스(Jira, Slack 등)를 직접 조회하지 않게 한다.

## 현재 → 향후

```
현재:
  /spec-plan → Jira Agent (jira-tools CLI 직접 호출)
            → Spec Agent (PRD/TechSpec 파일 직접 탐색)
            → Context Agent (impl-logs 직접 탐색)

향후:
  /spec-plan → context-central에 질의
            → 통합된 컨텍스트 수신 (Jira, Slack, 문서, 로그 등)
            → Code Agent만 레포 직접 분석
```

## 영향 범위

- `spec-plan.md`: Jira/Spec/Context Agent 3개 → context-central 1개로 통합 가능
- `hooks-spec.md`: 변경 없음
- `impl.md`: 변경 없음 (plan.md만 받으면 됨)

## 선행 조건

- context-central Agent 정의 및 구현
- 지식 수집 파이프라인 (Jira, Slack, Confluence 등 → context-central)
- 질의 인터페이스 확정 (MCP? CLI? API?)
