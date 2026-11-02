# Assignment #4 Roadmap

The plan for finishing Assignment #4-1 (schema report, due **Thu 2026-10-29 23:59**) and #4-2 (web app, report and demo video, due **Tue 2026-11-10 23:59**).

How to work through it: Claude generates the code for each step, you apply it, then you run the **Check** items before ticking the step off. Commit after each phase, from `~/Projects`, whose repo tracks this folder.

## Timeline

| Dates | Phases |
|---|---|
| Oct 24–26 | 0 Decisions · 1 Environment · 2 Schema and seed data |
| Oct 27–29 | Update the 4-1 report if the schema changed, then **submit 4-1** · 3 Auth |
| Oct 30–Nov 2 | 4 Book list · 5 Borrow/return · 6 Admin |
| Nov 3–6 | 7 Charts · 8 Extra features |
| Nov 7 | 9 Full test pass |
| Nov 8–9 | 10 README, report, demo video |
| Nov 10 | Build the ZIP and submit (buffer day) |

---

## Phase 0: Settle the design decisions

All decided on 2026-10-24 using the **bold** recommendations. The schema-level items (Author, Users, casing, FK rules, overdue rule, PostgreSQL syntax) are applied to `assignment4_1_report.html`, and the PDF still renders on 4 pages. The reservation and review rules are app-level and get implemented in Phases 5 and 8.

- [x] **Author storage.** The 4-1 schema stores `author` as text on `Book`, but the skeleton's add-book page picks authors from a list (`id:<n>`) and says to create new ones, and the README asks for a popular-**author** chart.
  **Recommendation: add an `Author(author_id, name UNIQUE)` table and give `Book` an `author_id` FK** (one author per book, which matches the single-select form). 4-1 isn't due yet, so update the report to match.
- [x] **Users key.** **Keep the 4-1 design, with `user_id VARCHAR` as the PK and login ID**, and store it in `session.userId`. The register form only sends username and password, so **make `name` and `email` nullable**, or add optional inputs for them. **`admin_code` was dropped**: the code is only checked at registration, and storing it would repeat the same value in every admin row.
- [x] **Casing.** **Store lowercase values with CHECK constraints**: `role IN ('user','admin')` and `status IN ('available','borrowed','maintenance')`. The views and middleware compare against lowercase. Note the change in the report.
- [x] **Copy status.** `BookCopy.status` duplicates what `Loan.return_date` already says. **Keep the column, as in the design, and update both in the same transaction** on borrow and return.
- [x] **Deleting copies.** **Refuse to delete a copy that's currently borrowed. Otherwise delete it, with `Loan.copy_id ON DELETE CASCADE`. When the last copy goes, delete the `Book`**, which cascades to `Book_Category`, `Review` and `Reservation`. Trade-off for the report: that copy's loan history disappears too. The alternative is soft-delete.
- [x] **Overdue rule.** "7일 이상" means overdue once `CURRENT_DATE >= due_date`, not `>`. Fix this in the 4-1 report as well.
- [x] **Reservation rules**, which change how borrowing works:
  - You can reserve a book only when none of its copies are available, you don't currently hold a copy, and you have no active reservation for it.
  - While a book has active reservations, only the **earliest reserver** may borrow a returned copy. Everyone else gets "reserved for another user".
  - Borrowing marks that user's reservation `fulfilled`, and users can cancel their own reservations.
- [x] **Review rules.** Only users with at least one loan of the book can review it. Keep `UNIQUE(user_id, book_id)`, `rating` 1–5, and let users edit or delete their own review.
- [x] **Extra features: keep exactly 2 statistics** (rating stats and loan/overdue stats). Don't add any other counts, averages or rankings to other pages, because they could be read as a third statistic. The popular book and author charts are *required* features, not extras.
- [x] Report redesigned from scratch on 2026-10-26 (12 pages, Chen ER diagram with participation, schema diagram, constraint tables) and re-exported to `assignment4_1_2022065250_문상철.pdf`.
- [x] Read the new PDF once and **submit 4-1 to the LMS by Oct 29 23:59**. Submitted 2026-10-26.

## Phase 1: Environment

PostgreSQL 18 is already installed and running in WSL.

