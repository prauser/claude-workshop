<!-- cw-impl-workflow:start (managed by workflow sync — sync-workflow.sh — do not rename these markers) -->
## Implementation Config

# /spec-plan · /impl 이 읽는 경로/명령 키. 형식은 `key: value` 한 줄.
# 값을 비우면 해당 기능은 조용히 skip (검색 에이전트·hook 미동작).
# 값 줄에는 인라인 주석(#)을 쓰지 말 것 — hook 파서가 값으로 오인한다.
# 각 키 설명·예시: templates/impl-workflow/implementation-config-example.md
# 경로: specs_path/prd_path/policies_path/docs_path/glossary_path/log_repo
# 명령: format_command(커밋 hook) / build_command·test_command(PR hook)
specs_path: docs/specs
prd_path: docs/prd
policies_path:
docs_path:
glossary_path: docs/glossary.md
log_repo:
format_command:
build_command:
test_command:
guidelines:
{{GUIDELINES_LIST}}

## Quality Gates
{{QUALITY_GATES}}
<!-- cw-impl-workflow:end -->
