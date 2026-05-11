# Future Ideas — impl-workflow

> 상태: 미정/미흡수 아이디어 보관소 | 2026-05-07
> 본 문서는 plan.md에 채택되지 않은 아이디어를 잃지 않기 위한 보관소다. 채택되면 plan.md로 이동하고 여기서는 제거.

## plan.md Intentional Exclusions에서 옮겨온 항목

### Worktree per-phase 격리

각 phase를 별도 git worktree에서 격리 실행하면 부분 롤백이 쉬워진다.
- 현재 제외 사유: monorepo / submodule heavy 레포에서 worktree 미지원·제한이 흔해 일반화 비용이 이득보다 크다.
- 검토 트리거: 한 레포에서 두 phase를 병렬 진행하다 충돌이 반복되거나, 사용자가 phase 단위로 일부만 머지하는 패턴이 표준이 되면 재검토.

### `prompts/` 디렉토리 분리

auto-startup의 `prompts/task-create.md` 패턴처럼 task 발행용 프롬프트를 별도 디렉토리로 추출.
- 잠재 이점: `claude-config/commands/`가 비대해지지 않고, 헤드리스 러너가 동일 프롬프트를 재사용하기 쉬움.
- 현재 제외 사유: 추출 가치는 있으나 우선순위 낮음. 본 revamp의 task 자기완결 형식이 안정된 후 검토.

### Headless runner cache 최적화

헤드리스 Claude/Codex 러너의 prompt cache·토큰 비용 측정 후 최적화.
- 검토 트리거: Phase 5 runner 추상화가 안정된 후 비용 측정이 가능해지면 별도 phase로.

## 흡수되지 않은 audit / experiment loop 아이디어

> 출처: 아카이브된 `workflow-improvement-system-proposal.md`, `workflow-observability-audit-proposal.md`. plan.md의 Phase 5 status machine + 자기보고 검증은 이들 제안의 일부만 채택했다.

### Decision Records 표준 (agent-written)

implementer / reviewer / integrator가 의미있는 결정 시점에 짧은 Decision Record를 result 파일에 남긴다 (Decision / Evidence / Alternatives / Assumptions / Uncertainty / Validation / Next step).
- 현재 미채택: reviewer 표준화([p1]-[p4]+side effect)는 plan.md에 있지만 implementer/integrator의 decision record 강제는 없음.
- 검토 트리거: reviewer 핑퐁이 반복적으로 같은 결정을 다시 논의할 때 (재발 검출).

### `events.jsonl` 정규화 + `.claude/runs/{run-id}/audit.md`

raw 로그를 정규 이벤트 스트림으로 변환하고 워크플로 감사를 자동화.
- 현재 미채택: artifact 단위(`manifest.yaml`)까지는 plan.md가 정의하지만 정규 이벤트 / 메트릭 / deviations.json 까지는 범위 밖.
- 검토 트리거: 같은 회귀가 다른 task에서 반복되거나, Phase 8(role별 mixing) 후 비용·성공률 비교가 필요해질 때.

### `workflow-auditor` 에이전트

run 종료 후 spec(`commands/*.md`, `agents/*.md`)과 실제 trace를 비교해 spec deviation·missing decision·scope expansion을 검출.
- 현재 미채택: plan.md는 status machine 자기보고 검증만 채택.
- 검토 트리거: 사용자가 같은 종류의 회귀를 사람 눈으로 반복 검출하기 시작할 때.

### Improvement experiment template

prompt / hook / schema 변경을 가설→베이스라인→trial→메트릭→promotion 결정으로 형식화.
- 현재 미채택: 본 revamp는 plan.md 단위 일괄 변경. 점진적 가설검증 프로토콜은 별도 작업.
- 검토 트리거: prompt 변경이 효과 있는지 의심스러운 경우가 누적되거나, 두 가지 후보 prompt 중 선택해야 할 때.

### Hook 기반 soft/hard gate 단계적 도입

`Stop` / `SubagentStop` hook으로 missing result file, promised tests not run, scope expansion을 차단.
- 현재 미채택: plan.md는 자동 자기보고 검증만 (status가 진행중인 채 종료되면 error 강등).
- 검토 트리거: 자기보고 검증이 false negative로 새는 케이스가 쌓이면 단계적 hook 도입 검토.

## 기타 추출 아이디어

### `agentlens` spec-awareness 통합

`commands/`·`agents/` 정의를 ground truth로 두고 trace를 비교하는 evaluator. agentlens 분석은 별도 노트(`notes/agent-skills-analysis/agentlens-spec-awareness-proposal.md` 등) 참조.

### Provider-neutral 메트릭 비교

Claude transcript와 Codex jsonl을 동일 `events.jsonl` 스키마로 정규화해 러너 간 행동 비교. plan.md Phase 5의 artifact 계약에서 한 단계 더 나간 형태.

---

각 항목은 plan.md / experiments / templates 어디에서도 살아있는 작업이 아니다. 채택할 때 본 파일에서 제거하고 적절한 위치로 옮긴다.
