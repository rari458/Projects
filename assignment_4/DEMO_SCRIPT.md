# 시연 영상 대본 (Assignment #4-2)

과제 조건: **모든 기능의 세세한 시연 과정**과 **음성 또는 자막 설명**이 필요합니다. 아래 장면을 순서대로 녹화하면 필수 기능과 추가 기능 4가지가 모두 들어갑니다. 장면 순서는 시드 데이터 상태에 맞춰 정했으므로 바꾸지 않는 것이 안전합니다. 예를 들어 차트는 대출을 하기 전에 보여야 숫자가 시드와 같습니다.

- 녹화 직전에 반드시 `npm run db:init`을 실행합니다 (대출 날짜가 초기화한 날 기준).
- 브라우저 확대를 125% 정도로 두면 표가 잘 보입니다.
- 각 장면의 "설명"은 내레이션으로 말하거나 자막으로 넣을 문장입니다.
- 예상 길이: 18~22분.
- 업로드: YouTube(일부 공개) 또는 Google Drive(링크가 있는 모든 사용자 보기)에 올리고 URL을 보고서에 넣습니다.

---

## 0. 준비 (약 1분)

| 동작 | 설명 |
|---|---|
| 터미널에서 `npm run db:init` 실행, 테이블별 행 수 출력 확인 | DB 초기화 스크립트로 9개 테이블을 다시 만들고 시드 데이터를 넣습니다. 전체가 한 트랜잭션입니다. |
| `npm start` 실행 후 브라우저에서 `http://localhost:3000` 접속 | 첫 화면은 인기 차트 페이지입니다. |

## 1. 회원가입 (약 2분)

| 동작 | 설명 |
|---|---|
| Register → ID `a b`, 비밀번호 아무거나 → 가입 | ID는 영문·숫자·밑줄 3~20자만 허용합니다. 오류 메시지가 나옵니다. |
| ID `demo_user`, Role User → 가입 → 로그인 화면으로 이동 | 일반 사용자 가입입니다. 비밀번호는 scrypt 해시로 저장됩니다. |
| 같은 ID `demo_user`로 다시 가입 | 이미 있는 ID는 "Username is already taken."으로 거절됩니다. |
| ID `demo_admin`, Role Admin 선택 (Admin Code 칸이 나타남), 코드 `1234567890` → 가입 | 관리자 가입은 추가 코드가 필요하고, 틀리면 "Invalid admin code."입니다. |
| 같은 내용에 코드 `2022065250` → 가입 | 코드는 제 학번입니다. 관리자 계정이 만들어집니다. |

## 2. 로그인과 권한 (약 2분)

| 동작 | 설명 |
|---|---|
| Login → `demo_user`, 틀린 비밀번호 | ID가 없을 때와 같은 메시지 "Invalid username or password."를 보여 줍니다. |
| `demo_user`로 로그인 → 상단 메뉴 확인 | 일반 사용자는 My Borrows, My Reservations, Loan Stats 메뉴가 생기고 관리자 메뉴는 없습니다. |
| 주소창에 `localhost:3000/users` 입력 | 관리자 전용 페이지라 "Access Denied: Admins only." (403)입니다. |
| Logout → `demo_admin`으로 로그인 → 상단 메뉴 확인 | 관리자는 Categories, Users 메뉴가 추가로 보입니다. |
| Logout | |

## 3. 도서 목록: 검색과 정렬 (약 2분)

| 동작 | 설명 |
|---|---|
| Books (로그아웃 상태) | 제목, 저자, 카테고리, 전체 수량, 대출 가능 수량을 보여 줍니다. Murder on the Orient Express는 2권 모두 대출 중이라 0입니다. |
| Title 머리글 두 번 클릭, Author, Categories 클릭 | 제목·저자·카테고리 오름차순/내림차순 정렬입니다. |
| 검색: Title `the` → Author `tolkien` → Category `fantasy` | 대소문자 구분 없이 부분 일치로 검색합니다. 카테고리 검색 결과에서도 Dune은 "Fantasy, Science Fiction"처럼 모든 카테고리를 보여 줍니다. |
| 아무 책의 Show Instances | 복본 목록은 로그인해야 볼 수 있습니다. |

