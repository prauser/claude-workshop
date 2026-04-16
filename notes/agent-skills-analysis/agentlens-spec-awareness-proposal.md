# agentlens: 워크플로우 명세 인식 기능 제안

> agentlens가 배포된 commands/*.md, agents/*.md를 읽어서
> "의���한 동작"과 "실제 세션"을 비교 분석하는 기능.

---

## 배경

현재 agentlens의 분석은 **세션 로그만 보고** 비효율을 탐지한다.
워크플로우가 "어떻게 동작해야 하는지"(commands/*.md, agents/*.md)는 모른다.

```
현재:   세션 JSONL → 패턴 매칭 → findings
원하는: 세션 JSONL + 워크플로우 명세 → "의도 vs 실제" 비교 → findings
```

이게 되면:
- 에이전트가 프롬프트에 적힌 단계를 건너뛰었는지 탐지
- 새 에이전트/커맨드 추가 시 agentlens 코드 수정 불필요
- `skill-suggestion` finding이 실제 명세 기반으로 구체화됨

---

## 제안 기능 (2단계)

### Level 1: 워크플로우 자동 발견

**현재 문제:** WORKFLOW_AGENTS가 하드코딩되어 있음.

```python
# analyze.py:27
DEFAULT_WORKFLOW_AGENTS = {
    "impl": {"implementer", "reviewer", "integrator", "debugger", "analyzer"},
    "spec-plan": {"jira-agent", "spec-agent", "code-agent", "context-agent"},
}
```

에이전트를 추가/변경할 때마다 이 매핑을 수동 업데이트해야 함.

**제안:** `~/.claude/commands/*.md`와 `~/.claude/agents/*.md`를 읽어서 자동 구성.

```python
def discover_workflows(claude_dir: Path = Path.home() / ".claude") -> dict[str, set[str]]:
    """commands/*.md를 파싱하여 워크플로우 → 에이전트 매핑을 자동 생성."""
    workflows = {}
    
    commands_dir = claude_dir / "commands"
    agents_dir = claude_dir / "agents"
    
    if not commands_dir.exists():
        return DEFAULT_WORKFLOW_AGENTS  # fallback
    
    for cmd_file in commands_dir.glob("*.md"):
        workflow_name = cmd_file.stem  # impl, spec-plan, ...
        content = cmd_file.read_text()
        
        # agents/*.md에 있는 에이전트 이름과 매칭
        known_agents = set()
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                agent_name = agent_file.stem
                # command 내용에서 에이전트 이름이 언급되면 포함
                if agent_name in content or agent_name.replace("-", "_") in content:
                    known_agents.add(agent_name)
        
        if known_agents:
            workflows[workflow_name] = known_agents
    
    return workflows or DEFAULT_WORKFLOW_AGENTS
```

**영향 범위:**
- `analyze.py`: `WORKFLOW_AGENTS`를 함수 호출로 교체
- `cli.py`: `--mode` 선택지를 동적으로 생성 (발견된 워크플로우 기반)
- 하위 호환: commands가 없으면 `DEFAULT_WORKFLOW_AGENTS` fallback

**테스트:**
- fixture로 임시 commands/agents 디렉토리 → 매핑 자동 생성 확인
- 기존 DEFAULT와 동일한 결과가 나오는 호환성 테스트

---

### Level 2: 명세 기반 LLM 분석

**현재:** LLM 분석이 세션 내용만 보고 7축으로 평가.

**제안:** commands/*.md + agents/*.md 내용을 LLM 컨텍스트에 주입하여 "명세 대비 실제" 비교.

#### 2-1. 명세 로딩

```python
def load_workflow_specs(claude_dir: Path = Path.home() / ".claude") -> str:
    """commands/*.md + agents/*.md를 읽어서 LLM 컨텍스트용 문자열로 반환."""
    sections = []
    
    for subdir in ("commands", "agents"):
        dir_path = claude_dir / subdir
        if not dir_path.exists():
            continue
        for md_file in sorted(dir_path.glob("*.md")):
            content = md_file.read_text().strip()
            if content:
                sections.append(f"### {subdir}/{md_file.name}\n\n{content}")
    
    if not sections:
        return ""
    
    return "## 워크플로우 명세 (배포된 commands + agents)\n\n" + "\n\n---\n\n".join(sections)
```

#### 2-2. ANALYSIS_PROMPT 확장

기존 7축에 1축 추가:

```
8. **spec-deviation**: 워크플로우 명세(commands/*.md, agents/*.md)에 정의된 
   단계/규칙/출력 형식을 건너뛰거나 위반한 경우.
   
   판단 기준:
   - 커맨드에 정의된 단계(Step 0, Step 1, ...)가 실제로 수행되었는가
   - 에이전트 프롬프트에 명시된 프로세스를 따랐는가
   - 에이전트 프롬프트에 명시된 출력 형식이 지켜졌는가
   - "금지" 규칙이 위반되지 않았는가
   - Reference Guidelines가 task 파일에 포함되었는가 (impl의 경우)
   
   예시:
   - implementer가 Change Summary를 출력하지 않았다
   - reviewer가 5축 중 security를 체크하지 않았다
   - debugger가 REPRODUCE 단계 없이 바로 FIX로 갔다
   - spec-plan이 Test Agent를 호출하지 않았다
   - impl이 task 파일에 Reference Guidelines 섹션을 넣지 않았다
```

#### 2-3. analyze_with_llm 수정

```python
async def analyze_with_llm(
    detail: SessionDetail,
    segments: list[WorkflowSegment],
    step2_findings: list[Finding],
    wiki_context: str = "",
    workflow_specs: str = "",  # ← 추가
) -> list[Finding]:
```

LLM에 보내는 메시지에 workflow_specs를 포함:

```python
messages = [
    {"role": "user", "content": f"{ANALYSIS_PROMPT}\n\n{workflow_specs}\n\n## 세션 데이터\n\n{context}"}
]
```

#### 2-4. analyze_session에서 자동 로딩

```python
def analyze_session(detail, *, no_llm=True, wiki_dir=None, claude_dir=None):
    # ...
    workflow_specs = ""
    if claude_dir is not None:
        workflow_specs = load_workflow_specs(claude_dir)
    elif not no_llm:
        # 기본 경로에서 시도
        default_dir = Path.home() / ".claude"
        if default_dir.exists():
            workflow_specs = load_workflow_specs(default_dir)
    # ...
    if not no_llm:
        llm_findings = asyncio.run(
            analyze_with_llm(detail, segments, findings, 
                           wiki_context=wiki_context,
                           workflow_specs=workflow_specs)
        )
```

#### 2-5. CLI 옵션

```bash
# 기본: ~/.claude/에서 자동 로드
alens analyze --last 3

# 명시적 경로 (다른 config 테스트)
alens analyze --last 3 --claude-dir /path/to/.claude

# 명세 무시 (기존 동작)
alens analyze --last 3 --no-specs
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--claude-dir` | `~/.claude` | commands/agents 명세 경로 |
| `--no-specs` | false | 명세 로딩 비활성화 (기존 동작) |

---

## 기대 Finding 예시

### spec-deviation findings

```json
{
  "kind": "spec-deviation",
  "topic": "missing-change-summary",
  "source": "impl",
  "agent": "implementer",
  "detail": "implementer가 task-result에 Change Summary(CHANGES MADE / DIDN'T TOUCH / CONCERNS)를 출력하지 않음. agents/implementer.md에 명시된 출력 형식 위반.",
  "confidence": "high",
  "suggestion": "implementer.md의 출력 형식 섹션을 더 강조하거나, 출력 템플릿을 XML 태그로 구조화"
}
```

```json
{
  "kind": "spec-deviation",
  "topic": "skipped-reproduce-step",
  "source": "impl",
  "agent": "debugger",
  "detail": "debugger가 REPRODUCE 단계를 건너뛰고 바로 코드 분석으로 진입. agents/debugger.md의 6단계 프로토콜 1단계 누락.",
  "confidence": "medium",
  "suggestion": "debugger.md에 '단계 건너뛰기 금지' 규칙을 더 명시적으로"
}
```

```json
{
  "kind": "spec-deviation",
  "topic": "missing-test-agent",
  "source": "spec-plan",
  "detail": "spec-plan Step 0에서 Test Agent를 호출하지 않음. commands/spec-plan.md��� 5번째 병렬 에이전트로 정의되어 있으나 실제 세션에서 4개만 스폰됨.",
  "confidence": "high",
  "suggestion": null
}
```

### 강화된 기존 findings

```json
{
  "kind": "skill-suggestion",
  "topic": "ue-gc-safety-rule",
  "source": "impl",
  "detail": "implementer가 UObject 포인터를 UPROPERTY 없이 사용하여 reviewer가 3회 지적. .claude/guidelines/에 GC 안전성 규칙이 없음.",
  "suggestion": "프로젝트 .claude/guidelines/ue-conventions.md에 GC 포인터 규칙 추가"
}
```

---

## 구현 순서

| 순서 | 내용 | 영향 파일 | 난이도 |
|------|------|----------|--------|
| 1 | `discover_workflows()` 함수 | analyze.py | 낮음 |
| 2 | `WORKFLOW_AGENTS`를 동적 호출로 교체 | analyze.py, cli.py | 낮음 |
| 3 | `load_workflow_specs()` 함수 | analyze.py (또는 별도 specs.py) | 낮음 |
| 4 | ANALYSIS_PROMPT에 8번째 축 추가 | analyze.py | 낮음 |
| 5 | `analyze_with_llm`에 workflow_specs 파라미터 추가 | analyze.py | 낮음 |
| 6 | `analyze_session`에서 자동 로딩 | analyze.py | 낮음 |
| 7 | CLI `--claude-dir`, `--no-specs` 옵션 | cli.py | 낮음 |
| 8 | 테스트 | tests/ | 중간 |

개별 난이도는 전부 낮음. 기존 구조(wiki_context 패턴)를 그대로 따르면 됨.

---

## 컨텍스트 크기 고려

commands/*.md + agents/*.md 전부 합쳐도 ~500줄 내외 (현재 구상 기준).
LLM 분석의 세션 컨텍스트가 이미 수천 줄이므로, 명세 추가로 인한 토큰 증가는 미미.

다만 명세가 커지면:
- 세션에서 활성화된 워크플로우의 command + 해당 에이전트만 로드
- 예: impl 세션이면 `commands/impl.md` + `agents/implementer.md, reviewer.md, ...`만
- spec-plan 세션이면 `commands/spec-plan.md` + 해당 에이전트만

```python
def load_workflow_specs(claude_dir, workflow_type=None):
    """workflow_type이 주어지면 해당 command + 관련 agents만 로드."""
```

---

## 하위 호환

- `--no-specs`로 기존 동작 완전 보존
- commands/agents 디렉토리가 없으면 자동 fallback (DEFAULT_WORKFLOW_AGENTS)
- Level 1(자동 발견)과 Level 2(LLM 명세 주입)는 독립적으로 배포 가능
- `--no-llm` 모드에서는 Level 2 자동 비활성화 (명세 로딩만 하고 LLM에 안 넘김)
