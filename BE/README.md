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
| `AI_SERVICE_BASE_URL` | `http://localhost:8000` | Python AI 서비스 주소 |
| `AI_SERVICE_CONNECT_TIMEOUT` | `3s` | AI 서비스 연결 제한 시간 |
| `AI_SERVICE_READ_TIMEOUT` | `60s` | AI 서비스 응답 제한 시간 |

## 현재 범위

- Spring Boot 애플리케이션과 Gradle Wrapper
- `/api/v1/health` 및 Actuator health check
- React 개발 서버용 CORS
- XLSX/XLSM 업로드를 위한 50MB multipart 제한
- 공통 검증/업로드 오류 응답
- Python AI 서비스 연결용 환경 설정

파일 업로드, 분석 Job, 결과 이력, 저장소, Python 호출은 다음 단계에서 구현합니다.