- [x] Create a role and a database: `sudo -u postgres createuser -P library` and `sudo -u postgres createdb -O library library`.
- [x] Create `assignment_4/.env` with `DATABASE_URL="postgresql://library:<pw>@localhost:5432/library"`.
- [x] Create `assignment_4/.env.example` with a placeholder URL. The submission requires an env example file.
- [x] Run `npm install`.
- **Check:** `psql "$DATABASE_URL" -c 'select 1'` works, and `npm start` serves the dummy pages on :3000.

## Phase 2: Schema and seed data (`scripts/init_db.js`)

- [x] Shared password helper, e.g. a new `utils/password.js` using built-in `crypto.scrypt` with a random salt. The seed script and `authController` both use it.
- [x] `DROP TABLE IF EXISTS ... CASCADE` in dependency order, then `CREATE TABLE` for all 9 tables:
  - Users, Author, Book, BookCopy, Category, Book_Category, Loan, Review, Reservation
  - include the PKs/FKs, `ON DELETE` rules, CHECKs, UNIQUEs and the two partial unique indexes exactly as listed in CLAUDE.md's Schema section (from 4-1 report §2 and §5)
  - use `SERIAL` (int4) ids so `pg` returns numbers
- [x] Seed data that makes every feature demonstrable:
  - 1–2 admins and 4–5 users with known passwords, written down in the README
  - about 10 books across 4–5 authors and 4–5 categories, some in several categories, with 1–4 copies each
  - loans spread over the last **5–6 months**: some older than 3 months to prove the chart filter, several months for the monthly stats, and some returned late for the overdue rate
  - one user with an unreturned loan of 7+ days (overdue) and one user holding 3 books (at the limit)
  - one book with every copy borrowed and a reservation queue
  - a handful of reviews
- **Check:** `npm run db:init` runs twice in a row without errors, and the row counts in `psql` match the seed. Passed 2026-10-27.

## Phase 3: Authentication (`controllers/authController.js`)

- [x] Set `adminCode = '2022065250'`.
- [x] `postRegister`:
  - reject an empty or duplicate username
  - reject `role === 'admin'` without the exact admin code
  - force any other role to `'user'`
  - hash the password before inserting
- [x] `postLogin`: look up the user, verify the hash, and set `session.userId`, `username` and `role`. A wrong username or password gets one generic error.
- **Check:** registering as a user works. Registering as admin with a wrong or missing code fails, and with `2022065250` it succeeds. The admin nav shows Categories and Users, and the user nav doesn't. A non-admin requesting `/users` gets a 403. Passed 2026-10-27.

## Phase 4: Book list (`bookController.getBooksPage`, `getBookInstances`)

- [x] One query per book row with title, author name, categories joined by `string_agg(... ORDER BY ...)`, total copies and available copies.
- [x] Search with `ILIKE $1` on the column picked by `searchBy` (title, author or category). The pattern comes from `containsPattern` in `utils/search.js`, which escapes `%`, `_` and `\`. A category search must still show *all* of the book's categories.
- [x] Sort through a whitelist map (`title`/`author`/`categories` → SQL expression, `asc`/`desc`), falling back to `title asc`.
- [x] Instances API: return every copy with `status`, `borrowing_id`, `borrowed_by`, `borrowed_by_id` and a formatted `borrow_date`.
- **Check:** each sortable column works in both directions. A search containing `%` or `'` doesn't break. `sortBy=foo` falls back to title. The instances panel shows who borrowed what. Passed 2026-11-01.

## Phase 5: Borrow and return (`postBorrowBook`, `postReturnBook`, `borrowingController`)

- [x] Borrow is a single transaction:
  1. `SELECT ... FOR UPDATE` the copy and require `available`
  2. the user holds fewer than 3 unreturned loans
  3. the user has no unreturned loan of the same `book_id`
  4. the user is not overdue (`>= due_date`)
  5. the reservation rule from Phase 0
  6. INSERT the loan with `due_date = CURRENT_DATE + 7`, set the copy to `borrowed`, and mark any reservation fulfilled

  Each failure gets a specific 400 message.
- [x] Return: `UPDATE loan SET return_date = CURRENT_DATE WHERE loan_id = $1 AND user_id = $2 AND return_date IS NULL`. Zero rows updated means 400 or 403. Set the copy back to `available` in the same transaction.
- [x] Borrowings page: all of the user's loans with the copy id, title, author and formatted dates, newest first.
- **Check:** a 4th book is refused. A 2nd copy of the same title is refused. The overdue seed user is refused. A crafted POST to another user's loan is refused. Returning twice is refused. The history shows the exact copy id. Only the first waiting reserver can borrow a returned copy. Passed 2026-11-01.

