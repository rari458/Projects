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
- [ ] Read the new PDF once and **submit 4-1 to the LMS by Oct 29 23:59**.

## Phase 1: Environment

PostgreSQL 18 is already installed and running in WSL.

- [ ] Create a role and a database: `sudo -u postgres createuser -P library` and `sudo -u postgres createdb -O library library`.
- [ ] Create `assignment_4/.env` with `DATABASE_URL="postgresql://library:<pw>@localhost:5432/library"`.
- [ ] Create `assignment_4/.env.example` with a placeholder URL. The submission requires an env example file.
- [ ] Run `npm install`.
- **Check:** `psql "$DATABASE_URL" -c 'select 1'` works, and `npm start` serves the dummy pages on :3000.

## Phase 2: Schema and seed data (`scripts/init_db.js`)

- [ ] Shared password helper, e.g. a new `utils/password.js` using built-in `crypto.scrypt` with a random salt. The seed script and `authController` both use it.
- [ ] `DROP TABLE IF EXISTS ... CASCADE` in dependency order, then `CREATE TABLE` for all 9 tables:
  - Users, Author, Book, BookCopy, Category, Book_Category, Loan, Review, Reservation
  - include the PKs/FKs, `ON DELETE` rules, CHECKs, UNIQUEs and the two partial unique indexes exactly as listed in CLAUDE.md's Schema section (from 4-1 report §2 and §5)
  - use `SERIAL` (int4) ids so `pg` returns numbers
- [ ] Seed data that makes every feature demonstrable:
  - 1–2 admins and 4–5 users with known passwords, written down in the README
  - about 10 books across 4–5 authors and 4–5 categories, some in several categories, with 1–4 copies each
  - loans spread over the last **5–6 months**: some older than 3 months to prove the chart filter, several months for the monthly stats, and some returned late for the overdue rate
  - one user with an unreturned loan of 7+ days (overdue) and one user holding 3 books (at the limit)
  - one book with every copy borrowed and a reservation queue
  - a handful of reviews
- **Check:** `npm run db:init` runs twice in a row without errors, and the row counts in `psql` match the seed.

## Phase 3: Authentication (`controllers/authController.js`)

- [ ] Set `adminCode = '2022065250'`.
- [ ] `postRegister`:
  - reject an empty or duplicate username
  - reject `role === 'admin'` without the exact admin code
  - force any other role to `'user'`
  - hash the password before inserting
- [ ] `postLogin`: look up the user, verify the hash, and set `session.userId`, `username` and `role`. A wrong username or password gets one generic error.
- **Check:** registering as a user works. Registering as admin with a wrong or missing code fails, and with `2022065250` it succeeds. The admin nav shows Categories and Users, and the user nav doesn't. A non-admin requesting `/users` gets a 403.

## Phase 4: Book list (`bookController.getBooksPage`, `getBookInstances`)

- [ ] One query per book row with title, author name, categories joined by `string_agg(... ORDER BY ...)`, total copies and available copies.
- [ ] Search with `ILIKE '%' || $1 || '%'` on the column picked by `searchBy` (title, author or category). A category search must still show *all* of the book's categories.
- [ ] Sort through a whitelist map (`title`/`author`/`categories` → SQL expression, `asc`/`desc`), falling back to `title asc`.
- [ ] Instances API: return every copy with `status`, `borrowing_id`, `borrowed_by`, `borrowed_by_id` and a formatted `borrow_date`.
- **Check:** each sortable column works in both directions. A search containing `%` or `'` doesn't break. `sortBy=foo` falls back to title. The instances panel shows who borrowed what.

## Phase 5: Borrow and return (`postBorrowBook`, `postReturnBook`, `borrowingController`)

- [ ] Borrow is a single transaction:
  1. `SELECT ... FOR UPDATE` the copy and require `available`
  2. the user holds fewer than 3 unreturned loans
  3. the user has no unreturned loan of the same `book_id`
  4. the user is not overdue (`>= due_date`)
  5. the reservation rule from Phase 0
  6. INSERT the loan with `due_date = CURRENT_DATE + 7`, set the copy to `borrowed`, and mark any reservation fulfilled

  Each failure gets a specific 400 message.
