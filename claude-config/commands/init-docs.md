# Initialize Project Docs

Bootstrap opt-in structured docs (`adr.yaml` + `conventions.yaml` + `glossary.md`).

**Usage**: `/init-docs` | `/init-docs --path docs` | `/init-docs --path .claude/docs`

## On activation

1. Default path: `.claude/docs/`. If `--path PATH` provided, use PATH.
2. If `${PATH}/adr.yaml` exists or `${PATH}/conventions.yaml` exists, abort and tell user
   ("docs already initialized at ${PATH}; refusing to overwrite").
   If `${PATH}/glossary.md` exists, abort and tell user
   ("glossary already initialized at ${PATH}/glossary.md; refusing to overwrite").
3. Copy templates verbatim. **Template source resolution** (처음 존재하는 디렉토리 사용):
   1. `.claude/templates/project-setup/docs/` — 소비 프로젝트에 vendored 된 경우 (`sync-workflow.sh` 배포)
   2. `./templates/project-setup/docs/` — 워크플로우 레포 안에서 직접 실행
   3. `~/.claude/templates/project-setup/docs/` — user-level `deploy.sh` 배포
   셋 다 없으면 "`sync-workflow.sh` 또는 `./deploy.sh` 미실행 가능성 — docs 템플릿을 찾을 수 없음" 경고 후 중단.

   해석된 `${DOCS_TPL}` 기준으로 복사:
   - `${DOCS_TPL}/adr.yaml` → `${PATH}/adr.yaml`
   - `${DOCS_TPL}/conventions.yaml` → `${PATH}/conventions.yaml`
   - `${DOCS_TPL}/glossary.md` → `${PATH}/glossary.md`
4. Append to `CLAUDE.md` under `## Implementation Config` (creating the section if missing):
   ```
   docs_path: ${PATH}
   glossary_path: ${PATH}/glossary.md
   ```
   If `CLAUDE.md` does not exist, do not create it — just print the two lines for the user to paste.
5. GLOSSARY 부트스트랩 — 도메인 어휘 추출 + 사용자 1-by-1 확인:
   a. 추출 소스: `CLAUDE.md` 의 `specs_path` / `prd_path` 가 가리키는 디렉토리. 없으면 repo root 의 `README` + 최상위 `src` 하위 디렉토리 이름에서 코드 식별자(주요 모듈/서비스/데이터 모델 이름)와 PRD 도메인 어휘를 추출한다.
   b. 추출 후보가 20개를 초과하면 사람에게 "후보가 N개입니다. 우선순위가 높은 term을 먼저 나열해 주세요 (최대 20개)" 라고 요청한다. 자동으로 임의 선택하지 않는다.
   c. 후보를 1-by-1 사용자에게 제시한다:
      ```
      term: {english} → 풀이 (제안): {one line}
      (y=등록 / n=skip / e=편집)
      ```
   d. `y` 또는 `e` (편집된) 응답은 `${PATH}/glossary.md` 본문에 `## {term}` 헤딩 + 한글 풀이 한 단락으로 append한다.
   e. idiom 분기(글로벌 vs 도메인 분류) **없음** — GLOSSARY 로만 등록한다.
   f. 사용자 응답 없이 자동 등록 금지. 응답 1건당 entry 1건.
6. Stop. Do not commit.

## Rules

- Never overwrite existing yaml.
- Never overwrite existing glossary.md — abort and notify the user.
- Never add example entries automatically — user fills in.
- Never modify any file outside `${PATH}/` and CLAUDE.md.
- GLOSSARY 부트스트랩 등록은 사용자 응답 1건당 entry 1건. 자동 batch 금지.
