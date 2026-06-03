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

## notes

workshop repo 내 수집된 지식 보관 디렉토리. 리서치, 아티클, 레퍼런스 자료 등을 주제별로 정리한다. `experiments/` 로 흘러가는 인풋 레이어.

## experiments

가설과 결과를 기록하는 실험 디렉토리. 검증 완료된 실험은 `templates/` 로 졸업한다. 재현 가능한 형태로 보관하여 후속 템플릿 설계의 근거가 된다.

## templates

검증 중인 프롬프트 템플릿 보관 디렉토리. 충분히 검증되면 `claude-config/` 로 졸업한다. `project-setup/` 하위에는 프로젝트 초기화용 스켈레톤이 위치한다.

## claude-config

배포 준비가 완료된 커맨드와 에이전트 보관 디렉토리. `deploy.sh` 를 실행하면 `~/.claude/` 에 동기화된다. 이 디렉토리를 편집 후 반드시 `./deploy.sh` 를 실행해야 실제 적용된다.

## references

분석 목적으로 git clone 한 플러그인 소스 보관 디렉토리. 내용은 일반 파일로만 존재하며 설치되거나 활성화된 것은 없다. hook 사용 패턴, 태스크 분해 패턴, 에이전트 정의, 컨텍스트 관리 전략 분석에 활용한다.

## sandbox

플러그인 격리 실험 디렉토리. 한 번에 하나의 플러그인만 설치하고, 분석 완료 후 반드시 uninstall 한다. hook 충돌 방지를 위해 복수 동시 설치는 금지한다.

## graduation flow

workshop repo 의 아티팩트 성숙 경로. `notes/ → experiments/ → templates/ → claude-config/ → ~/.claude/` 순서로 검증 단계를 거쳐 배포 준비 상태로 승격된다.

## preamble

`templates/workflow-contract/preamble.md` 에 정의된 글로벌 행동 규칙. spec-plan/impl 등 모든 커맨드 실행 전 prepend 되어 AI 행동의 공통 기반을 형성한다. §9 는 언어 순화 및 용어집 우선순위 규칙을 담는다.

## readiness check

태스크 시작 전 입력(티켓/프롬프트/PRD) 의 준비도를 진단하는 단계. 필수(must-have) / 산출예정(will-produce) / 이상(odd) 3등급으로 분류해 짧은 리포트를 출력한다. 입력 쪽 인지 바닥으로 기능한다.

## intent header

plan.md frontmatter 와 본문 상단에 기록하는 6필드 블록(Feature / Problem / Goal / Approach / Why / PRD). 무엇을·왜 만드는지를 게이트 출력 첫 화면에 노출하여 사람의 이해도를 높인다.

## gate event

spec-plan/impl 흐름에서 사람이 승인하는 지점. `gate_events:` frontmatter 슬롯에 게이트 번호, 결과(ok/abort), 대화 턴 수, 타임스탬프를 기록한다.

## skip_grill_count

pre-search grill 을 건너뛴 횟수를 기록하는 plan.md frontmatter 필드. grill 스킵 빈도를 추적해 입력 품질 패턴을 파악하는 데 사용한다.

## risk_acks

위험 영역(build-deploy / memory / network / concurrency 등) 에 대해 사람이 명시적으로 인지했음을 기록하는 frontmatter 슬롯. area, ack, ts 세 필드로 구성된다.

## plan_deviations

구현 중 plan.md 에서 벗어난 사항을 기록하는 result frontmatter 슬롯. 사후 검토 및 다음 태스크 핸드오프 시 컨텍스트로 활용된다.

## stale

DB나 캐시에 저장된 값이 최신본보다 오래된 상태. 예: 캐시가 갱신되지 않아 사용자가 폐기된(superseded) 데이터를 보는 상황. 오래된 값을 그대로 사용하면 논리 오류나 보안 취약점으로 이어질 수 있다.

## idempotent

같은 요청을 여러 번 보내도 결과가 동일한 연산. 예: HTTP PUT 요청이나 DB upsert 는 멱등(idempotent)으로 설계하는 것이 권장된다. 재시도(retry) 안전성을 보장하기 위해 중요한 속성이다.

## ad-hoc

특정 목적을 위해 임시방편으로 만들어진 것. 재사용이나 일반화를 고려하지 않은 일회성 해결책을 가리킨다. 반복적으로 등장하면 체계적인 설계로 대체하는 것이 바람직하다.

## eventual consistency

분산 시스템에서 일시적으로 노드 간 데이터 불일치가 허용되지만, 시간이 지나면 모든 노드가 동일한 값에 수렴하는 모델. 최종 일관성(eventual consistency) 모델에서는 읽기 직후 쓰기가 즉시 반영되지 않을 수 있다.