## Phase 6: Admin features

- [x] `getAddBookPage`: real author and category lists.
- [x] `postAddBook` in one transaction:
  - normalize `categories` from missing, a string or an array
  - parse `id:<n>` as an existing row; treat anything else as a new name and `INSERT ... ON CONFLICT (name) DO UPDATE ... RETURNING id`
  - insert the book, N copies, and the `Book_Category` rows

  As built (`resolveNamedRow`): a typed name reuses an existing author or category in any letter case. A title that already exists for the same author gets the new copies and categories instead of a second `Book` row. Quantity is 1–100. After adding, the list opens filtered to that title.
- [x] `postDeleteBookInstance`: refuse if the copy is borrowed, delete it, and delete the book when no copies remain. Locks the copy, then the book, so two admins deleting the last two copies at once still remove the book. Passed 2026-11-01.
- [x] **Add category**, which the skeleton is missing: a new `POST /categories/add` route with `isAuthenticated, isAdmin`, a form in `categories.ejs`, and a duplicate-name check.

  As built: the name is trimmed and must be 1–50 characters. A single `INSERT ... SELECT ... WHERE NOT EXISTS (lower(name) match) ON CONFLICT DO NOTHING` refuses a duplicate in any letter case, and `rowCount === 0` gives the duplicate message. New categories list last (`ORDER BY category_id`).
- [x] `postDeleteCategory`: delete the category. `Book_Category` rows cascade, and books keep their other categories. An unknown id is a 404.
- [x] `getUsersPage`: list users, with search by username or role through a whitelist plus `ILIKE`. `id` and `username` are both `user_id`, the default `searchBy` is `username`, and the search goes through `containsPattern`, so `_` and `%` match literally.
- `httpError` moved from `bookController` to `utils/httpError.js`, shared with `categoryController`.
- **Check:** a book added with a new author and two new categories shows up correctly. Deleting copies one by one removes the book at the end. Deleting a category leaves its books in their other categories. Passed 2026-11-01 (6a) and 2026-11-02 (6b).

  6b was checked on a fresh throwaway DB through the real routes, controllers and views:
  - adding `Poetry`, then refusing `poetry`, padded `  POETRY  `, blank, 51-character, missing and doubled names
  - HTML in a name is escaped
  - deleting Fantasy and History keeps the other categories of those books
  - a missing or non-numeric id is a 404
  - users list 7 rows; username `a` finds 5, role `admin`/`user` finds 1/6, and `_` or `%` finds none
  - a regular user gets 403 and a logged-out visitor goes to `/login` on all four routes

## Phase 7: Charts (`chartController`, `charts.ejs`)

- [x] Overall popular books: Loan → BookCopy → Book with `loan_date >= CURRENT_DATE - INTERVAL '3 months'`, `GROUP BY book_id`, `ORDER BY count DESC`, `LIMIT 10`.
- [x] Per-category chart: the same query filtered by `Book_Category.category_id = selected`. Default to the first category, and key the result object by category name.
- [x] **Popular authors** chart (from the README): group by author and add a table to `charts.ejs`.

  As built:
  - One `POPULAR_BOOKS_SQL` serves both book charts. `$1 = NULL` counts every book, and a category id keeps only that category's books (`EXISTS` on `Book_Category`). Each row still lists all of the book's categories.
  - Ties sort by title (books) or name (authors).
  - The dropdown is alphabetical. A missing, unknown or malformed `categoryId` falls back to its first entry.
  - The authors card sits between the overall table and the category table.
- **Check:** loans older than 3 months don't count, copies of the same book add up, and switching the dropdown updates the category table. Passed 2026-11-02.

  On a fresh seed:
  - LOTR shows 1 of its 5 loans, because the other 4 are older than 3 months.
  - The Hobbit's 6 loans span copies 1–3.
  - The chart total of 33 equals the loans since the cutoff.
  - Classic is the default; Science Fiction and History switch correctly.
  - `abc`, `999` and a repeated `categoryId` fall back to Classic.
  - A category with no loans shows an empty table, and no categories at all still renders.

## Phase 8: Extra features (as committed in the 4-1 report)

