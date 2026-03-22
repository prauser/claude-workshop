# claude-workshop

Claude Code 학습, 실험, 운영을 위한 올인원 워크스페이스.

플러그인 분석, 지식 수집, 프롬프트 실험, 커맨드/에이전트 배포까지 이 레포 안에서 완결된다.

## 폴더 구조

```
claude-workshop/
├── claude-config/         # 배포 소스 오브 트루스 (커맨드, 에이전트)
├── references/            # 외부 플러그인/도구 소스 클론 (읽기 전용 분석)
├── notes/                 # 수집·정리한 지식, 리서치 노트
├── experiments/           # 직접 테스트하고 결과 기록
├── templates/             # 실험 중인 프롬프트 템플릿 (검증 전)
├── sandbox/               # 임시 설치 테스트 (사용 후 제거)
├── CLAUDE.md              # Claude Code용 레포 규칙
├── SETUP_GUIDE.md         # 세팅 가이드 & 워크플로우 설명
├── deploy.sh              # claude-config → ~/.claude/ 배포
└── README.md
```

## 핵심 사이클

```
notes/        지식 수집·정리 (논문, 아티클, 팁 등)
    ↓
experiments/  직접 테스트·검증
    ↓
templates/    프롬프트 템플릿으로 정리
    ↓ 효과 확인
claude-config/  커맨드·에이전트에 반영
    ↓ deploy.sh
~/.claude/    유저 레벨에 즉시 적용 → 모든 프로젝트에서 사용
```

## 빠른 시작

```bash
# 초기 배포
cd ~/claude-workshop
./deploy.sh

# 플러그인 분석
cd ~/claude-workshop
claude
> references/get-shit-done/ 읽고 패턴 분석해줘

# 실험 후 배포
# claude-config/ 수정 → deploy.sh 실행
```

## ai-workspace와의 관계

| | claude-workshop | ai-workspace |
|---|---|---|
| 대상 | Claude 전용 | Claude 외 도구 (Gemini, Codex, Cursor 등) + 공통 |
| 성격 | 학습 + 실험 + 배포 | 도구 간 공유 자산 관리 |
| 배포 | `deploy.sh` → `~/.claude/` | 심링크로 각 프로젝트에 배포 |

두 레포는 같은 폴더 네이밍 컨벤션을 따른다. 자세한 내용은 [SETUP_GUIDE.md](SETUP_GUIDE.md) 참조.

## 폴더 컨벤션 (ai-workspace 공유)

```
commands/      도구별 커맨드 (배포용)
context/       프로젝트별 컨텍스트 파일 (배포용)
prompts/       검증된 프롬프트 템플릿 (배포용)
references/    외부 소스 클론/분석 (읽기 전용)
notes/         수집·정리한 지식
experiments/   직접 테스트 기록
sandbox/       임시 설치 테스트 (사용 후 제거)
```

필요할 때 폴더를 추가한다. 빈 폴더는 만들지 않는다.
