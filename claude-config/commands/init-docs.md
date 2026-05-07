# Initialize Project Docs

Bootstrap opt-in structured docs (`adr.yaml` + `conventions.yaml`).

**Usage**: `/init-docs` | `/init-docs --path docs` | `/init-docs --path .claude/docs`

## On activation

1. Default path: `.claude/docs/`. If `--path PATH` provided, use PATH.
2. If `${PATH}/adr.yaml` exists or `${PATH}/conventions.yaml` exists, abort and tell user
   ("docs already initialized at ${PATH}; refusing to overwrite").
3. Copy templates verbatim:
   - `templates/project-setup/docs/adr.yaml` → `${PATH}/adr.yaml`
   - `templates/project-setup/docs/conventions.yaml` → `${PATH}/conventions.yaml`
4. Append a one-line note to `CLAUDE.md` under `## Implementation Config` (creating the section
   if missing): `docs_path: ${PATH}`. If `CLAUDE.md` does not exist, do not create it — just print
   the line for the user to paste.
5. Stop. Do not commit.

## Rules

- Never overwrite existing yaml.
- Never add example entries automatically — user fills in.
- Never modify any file outside `${PATH}/` and CLAUDE.md.
