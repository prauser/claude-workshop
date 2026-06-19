# /wf-collect — 워크플로 텔레메트리 수집기

이 커맨드(command)는 `~/sbx-work/*` 아래에 있는 레포들의 워크플로 텔레메트리(telemetry)
(plan/result/manifest frontmatter + 세션로그 메타)를 수확(harvest)하고, 비식별(de-identification)
처리 후 번들(bundle)로 직렬화해 공유 레포에 업로드한다.

**핵심 속성**: 명시 실행만(opt-in only). 외부 설치 의존 0(stdlib만). 비식별 후 업로드.

## 파이프라인 스테이지

| 순서 | 스테이지 | 설명 | 구현 |
|------|---------|------|------|
| 1 | **discover** | `~/sbx-work/*` 디스커버리: `.claude/` 보유 레포 열거, 세션로그 slug 역매핑 | 구현: task-1 |
| 2 | **harvest-artifacts** | 각 레포 `.claude/{plans,tasks,runs}` frontmatter 수집. 드리프트(drift) 내성 방어적 파싱 | 구현: task-2 |
| 3 | **harvest-sessions** | 세션로그 메타 수집 → 평문(plain-text) 이벤트 스트림(tool/path/pattern/error/seq/tokens). vendored lean 파서 사용 | 구현: task-3 |
| 4 | **de-id** | 유저 raw 자연어 인풋(NL input) LLM 추상화(특성 보존·verbatim 제거) + secret 스캔 + 런타임 self-check hard-fail. LLM 추상화는 이 커맨드가 수행 | 구현: task-4 |
| 5 | **bundle** | 번들 직렬화(버전드 스키마) + git 업로드. `--dry-run` 시 업로드 없이 감사(audit)만 | 구현: task-5 |

## 사용법 (placeholder — task-5에서 확정)

```
/wf-collect
/wf-collect --dry-run
```

실행 예시(python3 직접 호출):

```bash
# 전체 파이프라인 (bundle까지)
python3 ~/.claude/templates/workflow-contract/runners/telemetry/collect.py discover

# 드라이런(dry-run) — 업로드 없이 번들 내용 확인 (task-5 이후)
python3 ~/.claude/templates/workflow-contract/runners/telemetry/collect.py --dry-run bundle

# 특정 티켓만
python3 ~/.claude/templates/workflow-contract/runners/telemetry/collect.py --ticket PRA-109 discover
```

## 주의사항

- 이 커맨드는 **명시 실행**만 한다. 자동/백그라운드/스케줄 트리거 없음.
- raw 로그는 머신 밖으로 반출하지 않는다. Tier-2 드릴다운(drill-down)은 로컬 raw에만 접근.
- 업로드 직전 런타임 self-check가 hard-fail하면 번들 전체가 업로드되지 않는다(전부-또는-전무).
- 비식별 대상: 유저 raw 자연어 인풋(`user_prompt` + 세션 유저 턴)만. 경로/코드/diff는 평문.
