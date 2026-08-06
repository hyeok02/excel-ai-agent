# Excel AI Agent Frontend

React, Vite, TypeScript, Tailwind CSS 기반 프런트엔드입니다.

## 실행

```bash
npm install
cp .env.example .env
npm run dev
```

기본 개발 서버는 `http://localhost:5173`에서 실행됩니다.

## 명령어

```bash
npm run dev          # 개발 서버
npm run typecheck    # TypeScript 검사
npm run lint         # ESLint + Oxlint
npm run format       # Prettier 포맷
npm run build        # 프로덕션 빌드
npm run preview      # 빌드 결과 확인
```

## 폴더 구조

```text
src/
├── app/providers/       # 앱 전역 Provider
├── components/          # 공통 컴포넌트
├── constants/           # 경로·메뉴 등 상수
├── layouts/             # RootLayout 등 공통 레이아웃
├── pages/               # 라우트 단위 화면
├── routes/              # React Router 설정
├── styles/              # Tailwind 테마·전역 스타일
└── utils/               # API Client와 공통 함수
```

`@/`는 `src/`를 가리키는 경로 별칭입니다.

## 환경 변수

```text
VITE_API_BASE_URL=http://localhost:8080
VITE_API_TIMEOUT=30000
```

실제 `.env` 파일은 Git에 포함하지 않습니다.