- [ ] Return: `UPDATE loan SET return_date = CURRENT_DATE WHERE loan_id = $1 AND user_id = $2 AND return_date IS NULL`. Zero rows updated means 400 or 403. Set the copy back to `available` in the same transaction.
- [ ] Borrowings page: all of the user's loans with the copy id, title, author and formatted dates, newest first.
- **Check:** a 4th book is refused. A 2nd copy of the same title is refused. The overdue seed user is refused. A crafted POST to another user's loan is refused. Returning twice is refused. The history shows the exact copy id.

## Phase 6: Admin features

- [ ] `getAddBookPage`: real author and category lists.
- [ ] `postAddBook` in one transaction:
  - normalize `categories` from missing, a string or an array
  - parse `id:<n>` as an existing row; treat anything else as a new name and `INSERT ... ON CONFLICT (name) DO UPDATE ... RETURNING id`
  - insert the book, N copies, and the `Book_Category` rows
- [ ] `postDeleteBookInstance`: refuse if the copy is borrowed, delete it, and delete the book when no copies remain.
- [ ] **Add category**, which the skeleton is missing: a new `POST /categories/add` route with `isAuthenticated, isAdmin`, a form in `categories.ejs`, and a duplicate-name check.
- [ ] `postDeleteCategory`: delete the category. `Book_Category` rows cascade, and books keep their other categories.
- [ ] `getUsersPage`: list users, with search by username or role through a whitelist plus `ILIKE`.
- **Check:** a book added with a new author and two new categories shows up correctly. Deleting copies one by one removes the book at the end. Deleting a category leaves its books in their other categories.

## Phase 7: Charts (`chartController`, `charts.ejs`)

- [ ] Overall popular books: Loan → BookCopy → Book with `loan_date >= CURRENT_DATE - INTERVAL '3 months'`, `GROUP BY book_id`, `ORDER BY count DESC`, `LIMIT 10`.
- [ ] Per-category chart: the same query filtered by `Book_Category.category_id = selected`. Default to the first category, and key the result object by category name.
- [ ] **Popular authors** chart (from the README): group by author and add a table to `charts.ejs`.
- **Check:** loans older than 3 months don't count, copies of the same book add up, and switching the dropdown updates the category table.

## Phase 8: Extra features (as committed in the 4-1 report)

| # | Feature | Pieces |
|---|---|---|
| E1 | Reviews | a `/books/:id` detail page listing reviews; a form shown only to users with a loan of the book; edit and delete your own review |
| E2 | Reservations | a Reserve button on the detail page or in the instances panel when nothing is available; `/reservations` (my queue, cancel); the borrow rule from Phase 0 |
| S1 | Rating statistics | `/stats/ratings`: average rating and review count per book; average, count and top-rated book per category |
| S2 | Loan statistics | `/stats/loans`: monthly loans and overdue rate (admin); member ranking by total loans, 다독 순위 (admin only, as promised in the 4-1 report); personal totals and on-time return rate (any user) |

- [ ] Each feature needs a controller (e.g. `reviewController`, `reservationController`, `statsController`), routes with the right middleware, views, and header nav links.
- **Check:** each feature works end to end with seed data. Reservation hand-off: user A holds the last copy, B reserves, A returns, C is refused, B can borrow.

## Phase 9: Full test pass

- [ ] Run every **Check** above again on a fresh `npm run db:init`.
- [ ] Security: every query uses `$n` parameters, and ORDER BY and search columns come only from whitelists. Every admin route has `isAdmin`. Usernames are restricted to a safe character set, because `books.ejs` builds the instances table with unescaped template literals.
- [ ] No `dummy*` variables or `TODO`s remain (`grep -rn "dummy\|TODO" controllers scripts`).

## Phase 10: Deliverables

- [ ] `README.md` 실행 방법: PostgreSQL setup, `.env`, `npm install`, `npm run db:init`, `npm start`, and the seed accounts.
- [ ] Report PDF covering:
  1. name, student ID and tech stack (Node.js, Express 5, EJS, PostgreSQL 18, express-session, pg, Choices.js)
  2. each required feature with what was implemented and screenshots
  3. how to run it locally
  4. the extra features, with their purpose and how they work
  5. the demo video URL

  Mention any schema changes from 4-1 and why.
- [ ] Demo video with narration or subtitles covering **every** feature. A suggested order: register (user, admin with a wrong and the right code) → login → books search and sort → borrow, including each rule violation → return → history → charts → admin add book, delete copy, add and delete category, users → E1, E2, S1, S2.
- [ ] ZIP `assignment4_2022065250_문상철.zip` with the source (no `node_modules`, no `.env`), `.env.example`, the init script and the report PDF.
