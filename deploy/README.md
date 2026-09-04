# AWS 단일 서버 배포

Frontend, Backend, AI Service, Oracle Database를 Docker Compose로 한 EC2 인스턴스에 배포합니다. 외부에는 Frontend의 HTTP 80번 포트만 노출하고 나머지 서비스는 Docker 내부 네트워크에서만 통신합니다.

## 준비

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

그룹 변경 사항을 적용하려면 SSH 세션을 다시 연결합니다.

## 환경 파일

```bash
cd deploy
cp oracle.env.example oracle.env
cp backend.env.example backend.env
cp ai.env.example ai.env
chmod 600 oracle.env backend.env ai.env
```

세 환경 파일의 placeholder를 운영 값으로 변경합니다. Oracle 21c의 관리자 및 애플리케이션 사용자 비밀번호는 영문 대·소문자와 숫자를 포함한 12~30자 ASCII 문자열로 지정합니다. `oracle.env`의 `APP_USER_PASSWORD`와 `backend.env`의 `DB_PASSWORD`는 반드시 같아야 합니다. `CORS_ALLOWED_ORIGINS`와 `FRONTEND_BASE_URL`에는 실제 공개 주소를 입력합니다.

## 실행

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=200
```

Oracle 최초 초기화에는 수 분이 걸릴 수 있습니다. 모든 컨테이너가 healthy 상태가 된 뒤 `http://서버주소`에서 접속합니다.

## 업데이트

```bash
git pull --ff-only
cd deploy
docker compose up -d --build
docker image prune -f
```

## 중지

```bash
docker compose down
```

데이터를 보존하려면 `docker compose down -v`는 사용하지 않습니다.
