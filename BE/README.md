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
| `UPLOAD_RETENTION` | `1d` | 업로드 원본 파일 보존 기간 |
| `UPLOAD_CLEANUP_INTERVAL` | `1h` | 만료 파일 정리 주기 |
| `UPLOAD_CLEANUP_INITIAL_DELAY` | `1m` | 서버 시작 후 첫 정리까지의 대기 시간 |
| `ANALYSIS_ASYNC_ENABLED` | `true` | 분석 작업 비동기 실행 여부 |
| `AI_SERVICE_BASE_URL` | `http://localhost:8000` | Python AI 서비스 주소 |
| `AI_SERVICE_CONNECT_TIMEOUT` | `3s` | AI 서비스 연결 제한 시간 |
| `AI_SERVICE_READ_TIMEOUT` | `150s` | AI 서비스 응답 제한 시간 |
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
