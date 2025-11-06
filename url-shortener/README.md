<<<<<<< HEAD
# URL 단축 서비스 (MERN Stack Project)

MERN 스택(MongoDB, Express.js, React, Node.js)을 사용하여 개발한 풀스택 URL 단축 서비스입니다.

긴 URL을 입력하면 짧은 URL을 생성해주며, 사용자 정의 URL, 만료 기한 설정, 클릭 횟수 추적 등 다양한 기능을 제공합니다.

---

## 주요 기능

* **URL 단축:** `nanoid`를 사용하여 안전하고 짧은 URL 코드를 생성합니다.
* **리다이렉트:** 생성된 짧은 URL로 접속 시 원래 URL로 리다이렉트합니다.
* **사용자 정의 URL:** 사용자가 원하는 문자열로 짧은 URL을 직접 지정할 수 있습니다.
* **클릭 횟수 추적:** 생성된 URL의 리다이렉트 횟수(클릭 수)를 추적합니다.
* **만료 기한 설정:** MongoDB의 `TTL Index`를 활용하여 1시간, 1일, 7일 후 URL이 자동으로 만료되도록 설정할 수 있습니다.
* **실시간 클립보드 복사:** 생성된 URL을 클릭 한 번으로 복사할 수 있습니다.

---

## 사용된 기술 스택

### 프론트엔드 (Client)
* **React** (with Vite)
* **JavaScript (ES6+)**
* **axios** (for API communication)
* **CSS 3**

### 백엔드 (Server)
* **Node.js**
* **Express.js** (for REST API)
* **MongoDB Atlas** (Database)
* **Mongoose** (ODM for MongoDB)
* `nanoid` (for short code generation)
* `dotenv` (for environment variables)
* `cors`

---

## 로컬에서 실행하기

이 프로젝트를 로컬 환경에서 실행하는 방법입니다.

### 1. 전제 조건

* Node.js (v20+ 권장)
* npm
* Git
* MongoDB Atlas 계정 (무료 M0 클러스터)

### 2. 프로젝트 클론 및 설정

```bash
# 1. GitHub 리포지토리 클론
git clone [https://github.com/](https://github.com/)<your-username>/url-shortener.git

# 2. 프로젝트 폴더로 이동
cd url-shortener
