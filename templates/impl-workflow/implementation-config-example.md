## Implementation Config

프로젝트 레포의 CLAUDE.md에 아래 섹션을 추가하세요.
`/spec-plan`과 `/impl`이 이 섹션을 읽어서 경로를 결정합니다.

```markdown
## Implementation Config

| 항목 | 값 |
|------|-----|
| specs_path | ../studio-docs/output/specs/ |
| prd_path | ../studio-docs/output/prd/ |
| policies_path | ../studio-docs/policies/ |
| format_command | (커밋 Hook용 — clang-format, prettier 등 빠른 포맷터) |
| build_command | (PR Hook용 — 프로젝트 빌드 명령) |
| test_command | (PR Hook용 — 테스트 실행 명령) |
| log_repo | ../impl-logs |
```

### 프로젝트 레포 셋업

1. CLAUDE.md에 위 섹션 추가
2. `templates/impl-workflow/settings.json` → `.claude/settings.json`으로 복사
3. `templates/impl-workflow/hooks/` → `.claude/hooks/`로 복사
4. `.gitignore`에 추가: `.claude/current-ticket`, `.claude/plans/`
