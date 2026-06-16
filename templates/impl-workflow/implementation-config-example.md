## Implementation Config

프로젝트 레포의 CLAUDE.md에 아래 섹션을 추가하세요.
`/spec-plan`과 `/impl`이 이 섹션을 읽어서 경로/명령을 결정합니다.
형식은 `key: value` 한 줄. 값이 비면 해당 기능은 조용히 skip 됩니다.
(`sync-workflow.sh`로 동기화하면 이 블록이 CLAUDE.md에 자동 렌더됩니다 — 수동 작성은 아래 참고.)

```markdown
## Implementation Config

specs_path: ../studio-docs/output/specs/
prd_path: ../studio-docs/output/prd/
policies_path: ../studio-docs/policies/
docs_path: .claude/docs
glossary_path: docs/glossary.md
log_repo: ../impl-logs
format_command: clang-format -i
build_command: ./build.sh
test_command: ctest --output-on-failure
```

| 키 | 용도 | 비고 |
|---|---|---|
| `specs_path` / `prd_path` / `policies_path` | spec·PRD·정책 검색 소스 (Spec Agent) | 비우면 해당 검색 skip |
| `docs_path` | `/init-docs` 가 만드는 adr/conventions 위치 | 선택 |
| `glossary_path` | 용어집 — 순화 가이드 1순위 + `/idiom-review` 대상 | 선택 |
| `log_repo` | impl 로그 동기화 대상 레포 (`sync-logs.sh`) | 선택 |
| `format_command` | 커밋 hook용 빠른 포맷터 | 비우면 hook skip |
| `build_command` / `test_command` | PR hook용 빌드·테스트 명령 | 비우면 hook skip |

> **hook 파싱 규칙**: 각 키는 `^key: value` 한 줄로만 인식됩니다. 표(table) 형식·멀티라인 값·**값 줄의 인라인 주석(`#`)** 은 인식되지 않으니, 설명은 값 줄이 아닌 별도 줄(`#`)에 두세요.

### 프로젝트 레포 셋업

`sync-workflow.sh`를 쓰면 1~3은 자동입니다. 수동 셋업 시:

1. CLAUDE.md에 위 `## Implementation Config` 블록 추가 (경로/명령을 프로젝트에 맞게)
2. `templates/impl-workflow/settings.json` → `.claude/settings.json`으로 복사 (없을 때만)
3. `templates/impl-workflow/hooks/` → `.claude/hooks/`로 복사
4. `.gitignore`에 추가: `.claude/current-ticket`, `.claude/plans/`, `.claude/tasks/`, `.claude/runs/`
