---
version: 1
updated_at: 2026-06-04
---

# Glossary

## 사용 안내

이 파일은 spec-plan/impl 시작 시 AI가 읽는다. 도메인 용어를 등록하면 게이트 출력에서 자동 풀이가 적용된다.

파일 위치는 `CLAUDE.md` `## Implementation Config` 섹션의 `glossary_path:` 키로 지정한다 (기본값: `docs/glossary.md`).

---

## 편집 가이드

새 term 추가 시: 영어 heading(`## term`) + 한글 풀이 한 단락 + (선택) 코드 위치 링크.

한글 term이 꼭 필요하면 `## 한글표기 (english)` 형태로 영어 alias를 괄호 안에 넣어 anchor를 영어로 유지한다.

---

## stale

DB나 캐시에 저장된 값이 최신본보다 오래된 상태. 예: 캐시가 갱신되지 않아 사용자가 폐기된(superseded) 데이터를 보는 상황. 오래된 값을 그대로 사용하면 논리 오류나 보안 취약점으로 이어질 수 있다.

## idempotent

같은 요청을 여러 번 보내도 결과가 동일한 연산. 예: HTTP PUT 요청이나 DB upsert 는 멱등(idempotent)으로 설계하는 것이 권장된다. 재시도(retry) 안전성을 보장하기 위해 중요한 속성이다.

## eventual consistency

분산 시스템에서 일시적으로 노드 간 데이터 불일치가 허용되지만, 시간이 지나면 모든 노드가 동일한 값에 수렴하는 모델. 최종 일관성(eventual consistency) 모델에서는 읽기 직후 쓰기가 즉시 반영되지 않을 수 있다.

## idempotency key

클라이언트가 중복 요청을 방지하기 위해 요청마다 붙이는 고유 식별자. 서버는 이 키를 보고 동일 요청을 한 번만 처리했다고 판단한다.

## backoff

재시도 간격을 점진적으로 늘리는 전략. 보통 지수 함수적으로 대기 시간을 증가시켜 서버 과부하를 방지한다. 예: 1초 → 2초 → 4초 → 8초.
