# 📈 주식 포트폴리오 트래커 (Stock Portfolio Tracker)

MERN 스택 (MongoDB, Express, React, Node.js)과 WebSocket을 활용하여 구축한 풀스택 주식 포트폴리오 트래커입니다.

사용자는 이메일/비밀번호 또는 Google 계정으로 로그인하여, 주식 거래(매수, 매도, 배당) 내역을 기록할 수 있습니다. Finnhub API와 WebSocket을 연동하여 포트폴리오의 자산 가치와 손익(P/L)을 실시간으로 계산하고 시각화합니다.

---

## 🚀 라이브 데모 (Live Demo)

* **프론트엔드 (Vercel):** [**https://projects-one-teal.vercel.app/**](https://projects-one-teal.vercel.app/)
* **백엔드 (Render):** [**https://stock-tracker-server.onrender.com/**](https://stock-tracker-server.onrender.com/)

## ✨ 주요 기능 (Features)

### 🔐 인증 (Authentication)
* **JWT 인증:** 이메일/비밀번호 회원가입 및 `jsonwebtoken`을 사용한 토큰 기반 로그인.
* **소셜 로그인:** `Passport.js`와 `passport-google-oauth20`을 이용한 **Google OAuth 2.0** 인증.
* **보호된 라우트:** 로그인한 사용자만 API와 페이지에 접근할 수 있도록 미들웨어로 보호.
* **자동 로그아웃:** `Axios Interceptor`를 활용, `401` 에러(토큰 만료 등) 발생 시 자동으로 로그아웃 처리.

### 📊 포트폴리오 관리 (Core)
* **거래 내역(CRUD):** 주식 매수(Buy), 매도(Sell), 배당금(Dividend) 입력을 기록.
* **실시간 손익(P/L) 계산:** 백엔드 API가 모든 거래 내역을 `date` 순으로 정렬하여, 평균 매수 단가(Avg. Cost)를 기반으로 **실현 손익(Realized P/L)**과 **미실현 손익(Unrealized P/L)**을 정확하게 계산.

### 📈 실시간 기능 (Real-time)
* **외부 API 연동:** `Finnhub` API를 연동하여 주식 심볼 검색 및 현재가(`Quote`) 조회.
* **실시간 가격:** `Finnhub WebSocket`에 연결하여, 보유 주식과 관심 목록의 주가를 **실시간으로** 업데이트.
* **데이터 시각화:** `Chart.js` (`react-chartjs-2`)를 사용하여 현재 보유 자산의 비율을 **원 그래프(Doughnut Chart)**로 시각화.

### 💅 UI/UX 개선
* **관심 목록(Watchlist):** `GET`, `POST`, `DELETE` API를 구현하여 관심 목록(찜하기) 추가/삭제/조회 기능.
* **동적 폼:** "거래 유형" 선택(매수/매도/배당)에 따라 폼의 UI가 동적으로 변경.
* **검색 연동:** 주식 검색 결과 클릭 시, "거래 추가" 폼에 심볼과 현재가가 자동으로 채워짐.

### 🧪 테스트 (Testing)
* **백엔드 API 테스트:** `Jest`와 `Supertest`를 사용하여 인증(Auth) 및 포트폴리오(Portfolio) API의 핵심 로직을 테스트.
* **데이터베이스 격리:** `NODE_ENV=test` 환경 변수를 사용하여, 테스트 실행 시 **별도의 테스트 DB**(`MONGO_URI_TEST`)를 사용하고 매번 초기화.
* **모킹(Mocking):** `jest.mock('axios')`를 사용하여 외부 Finnhub API를 모킹하고, API가 다운되어도 손익 계산 로직을 안정적으로 테스트.

---

## 🛠️ 기술 스택 (Tech Stack)

### 🖥️ Frontend (`client/`)
* React
* Vite
* React Router
* React Context API (전역 상태 관리)
* Chart.js (`react-chartjs-2`)
* Axios (인터셉터 포함)

### ⚙️ Backend (`server/`)
* Node.js
* Express.js
* MongoDB (Mongoose)
* Passport.js (`passport-google-oauth20`)
* JSON Web Token (JWT)
* Bcrypt.js
* WebSocket (Finnhub 연동)

### 🧪 Testing (`server/`)
* Jest
* Supertest
* Cross-Env

---

## 🏃‍♂️ 로컬에서 실행하기 (Local Setup)

이 프로젝트는 `Projects` 모노레포 내의 `stock-tracker` 폴더입니다.

### 1. 저장소 클론 (Root)
```bash
git clone [https://github.com/](https://github.com/)<your-username>/Projects.git
cd Projects/stock-tracker