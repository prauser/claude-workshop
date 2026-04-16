---
name: security-and-hardening
description: 취약점으로부터 코드를 강화합니다. 사용자 입력 처리, 인증, 데이터 저장, 외부 연동을 다룰 때 사용합니다. 신뢰할 수 없는 데이터를 받아들이거나, 사용자 세션을 관리하거나, 서드파티 서비스와 상호작용하는 기능을 구축할 때 사용합니다.
---

# 보안과 하드닝

## 개요

웹 애플리케이션을 위한 보안 우선 개발 실천 방법입니다. 모든 외부 입력을 적대적인 것으로, 모든 비밀 정보를 신성한 것으로, 모든 인가 확인을 필수적인 것으로 취급합니다. 보안은 하나의 단계가 아닙니다 — 사용자 데이터, 인증, 또는 외부 시스템을 건드리는 모든 코드 한 줄 한 줄에 적용되는 제약 조건입니다.

## 사용 시점

- 사용자 입력을 받는 모든 것을 구축할 때
- 인증 또는 인가를 구현할 때
- 민감한 데이터를 저장하거나 전송할 때
- 외부 API 또는 서비스와 연동할 때
- 파일 업로드, 웹훅, 또는 콜백을 추가할 때
- 결제 또는 개인식별정보(PII) 데이터를 처리할 때

## 3단계 경계 시스템

### 항상 수행 (예외 없음)

