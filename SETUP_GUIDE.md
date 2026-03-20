# Claude Code 워크플로우 세팅 가이드

## 전체 디렉토리 구조

```
~/.claude/                        # 유저 레벨 — 모든 레포에 공통 적용
  commands/
    orchestrate.md                # /orchestrate 커맨드
    review.md                     # /review 커맨드 (예정)
    design.md                     # /design 커맨드 (예정)
    brainstorm.md                 # /brainstorm 커맨드 (예정)
  agents/
    implementer.md                # 구현 + 유닛테스트 (model: sonnet)
    reviewer.md                   # 코드 리뷰 (model: sonnet)
    integrator.md                 # 통합 테스트 (model: sonnet)

~/claude-workshop/                # 분석 & 실험 전용 — 실제 프로젝트와 완전 분리
  references/                     # 플러그인 소스 클론 (읽기 전용 분석)
    get-shit-done/
    superpowers/
    barkain-workflow/
    wshobson-agents/
  sandbox/                        # 실제 설치 테스트가 필요할 때만 사용 후 제거

~/your-project-A/                 # 실제 프로젝트 레포
  .claude/
    tasks/
      pending/
      done/
      failed/

~/your-project-B/
  .claude/
    tasks/
      ...
```

---

## 레이어 분리 원칙

| 레이어 | 위치 | 내용 | 적용 범위 |
|--------|------|------|-----------|
| 유저 레벨 | `~/.claude/` | 워크플로우 커맨드, 공통 에이전트 | 모든 레포 |
| 프로젝트 레벨 | `./.claude/` | tasks/ 실행 상태 | 해당 레포만 |
| 분석 전용 | `~/claude-workshop/` | 참고 소스, 실험 | 분리된 환경 |

**핵심 규칙**
- 커맨드(`/orchestrate` 등)는 유저 레벨에서 관리 → 모든 레포에서 바로 사용 가능
- 실행 상태(`tasks/`)는 프로젝트 레벨 → 레포마다 독립
- 플러그인 분석은 `claude-workshop/references/`에서 클론만 받아서 읽기 → 설치 없이 안전하게 분석
- 실제 동작 확인이 꼭 필요하면 `claude-workshop/sandbox/`에서만 설치하고 분석 후 제거

---

## 초기 세팅

### 1. claude-workshop 세팅 및 배포

`claude-workshop/claude-config/` 가 커맨드/에이전트의 소스 오브 트루스다.
수정은 여기서 하고 `deploy.sh` 로 `~/.claude/` 에 배포한다.

```bash
# 초기 배포
cd ~/claude-workshop
./deploy.sh
```

### 2. 프로젝트 레벨 tasks 디렉토리 생성

```bash
# 각 프로젝트 레포에서 실행
cd ~/your-project
mkdir -p .claude/tasks/pending
mkdir -p .claude/tasks/done
mkdir -p .claude/tasks/failed
```

### 3. claude-workshop 세팅

```bash
mkdir -p ~/claude-workshop/references
mkdir -p ~/claude-workshop/sandbox

# 참고할 플러그인 소스 클론 (설치 X, 읽기용)
cd ~/claude-workshop/references
git clone https://github.com/gsd-build/get-shit-done
git clone https://github.com/obra/superpowers
git clone https://github.com/barkain/claude-code-workflow-orchestration
git clone https://github.com/wshobson/agents
```

---

## 사용법

### 일반 워크플로우

```bash
# 실제 프로젝트에서 Claude Code 시작
cd ~/your-project
claude

# 스펙 대화 충분히 한 후
> /orchestrate

# 이후 구현 요청하면 자동으로:
# 태스크 분해 → 승인 → 서브에이전트 실행 → 결과 보고
```

### 플러그인 분석 워크플로우

```bash
# claude-workshop에서 세션 시작 (플러그인 미설치 상태)
cd ~/claude-workshop
claude

# 소스 읽어서 분석 요청
> references/get-shit-done/ 읽고
  1. hook 사용 방식
  2. 태스크 분해 패턴이 우리 orchestrate.md랑 뭐가 다른지
  3. 가져올 만한 패턴
  분석해줘
```

### sandbox 사용 (실제 동작 확인이 필요할 때)

```bash
cd ~/claude-workshop/sandbox
claude plugin install gsd@gsd-plugins   # 분석 목적으로만 설치
claude

# 분석 후 반드시 제거
claude plugin uninstall gsd@gsd-plugins
```

---

## 커맨드 로드맵

| 커맨드 | 상태 | 설명 |
|--------|------|------|
| `/orchestrate` | ✅ 완성 | 스펙 대화 → 태스크 분해 → 서브에이전트 실행 → 결과 보고 |
| `/review` | 🔜 다음 | 세션 회고 — 태스크 분해 적절성, 테스트 커버리지, 워크플로우 개선점 |
| `/design` | 📋 예정 | TechSpec 작성 에이전트 |
| `/brainstorm` | 📋 예정 | PRD 작성 에이전트 (스펙 논의 자동화) |

### 최종 목표 파이프라인

```
요구사항
    ↓
/brainstorm    → PM 에이전트 (브레인스토밍 + PRD)
    ↓ 승인
/design        → Architect 에이전트 (TechSpec + 설계)
    ↓ 승인
/orchestrate   → 오케스트레이터 (구현 + 테스트 이터레이션)
    ↓
/review        → QA 에이전트 (최종 테스트 + 개선점)
```

사람은 각 단계 사이 게이트에서만 개입.

---

## 참고 프로젝트

개선이 필요한 시점에 `claude-workshop/references/`에서 해당 소스를 읽고 패턴만 가져온다.

| 레포 | 참고 시점 | 핵심 패턴 |
|------|-----------|-----------|
| `barkain/claude-code-workflow-orchestration` | orchestrate 개선 시 | hook 기반 자동 분해, 병렬/순차 선택 로직 |
| `gsd-build/get-shit-done` | context rot 문제 생길 시 | 태스크당 신선한 컨텍스트, atomic commit |
| `obra/superpowers` | review 만들 때 | TDD 강제, 4단계 디버깅 방법론 |
| `wshobson/agents` | brainstorm/design 만들 때 | PRD → 구현 전체 파이프라인 커맨드 |
| `VoltAgent/awesome-claude-code-subagents` | 에이전트 역할 분리 시 | 역할별 서브에이전트 정의 카탈로그 |
| `ruvnet/ruflo` | 대규모 확장 시 | 풀스택 오케스트레이션, self-learning |

---

## 주의사항

- 플러그인은 **설치해야만** hook/커맨드가 활성화됨. 디렉토리에 파일만 있는 건 무해함
- 여러 플러그인을 유저 레벨에 동시 설치하면 hook 충돌 가능성 있음 → 분석용은 반드시 sandbox에서만
- `tasks/` 디렉토리는 `.gitignore`에 추가 권장 (실행 상태는 레포에 커밋하지 않음)