| # | Feature | Pieces |
|---|---|---|
| E1 | Reviews | a `/books/:id` detail page listing reviews; a form shown only to users with a loan of the book; edit and delete your own review |
| E2 | Reservations | a Reserve button on the detail page or in the instances panel when nothing is available; `/reservations` (my queue, cancel); the borrow rule from Phase 0 |
| S1 | Rating statistics | `/stats/ratings`: average rating and review count per book; average, count and top-rated book per category |
| S2 | Loan statistics | `/stats/loans`: monthly loans and overdue rate (admin); member ranking by total loans, 다독 순위 (admin only, as promised in the 4-1 report); personal totals and on-time return rate (any user) |

- [x] Each feature needs a controller (e.g. `reviewController`, `reservationController`, `statsController`), routes with the right middleware, views, and header nav links.

Split into three rounds of typing, each checked and committed on its own:

- [x] **8a: book detail page and E1.** Passed 2026-11-02, on a fresh seed:
  - Hobbit shows 4.7 from 3 reviews.
  - alice gets her review prefilled, frank can review I, Robot but not Dune, and a crafted POST on Dune is a 403.
  - Writing, editing (the count stays 1) and deleting work; deleting again is a 404.
  - Bad ratings and a 1001-character comment are 400s, and HTML in a comment is escaped.
  - Logged-out POSTs go to `/login`, `/books/999999` is a 404, and `/books/add` still routes.
  - `GET /books/:id` (public, `bookController.getBookDetailPage`), with titles in the book list linking to it. It shows the book, the average rating and review count (as promised in the 4-1 report's E1), and every review.
  - `reviewController`:
    - `POST /books/:id/review` writes or replaces your review, in one `INSERT ... SELECT ... WHERE EXISTS (a loan of the book) ON CONFLICT (user_id, book_id) DO UPDATE`
    - `POST /books/:id/review/delete` deletes your own review
  - The form appears only for users with a loan of the book, and is prefilled when you already have a review.
- [x] **8b: E2.** A Reserve button on the detail page, `/reservations` (my queue with positions, cancel), and a header link.

  As built (`reservationController`):
  - Reserving runs in a transaction that locks the book's copies `FOR SHARE`. It refuses when a copy is available, when the user is borrowing a copy, and (through `ON CONFLICT ... WHERE status = 'waiting' DO NOTHING` on the partial unique index) when the user is already waiting.
  - Cancel updates only the user's own waiting reservation.
  - The queue position counts waiting rows with `(reserved_at, reservation_id) <=` the user's own, the same order the borrow check uses.
  - Trade-off for the report: if #1 can't borrow (at the limit or overdue), the returned copy waits until they cancel, because there's no expiry.

  Passed 2026-11-03, on a fresh seed:
  - The seed queue shows erin #1 and frank #2. bob reserves as #3, and a second try is refused.
  - Holding a copy, a book with a copy available, and a missing book are all refused.
  - Cancelling someone else's reservation, or one that's no longer waiting, is refused.
  - The ROADMAP hand-off works: alice returns, frank and admin are refused, erin borrows, frank becomes #1, then borrows after dave returns.
  - Logged out goes to `/login`.
  - The 8a checks still pass.
- [x] **8c: S1 and S2.** `/stats/ratings` and `/stats/loans`, with header links.

  As built (`statsController`):
  - `/stats/ratings` is public. It shows each book's average (2 decimals) and review count, and each category's average, review count and top-rated book (highest average, then more reviews, then title). The category query is the report's, with `LEFT JOIN Book_Category` so a category without books still shows.
  - `/stats/loans` needs login. Every member sees their own loans, returned loans, loans returned on time, and the on-time rate over returned loans.
  - Only an admin also gets loans and overdue rate per month (the report's overdue rule: `COALESCE(return_date, CURRENT_DATE) >= due_date`) and the reading ranking (`RANK()`, every user including 0-loan ones). Those two queries run only for admins.

  Passed 2026-11-03: every number on both pages matched an independent recomputation in JS from the raw rows.
  - Hobbit 4.67 from 3; Classic 4.57 with LOTR as top.
  - alice 9 / 7 / 4 / 57.1%.
  - The ranking has alice, bob and dave tied at 1.
  - Logged out goes to `/login`; members see only My Reading.
- **Check:** each feature works end to end with seed data. Reservation hand-off: user A holds the last copy, B reserves, A returns, C is refused, B can borrow. Passed 2026-11-03 (8a, 8b and 8c, with the 8a and 8b suites re-run after 8c).

## Phase 9: Full test pass

- [x] Run every **Check** above again on a fresh `npm run db:init`. Passed 2026-11-03.
  - Phase 2: `db:init` runs twice in a row with the seed counts, and all 13 constraint probes are rejected. These cover:
    - the CHECKs, both partial unique indexes and `UNIQUE(user_id, book_id)`
    - both `RESTRICT` deletes, and `NOT NULL` on a foreign key
    - the Book delete cascade
  - Phases 3–7: one harness wired like `index.js`, with a real `express-session` and real logins: **83/83 passed, no 500s**. It covers:
    - registration rules, the admin code, hashing, one login error message, session-ID rotation and logout
    - search and sort and their whitelists, the instances API
    - each borrow and return rule
    - add-book, delete-copy, categories, users, and 403 or `/login` on every admin route
    - the charts, recomputed from raw loans
    - every nav link for each role
  - Phase 8: the 8a, 8b and 8c suites all pass again on fresh seeds.
- [x] Security: every query uses `$n` parameters, and ORDER BY and search columns come only from whitelists. Every admin route has `isAdmin`. Usernames are restricted to a safe character set, because `books.ejs` builds the instances table with unescaped template literals.
  - All confirmed.
    - The only interpolated SQL pieces are `SEARCH_CONDITIONS[searchBy]` (behind `Object.hasOwn`), the `sortBy`/`sortOrder` whitelists, `NAMED_ROWS[kind]` with literal kinds, and constants.
    - Every admin route has `isAuthenticated, isAdmin`.
    - The only `<%-` besides the header include is in the unused skeleton file `views/index.ejs`.
  - Found and fixed (2026-11-03). Verified through the real `index.js`: crafted arrays give 401/400, normal login and register still work, a forced 500 shows only `Internal Server Error`, 404 messages still show, the cookie carries `SameSite=Lax`, and the 83-check pass still passes.
    - `postLogin` and `postRegister` crashed with a 500 and showed the JS error when a field was sent twice (an array). They now accept only strings, like the other controllers.
    - The error handler showed raw 500 messages (SQL text). It now shows `Internal Server Error` for 5xx and still logs the stack.
    - The session cookie now sets `sameSite: 'lax'` explicitly.
  - Known and left as is, for the report:
    - no CSRF tokens (SameSite=Lax covers cross-site form posts)
    - the skeleton's session secret is hard-coded in `index.js` in a public repo (sessions are server-side and their IDs random, so knowing the secret doesn't let anyone forge a valid session)
- [x] No `dummy*` variables or `TODO`s remain. Checked over all source folders, not just `controllers scripts`.

## Phase 10: Deliverables

- [x] `README.md` 실행 방법: PostgreSQL setup, `.env`, `npm install`, `npm run db:init`, `npm start`, and the seed accounts. Rewritten 2026-11-03 in Korean as a project README:
  - name and student ID, the tech stack with versions, and the 6 run steps (including creating the DB user and database)
  - the seed accounts with their starting state, and the admin code
  - required and extra features with routes, the project layout
  - the assignment's original requirement checklist, now ticked
- [x] `DEMO_SCRIPT.md`: a 12-scene recording script with a Korean narration or subtitle line for each action, ordered so each scene leaves the seed in the state the next one needs (the charts come before any borrowing; the same-book refusal comes before alice reaches 3 books). Dry-run in full against the app with real logins on a fresh seed, 56/56. Not part of the ZIP.
- [ ] Report PDF covering:
  1. name, student ID and tech stack (Node.js, Express 5, EJS, PostgreSQL 18, express-session, pg, Choices.js)
  2. each required feature with what was implemented and screenshots
  3. how to run it locally
  4. the extra features, with their purpose and how they work
  5. the demo video URL

  Mention any schema changes from 4-1 and why.
- [ ] Demo video with narration or subtitles covering **every** feature. A suggested order: register (user, admin with a wrong and the right code) → login → books search and sort → borrow, including each rule violation → return → history → charts → admin add book, delete copy, add and delete category, users → E1, E2, S1, S2.
- [ ] ZIP `assignment4_2022065250_문상철.zip` with the source (no `node_modules`, no `.env`), `.env.example`, the init script and the report PDF.