- **모든 외부 입력 유효성 검증** — 시스템 경계(API 라우트, 폼 핸들러)에서 수행
- **모든 데이터베이스 쿼리 파라미터화** — 사용자 입력을 SQL에 직접 연결하지 말 것
- **출력 인코딩** — XSS 방지 (프레임워크 자동 이스케이프 사용, 우회하지 말 것)
- **모든 외부 통신에 HTTPS 사용**
- **bcrypt/scrypt/argon2로 비밀번호 해싱** (평문 저장 금지)
- **보안 헤더 설정** (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- **세션에 httpOnly, secure, sameSite 쿠키 사용**
- **모든 릴리스 전 `npm audit` 실행** (또는 동급 도구)

### 먼저 확인 (사람의 승인 필요)

- 새로운 인증 플로우 추가 또는 인증 로직 변경
- 새로운 범주의 민감한 데이터 저장 (PII, 결제 정보)
- 새로운 외부 서비스 연동 추가
- CORS 설정 변경
- 파일 업로드 핸들러 추가
- 속도 제한 또는 스로틀링 수정
- 높은 권한이나 역할 부여

### 절대 하지 말 것

- **버전 관리에 비밀 정보 커밋 금지** (API 키, 비밀번호, 토큰)
- **민감한 데이터 로깅 금지** (비밀번호, 토큰, 전체 신용카드 번호)
- **클라이언트 측 유효성 검증을 보안 경계로 신뢰 금지**
- **편의를 위해 보안 헤더 비활성화 금지**
- **사용자 제공 데이터에 `eval()` 또는 `innerHTML` 사용 금지**
- **클라이언트 접근 가능한 저장소에 세션 저장 금지** (인증 토큰에 localStorage 사용)
- **사용자에게 스택 트레이스 또는 내부 오류 세부 정보 노출 금지**

## OWASP Top 10 예방

### 1. 인젝션 (SQL, NoSQL, OS 명령어)

```typescript
// 나쁜 예: 문자열 연결을 통한 SQL 인젝션
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// 좋은 예: 파라미터화된 쿼리
const user = await db.query('SELECT * FROM users WHERE id = $1', [userId]);

// 좋은 예: 파라미터화된 입력이 있는 ORM
const user = await prisma.user.findUnique({ where: { id: userId } });
```

### 2. 인증 취약점

```typescript
// 비밀번호 해싱
import { hash, compare } from 'bcrypt';

const SALT_ROUNDS = 12;
const hashedPassword = await hash(plaintext, SALT_ROUNDS);
const isValid = await compare(plaintext, hashedPassword);

// 세션 관리
app.use(session({
  secret: process.env.SESSION_SECRET,  // 코드가 아닌 환경변수에서
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,     // JavaScript로 접근 불가
    secure: true,       // HTTPS 전용
    sameSite: 'lax',    // CSRF 방지
    maxAge: 24 * 60 * 60 * 1000,  // 24시간
  },
}));
```

### 3. Cross-Site Scripting (XSS)

```typescript
// 나쁜 예: 사용자 입력을 HTML로 렌더링
element.innerHTML = userInput;

// 좋은 예: 프레임워크 자동 이스케이프 사용 (React는 기본으로 수행)
return <div>{userInput}</div>;

// HTML을 반드시 렌더링해야 한다면, 먼저 살균
import DOMPurify from 'dompurify';
const clean = DOMPurify.sanitize(userInput);
```

### 4. 접근 제어 취약점

```typescript
// 인증뿐만 아니라 인가도 항상 확인
app.patch('/api/tasks/:id', authenticate, async (req, res) => {
  const task = await taskService.findById(req.params.id);

  // 인증된 사용자가 이 리소스를 소유하는지 확인
  if (task.ownerId !== req.user.id) {
    return res.status(403).json({
      error: { code: 'FORBIDDEN', message: '이 태스크를 수정할 권한이 없습니다' }
    });
  }

  // 업데이트 진행
  const updated = await taskService.update(req.params.id, req.body);
  return res.json(updated);
});
```

### 5. 보안 설정 오류

```typescript
// 보안 헤더 (Express에는 helmet 사용)
import helmet from 'helmet';
app.use(helmet());

// Content Security Policy
app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'"],
    styleSrc: ["'self'", "'unsafe-inline'"],  // 가능하면 더 엄격하게
    imgSrc: ["'self'", 'data:', 'https:'],
    connectSrc: ["'self'"],
  },
}));

// CORS — 알려진 출처로 제한
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || 'http://localhost:3000',
  credentials: true,
}));
```

### 6. 민감한 데이터 노출

```typescript
// API 응답에 민감한 필드를 절대 반환하지 말 것
function sanitizeUser(user: UserRecord): PublicUser {
  const { passwordHash, resetToken, ...publicFields } = user;
  return publicFields;
}

// 비밀 정보에는 환경 변수 사용
const API_KEY = process.env.STRIPE_API_KEY;
if (!API_KEY) throw new Error('STRIPE_API_KEY가 설정되지 않았습니다');
```

## 입력 유효성 검증 패턴

### 경계에서의 스키마 유효성 검증

```typescript
import { z } from 'zod';

const CreateTaskSchema = z.object({
  title: z.string().min(1).max(200).trim(),
  description: z.string().max(2000).optional(),
  priority: z.enum(['low', 'medium', 'high']).default('medium'),
  dueDate: z.string().datetime().optional(),
});

// 라우트 핸들러에서 유효성 검증
app.post('/api/tasks', async (req, res) => {
  const result = CreateTaskSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(422).json({
      error: {
        code: 'VALIDATION_ERROR',
        message: '잘못된 입력',
        details: result.error.flatten(),
      },
    });
  }
  // result.data는 이제 타입이 지정되고 유효성 검증됨
  const task = await taskService.create(result.data);
  return res.status(201).json(task);
});
```

### 파일 업로드 안전 처리

```typescript
// 파일 유형과 크기 제한
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE = 5 * 1024 * 1024; // 5MB

function validateUpload(file: UploadedFile) {
  if (!ALLOWED_TYPES.includes(file.mimetype)) {
    throw new ValidationError('허용되지 않는 파일 유형');
  }
  if (file.size > MAX_SIZE) {
    throw new ValidationError('파일 크기 초과 (최대 5MB)');
  }
  // 파일 확장자를 신뢰하지 말 것 — 중요한 경우 매직 바이트 확인
}
```

## npm audit 결과 분류

모든 감사 결과가 즉각적인 조치를 필요로 하지는 않습니다. 다음 의사결정 트리를 사용하세요:

```
npm audit이 취약점을 보고함
├── 심각도: critical 또는 high
│   ├── 취약한 코드가 앱에서 도달 가능한가?
│   │   ├── 예 --> 즉시 수정 (업데이트, 패치, 또는 의존성 교체)
│   │   └── 아니오 (개발 전용 의존성, 사용되지 않는 코드 경로) --> 곧 수정하되 차단 요소는 아님
│   └── 수정 방법이 있는가?
│       ├── 예 --> 패치된 버전으로 업데이트
│       └── 아니오 --> 우회 방법 확인, 의존성 교체 고려, 또는 검토 날짜와 함께 허용 목록에 추가
├── 심각도: moderate
│   ├── 프로덕션에서 도달 가능? --> 다음 릴리스 사이클에서 수정
│   └── 개발 전용? --> 편할 때 수정, 백로그에서 추적
└── 심각도: low
    └── 정기 의존성 업데이트 시 추적 및 수정
```

**핵심 질문:**
- 취약한 함수가 실제로 코드 경로에서 호출되는가?
- 의존성이 런타임 의존성인가, 개발 전용인가?
- 배포 컨텍스트를 고려할 때 취약점이 실제로 악용 가능한가? (예: 클라이언트 전용 앱의 서버 측 취약점)

수정을 미룰 경우, 이유를 문서화하고 검토 날짜를 설정하세요.

## 속도 제한

```typescript
import rateLimit from 'express-rate-limit';

// 일반 API 속도 제한
app.use('/api/', rateLimit({
  windowMs: 15 * 60 * 1000, // 15분
  max: 100,                   // 윈도우당 100 요청
  standardHeaders: true,
  legacyHeaders: false,
}));

// 인증 엔드포인트에 더 엄격한 제한
app.use('/api/auth/', rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,  // 15분당 10회 시도
}));
```

## 비밀 정보 관리

```
.env 파일:
  ├── .env.example  → 커밋됨 (플레이스홀더 값이 있는 템플릿)
  ├── .env          → 커밋 안 됨 (실제 비밀 정보 포함)
  └── .env.local    → 커밋 안 됨 (로컬 오버라이드)

.gitignore에 반드시 포함:
  .env
  .env.local
  .env.*.local
  *.pem
  *.key
```

**커밋 전 항상 확인:**
```bash
# 실수로 스테이징된 비밀 정보 확인
git diff --cached | grep -i "password\|secret\|api_key\|token"
```

## 보안 검토 체크리스트

```markdown
### 인증
- [ ] bcrypt/scrypt/argon2로 비밀번호 해싱 (salt rounds ≥ 12)
- [ ] 세션 토큰이 httpOnly, secure, sameSite 적용됨
- [ ] 로그인에 속도 제한이 있음
- [ ] 비밀번호 재설정 토큰이 만료됨

### 인가
- [ ] 모든 엔드포인트에서 사용자 권한 확인
- [ ] 사용자가 자신의 리소스에만 접근 가능
- [ ] 관리자 작업에 관리자 역할 검증 필요

### 입력
- [ ] 모든 사용자 입력이 경계에서 유효성 검증됨
- [ ] SQL 쿼리가 파라미터화됨
- [ ] HTML 출력이 인코딩/이스케이프됨

### 데이터
- [ ] 코드나 버전 관리에 비밀 정보 없음
- [ ] API 응답에서 민감한 필드 제외됨
- [ ] PII가 저장 시 암호화됨 (해당되는 경우)

### 인프라
- [ ] 보안 헤더 설정됨 (CSP, HSTS 등)
- [ ] CORS가 알려진 출처로 제한됨
- [ ] 의존성의 취약점 감사 완료
- [ ] 오류 메시지가 내부 정보를 노출하지 않음
```

## 참고 자료

자세한 보안 체크리스트와 커밋 전 검증 단계는 `references/security-checklist.md`를 참고하세요.

## 흔한 합리화

| 합리화 | 현실 |
|--------|------|
| "내부 도구라서 보안이 중요하지 않아" | 내부 도구도 침해됩니다. 공격자는 가장 약한 연결 고리를 노립니다. |
| "나중에 보안을 추가할게" | 보안을 나중에 추가하는 것은 처음부터 구축하는 것보다 10배 더 어렵습니다. 지금 추가하세요. |
| "아무도 이걸 악용하려 하지 않을 거야" | 자동화된 스캐너가 찾아낼 겁니다. 모호함에 의한 보안은 보안이 아닙니다. |
| "프레임워크가 보안을 처리해줘" | 프레임워크는 도구를 제공하지 보장을 제공하지 않습니다. 올바르게 사용해야 합니다. |
| "그냥 프로토타입이야" | 프로토타입은 프로덕션이 됩니다. 첫날부터 보안 습관을 들이세요. |

## 위험 신호

- 사용자 입력이 데이터베이스 쿼리, 셸 명령어, 또는 HTML 렌더링에 직접 전달됨
- 소스 코드나 커밋 히스토리에 비밀 정보 존재
- 인증이나 인가 확인 없는 API 엔드포인트
- CORS 설정 없거나 와일드카드(`*`) 출처
- 인증 엔드포인트에 속도 제한 없음
- 사용자에게 스택 트레이스나 내부 오류 노출
- 알려진 critical 취약점이 있는 의존성

## 검증

보안 관련 코드 구현 후:

- [ ] `npm audit`에서 critical 또는 high 취약점 없음
- [ ] 소스 코드나 git 히스토리에 비밀 정보 없음
- [ ] 시스템 경계에서 모든 사용자 입력 유효성 검증됨
- [ ] 모든 보호된 엔드포인트에서 인증과 인가 확인됨
- [ ] 응답에 보안 헤더 존재 (브라우저 DevTools로 확인)
- [ ] 오류 응답이 내부 세부 정보를 노출하지 않음
- [ ] 인증 엔드포인트에 속도 제한 활성화됨
