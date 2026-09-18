# Excel AI Agent Backend

Java 21, Spring Boot, Gradle 기반 백엔드 API입니다.

## 실행

```bash
./gradlew bootRun
```

기본 서버 주소는 `http://localhost:8080`입니다.

## 확인

```bash
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/actuator/health
```

## 환경 변수

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `SERVER_PORT` | `8080` | 백엔드 포트 |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | 프런트엔드 허용 Origin |
| `MAX_FILE_SIZE` | `50MB` | 단일 업로드 파일 제한 |
| `MAX_REQUEST_SIZE` | `50MB` | 전체 multipart 요청 제한 |
| `UPLOAD_DIR` | `./uploads` | 분석 원본 파일 저장 경로 |
| `UPLOAD_RETENTION` | `7d` | 업로드 원본 파일 보존 기간. 이 기간이 지나면 예전 분석에 질문하거나 수정할 수 없습니다 |
| `UPLOAD_CLEANUP_INTERVAL` | `1h` | 만료 파일 정리 주기 |
| `UPLOAD_CLEANUP_INITIAL_DELAY` | `1m` | 서버 시작 후 첫 정리까지의 대기 시간 |
| `ANALYSIS_ASYNC_ENABLED` | `true` | 분석 작업 비동기 실행 여부 |
| `AI_SERVICE_BASE_URL` | `http://localhost:8000` | Python AI 서비스 주소 |
| `AI_SERVICE_CONNECT_TIMEOUT` | `3s` | AI 서비스 연결 제한 시간 |
| `AI_SERVICE_READ_TIMEOUT` | `150s` | AI 서비스 응답 제한 시간 |
| `TELEGRAM_ENABLED` | `false` | 분석 결과 텔레그램 전송 활성화 |
| `TELEGRAM_BOT_TOKEN` | 빈 값 | BotFather에서 발급한 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 빈 값 | 수신자를 선택하지 않는 기존 전송의 기본 채팅방 ID(선택) |
| `TELEGRAM_WEBHOOK_SECRET` | 빈 값 | Telegram webhook 요청 검증용 임의 비밀 문자열 |
| `TELEGRAM_WEBHOOK_URL` | 빈 값 | 외부에서 접근 가능한 HTTPS webhook 전체 URL |
| `TELEGRAM_INVITATION_TTL` | `24h` | 일회용 수신자 초대 링크 유효 시간 |
| `ANALYSIS_PUBLIC_SHARE_TTL` | `7d` | 수신자용 읽기 전용 분석 링크 유효 시간 |
| `AUTH_SECURITY_ENABLED` | `true` | API 로그인 보호 활성화 |
| `FRONTEND_BASE_URL` | `http://localhost:5173` | SSO 완료 후 돌아갈 Frontend 주소 |
| `BOOTSTRAP_ADMIN_USERNAME` | `admin` | 최초 관리자 아이디 |
| `BOOTSTRAP_ADMIN_PASSWORD` | `admin1234` | 최초 관리자 비밀번호 |
| `SSO_ENABLED` | `false` | 회사 OIDC SSO 활성화 |
| `SSO_ALLOWED_DOMAIN` | 빈 값 | 허용할 회사 이메일 도메인 |
| `SSO_AUTO_PROVISION` | `true` | 최초 SSO 로그인 시 사용자 자동 생성 |

## 로그인

최초 실행 시 `admin / admin1234` 관리자 계정이 생성됩니다. 운영 환경에서는 `BOOTSTRAP_ADMIN_PASSWORD`를 반드시 변경해야 합니다. 관리자는 `/api/v1/admin/users`를 통해 별도의 회원가입 없이 사내 계정을 발급할 수 있습니다.

회사 SSO는 OpenID Connect 공급자를 사용합니다. `SSO_ENABLED=true`와 함께 `.env.example`의 `SPRING_SECURITY_OAUTH2_CLIENT_*` 값을 회사 인증 서버 정보로 설정합니다.

## 현재 범위

- Spring Boot 애플리케이션과 Gradle Wrapper
- `/api/v1/health` 및 Actuator health check
- React 개발 서버용 CORS
- XLSX/XLSM 업로드를 위한 50MB multipart 제한
- 공통 검증/업로드 오류 응답
- Python AI 서비스 연결용 환경 설정
- 비동기 Excel 분석 작업, 결과 이력 및 원본 파일 보관
- `POST /api/v1/analyses/{analysisId}/questions` 단일 Excel 근거 기반 Q&A
  - 요청: `{ "question": "자연어 질문" }`
  - 응답: 답변, 신뢰도, 선택된 Agent Tool, 원본 시트·셀 근거, 분석 한계

Q&A는 기존 분석 ID에 보관된 원본 Excel을 다시 사용하므로 파일을 재업로드하지 않습니다.

## 텔레그램 공유

BotFather에서 봇을 만든 뒤 `TELEGRAM_ENABLED=true`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_WEBHOOK_URL`을 설정합니다. Webhook URL은 외부에서
접근 가능한 HTTPS 주소이며 보통
`https://<backend-host>/api/v1/telegram/webhook`입니다. 서버는 시작할 때 Telegram의
`setWebhook`을 호출해 URL, 비밀 헤더와 `message` 업데이트를 등록합니다.

로그인한 사용자는 일회용 초대 링크를 생성하고 상대방에게 전달할 수 있습니다. 상대방이
링크를 열고 봇의 **Start**를 누르면 개인 채팅 ID가 초대를 만든 사용자에게만 귀속됩니다.
원문 초대 토큰은 생성 응답에서 한 번만 반환되고 데이터베이스에는 SHA-256 해시만
저장됩니다. 초대는 기본 24시간 후 만료되며 한 번만 사용할 수 있습니다.

분석 결과 전송 시 등록된 수신자 UUID를 선택하면 수신자별 성공·실패 결과가 반환됩니다.
봇 토큰과 실제 Telegram 채팅 ID는 Frontend 응답에 포함되지 않습니다. 요청 body 자체를
생략한 기존 호출만 `TELEGRAM_CHAT_ID`를 기본 수신자로 사용하며, 명시적으로 빈 수신자
목록을 보내면 요청이 거부됩니다.

등록된 수신자에게 전송되는 상세 결과 주소는 기본 7일 동안 유효한 읽기 전용 링크입니다.
링크 원문은 데이터베이스에 저장하지 않으며, 수신자를 연결 해제하면 발급된 링크도 즉시
폐기됩니다. 공유 화면에는 질문·Excel 수정·내보내기·재전송 기능이 노출되지 않습니다.