## 4. 인기 차트 (약 2분) — 대출하기 전에

| 동작 | 설명 |
|---|---|
| Charts | 최근 3개월 대출을 집계합니다. 같은 책의 복본은 합칩니다. The Hobbit 6건은 복본 3권의 대출을 합친 수입니다. |
| 전체 차트의 The Lord of the Rings (1건) 가리키기 | 이 책은 전체 대출이 5건이지만 4건이 3개월보다 오래돼 1건만 집계됩니다. |
| Popular Authors 표 | 같은 대출을 저자별로 합친 인기 저자 차트입니다. |
| 카테고리 드롭다운: Classic(기본) → Science Fiction → History | 카테고리별 인기 도서 차트입니다. 선택한 카테고리에 속한 책만 집계합니다. |

## 5. 대출과 대출 규칙 (약 3분)

| 동작 | 설명 |
|---|---|
| `alice` 로그인 → Books → The Hobbit Show Instances | 복본마다 대출자와 대출일이 보입니다. alice가 빌린 복본에만 Return 버튼이 있습니다. |
| Murder on the Orient Express Show Instances | 남이 빌린 복본은 Borrowed로 비활성화되어 있습니다. |
| The Hobbit의 다른 복본 Borrow | 같은 책은 동시에 2권 빌릴 수 없습니다: "You are already borrowing a copy of this book." (반드시 Dune을 빌리기 전에. 3권을 빌린 뒤에는 한도 메시지가 먼저 나옵니다.) |
| Books → Dune Show Instances → Borrow | 대출하면 대출 기록 페이지로 이동합니다. 반납 기한은 7일 뒤입니다. |
| 대출 기록에서 Dune 행의 Book ID(#번호) 가리키기 | 같은 책 중에서도 정확히 어떤 복본을 빌렸는지 복본 번호로 기록됩니다. |
| Books → Foundation의 대출 가능한 복본 Borrow | alice는 이제 3권을 빌린 상태라 "maximum borrowing limit (3 books)"로 거절됩니다. |
| Logout → `carol` 로그인 → My Borrows | carol은 10일 전에 빌린 책을 아직 반납하지 않았습니다. 7일 이상이면 연체입니다. |
| Books → Foundation 복본 Borrow | 연체 중인 사용자는 대출할 수 없습니다: "You have an overdue book." |

## 6. 반납과 대출 기록 (약 1분)

| 동작 | 설명 |
|---|---|
| Logout → `alice` 로그인 → My Borrows → Dune Return | 반납일이 기록되고 Return 버튼이 사라집니다. 본인 대출만 반납할 수 있습니다. |
| 대출 기록 전체 보기 | 과거 대출까지 복본 번호, 대출일, 반납일이 최신순으로 나옵니다. |

## 7. 관리자: 도서·카테고리·회원 관리 (약 4분)

| 동작 | 설명 |
|---|---|
| Logout → `admin` 로그인 → Books → Add Book | 저자와 카테고리 목록은 DB에서 불러옵니다. |
| Title `Demo Book`, Author에 새 이름 `Demo Author` 입력, Categories에서 Classic 선택 + 새 이름 `Poetry` 입력, Quantity 2 → 추가 | 새 저자와 새 카테고리는 입력하면 바로 만들어집니다. 한 책이 여러 카테고리에 속할 수 있습니다. 추가 후 그 책으로 검색된 목록이 열립니다 (2/2권). |
| 같은 제목·저자로 Quantity 1 다시 추가 | 같은 저자의 같은 제목은 새 도서가 아니라 복본만 늘어납니다 (3권). |
| Demo Book Show Instances → 복본 하나 Delete | 복본 단위로 삭제합니다. |
| The Hobbit Show Instances → alice가 빌린 복본 Delete | 대출 중인 복본은 삭제할 수 없습니다. |
| Categories → `Biography` 추가 → `biography` 다시 추가 | 카테고리 추가. 대소문자만 다른 이름은 중복으로 거절됩니다. |
| Categories → `Poetry` 삭제 → Books에서 Demo Book 확인 | 카테고리를 지우면 그 연결만 사라지고 책은 Classic으로 남습니다. |
| Demo Book의 남은 복본 2개 Delete → 목록 확인 | 마지막 복본을 지우면 도서도 함께 삭제됩니다. |
| Users → 검색 Username `a`, Role `admin` | 회원 목록과 ID·역할 검색입니다. |

## 8. 추가 기능 E1: 리뷰와 별점 (약 2분)

| 동작 | 설명 |
|---|---|
| Logout → Books → The Hobbit 제목 클릭 | 도서 상세 페이지입니다. 평균 별점 4.7(리뷰 3개)과 리뷰 목록을 보여 줍니다. 로그인해야 쓸 수 있습니다. |
| `frank` 로그인 → Books → I, Robot 제목 클릭 | frank는 이 책을 빌린 적이 있어 리뷰 작성 폼이 보입니다. |
| 4점, 코멘트 입력 → Submit | 리뷰가 저장되고 평균이 갱신됩니다. |
| 5점으로 바꿔 Update | 회원당 도서별 리뷰는 하나이므로 두 번째 작성은 수정이 됩니다 (리뷰 수는 1 그대로). |
| Delete my review | 본인 리뷰만 삭제할 수 있습니다. |
| Dune 제목 클릭 | 빌린 적 없는 책은 "Only members who have borrowed this book can review it."라고 나옵니다. |

## 9. 추가 기능 E2: 예약 대기열 (약 3분)

| 동작 | 설명 |
|---|---|
| (frank) My Reservations | frank는 Murder on the Orient Express 예약 대기 2순위입니다. 1순위는 erin입니다. |
| Logout → `demo_user` 로그인 → Murder on the Orient Express 제목 클릭 → Reserve | 모든 복본이 대출 중이고, 이 책을 빌리고 있지 않고, 대기 중인 예약도 없을 때만 예약할 수 있습니다. |
| My Reservations: 3순위 확인 → Cancel | 본인 예약은 취소할 수 있습니다. |
| Logout → `alice` 로그인 → Orient Express 상세 | alice는 이 책을 빌리고 있어서 Reserve 버튼이 없습니다. |
| My Borrows → Orient Express Return | 복본 하나가 반납되었습니다. |
| Logout → `frank` 로그인 → Books → Orient Express Show Instances → 반납된 복본 Borrow | 대기열이 있으면 가장 먼저 예약한 사람만 빌릴 수 있습니다: "This book is reserved for another user." |
| Logout → `erin` 로그인 → 같은 복본 Borrow → My Reservations | 1순위 erin은 빌릴 수 있고, 예약은 fulfilled가 됩니다. |
| Logout → `frank` 로그인 → My Reservations | 이제 frank가 1순위입니다. |

## 10. 추가 기능 S1: 평점 통계 (약 1분)

| 동작 | 설명 |
|---|---|
| Rating Stats | 통계 기능 1. 도서별 평균 별점과 리뷰 수입니다. 리뷰가 없는 책은 맨 아래에 '-'로 나옵니다. |
| Ratings by Category | 카테고리별 평균 별점, 리뷰 수, 가장 평점이 높은 책입니다. 별도 통계 테이블 없이 Review에서 매번 집계합니다. |

## 11. 추가 기능 S2: 대출 통계 (약 2분)

| 동작 | 설명 |
|---|---|
| (frank) Loan Stats | 통계 기능 2. 모든 회원은 본인의 누적 대출 수와 기한 내 반납률을 봅니다. 월별 통계와 순위는 보이지 않습니다. |
| Logout → `admin` 로그인 → Loan Stats | 관리자는 월별 대출 건수와 연체율을 봅니다. 기한 이후 반납했거나 아직 반납하지 않고 기한이 지난 대출을 연체로 셉니다. |
| Reading Ranking 표 | 회원별 누적 대출 수 순위(다독 순위)입니다. 다른 회원의 기록이 드러나므로 관리자 전용입니다. |

## 12. 마무리 (약 30초)

| 동작 | 설명 |
|---|---|
| 상단 메뉴 전체를 한 번 훑기 | 필수 기능과 추가 기능 4가지(리뷰, 예약, 평점 통계, 대출 통계)를 모두 시연했습니다. |
