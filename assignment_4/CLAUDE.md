# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working rule

Never edit, write, or create code files (`.js`, `.ejs`, `.css`, `.sql`, `package.json`, …). Generate the code in the reply, naming the target file and location, and the user applies it by hand. Markdown (`.md`) and HTML (`.html`) files, such as the reports, may be edited directly. `.ejs` views are code and stay show-don't-edit.

`ROADMAP.md` holds the phased plan, the design decisions and the checklists. Read it to see what's next, and tick off items there as they're completed.

## Context

DBMS class Assignment #4-2: a library management web app (login, book search/sort, borrow/return, popularity charts, admin book/category/user management) built on the PostgreSQL schema designed in Assignment #4-1. Due 2026-11-10 23:59 (the 4-1 report is due 2026-10-29 23:59).

- This folder (`~/Projects/assignment_4/`) is one flat tree. It holds the app (the instructor's skeleton), the specs, the 4-1 report, `ROADMAP.md` and this file.
- `~/projects/` (lowercase) is the stale workspace this tree was flattened from. Nothing there is current, so never edit it.
- Git: this folder has no `.git` of its own. The `~/Projects` repo tracks it as plain files and pushes to github.com/rari458/Projects, which is **public**, so run git from `~/Projects`. That repo's `.gitignore` keeps out the instructor's spec PDFs (`assignment_4/Assignment4_*.pdf`), and this folder's own `.gitignore` keeps out `node_modules/` and `.env`. The instructor's skeleton history (4 commits, `origin` = github.com/hongjun9904/assignment_4) is kept in `~/assignment_4.git.bak`. Don't run git unless the user asks.
- The specs are `Assignment4_1.pdf` (the full feature list) and `Assignment4_2.pdf` (the submission rules). The student's 4-1 schema report has its source in `assignment4_1_report.html` and is submitted as `assignment4_1_2022065250_문상철.pdf`, both in this folder. The report is the source of truth for the schema and planned extra features. The PDF is printed from the HTML with headless Chrome, run from this folder: `~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome --headless --no-sandbox --no-pdf-header-footer --print-to-pdf=assignment4_1_2022065250_문상철.pdf file://$PWD/assignment4_1_report.html`. There's no page limit (12 pages as of 2026-10-26); only §4 (ER diagram) and §5 (relation schema) force a page break. Both diagrams are inline SVG drawn to match §2–§5, so a schema change means editing the SVG too. After any edit, re-export and look at the rendered pages, not just the page count.
- Submission: `assignment4_2022065250_문상철.zip` containing the source, the DB init script, an env example file (`.env` is gitignored, so use e.g. `.env.example`), and a report PDF. The report covers the tech stack, each feature with screenshots, local run instructions, the extra features, and a demo video URL. Because the spec PDFs, the 4-1 report files, `CLAUDE.md` and `ROADMAP.md` sit beside the source, build the zip from an explicit file list rather than zipping the whole folder, and always leave out `node_modules/` and `.env`.
- Extra features: the 4-1 spec requires **≥3 extra features, of which exactly 2 are statistics**. The README's "최소 1개" is looser, so follow the spec. The 4-1 report committed to: Review (1–5 rating plus comment, only for users who borrowed the book), Reservation (a queue for when every copy is borrowed), per-book/per-category rating stats, and monthly loan/overdue-rate stats. None of these have routes or views in the skeleton yet.

## Commands

The environment is WSL2 with Node 22 and PostgreSQL 18. Run commands from this folder (the project root), because `views/`, `public/` and `.env` resolve against the working directory:

```bash
npm install
# .env: DATABASE_URL="postgresql://{user}:{password}@{host}:{port}/{db}"
npm run db:init   # scripts/init_db.js: drop + recreate tables
npm start         # http://localhost:3000 (port hard-coded in index.js)
```

There is no test suite or linter, and `npm test` exits 1 on purpose. To verify a change, run the app and check the DB with `psql`. `dotenv` loads `.env` only into the Node process, so load it into the shell first: `set -a; . ./.env; set +a; psql "$DATABASE_URL"`. Edits to EJS views take effect on the next request (view cache is off unless `NODE_ENV=production`). Edits to JS need a server restart. Sessions use express-session's default in-memory store, so every restart logs everyone out. `init_db.js` catches and logs its own errors, so `npm run db:init` exits 0 even when it fails. Read its output.

## Architecture

Express 5 + EJS + `pg` + `express-session`, CommonJS.

- `index.js`: app setup. It serves `public/`, serves `node_modules` at `/modules` (add-book loads Choices.js this way), and exposes the session to every view through `res.locals.session`. Only `express.urlencoded` is mounted, with no `express.json()`, so new POST endpoints should take HTML form posts. `/` redirects to `/charts`. A generic error handler renders `pages/error`. The page shows only `err.message`, and `err.status` sets just the HTTP status, so a message has to make sense on its own.
- `routes/routes.js`: the full route table. Access control is per route through `isAuthenticated` / `isAdmin` in `middleware/authMiddleware.js`. `isAuthenticated` redirects to `/login`, even for the JSON instances API, and `isAdmin` raises a 403. `/charts` and `/books` are public.
- Borrow and return are both handled in `bookController` (`postBorrowBook`, `postReturnBook`), even though the return route is `/borrowings/:id/return`. `borrowingController` only renders the history page.
- `config/db.js`: exports `query(text, params)` and the `pool`. Use `pool.connect()` + `BEGIN`/`COMMIT` for multi-statement operations (borrowing, adding a book with copies/authors/categories, deletes).
- Controllers report rule violations with `err = new Error(msg); err.status = 400; return next(err);`, which renders the error page.
- Session keys: `userId`, `username`, `role`. The header and `isAdmin` compare against lowercase `'admin'`, and the register form posts `role` as `user`/`admin`.
- `views/pages/*.ejs` are each a full HTML document that includes `components/header.ejs`. `views/index.ejs` is unused (it includes a nonexistent `partials/header`).

## Skeleton state

Search for `TODO` to find the work. Every controller currently renders hard-coded `dummy*` arrays. Replace them with queries and delete the dummies.

- `postLogin` logs everyone in as admin `userId = 1`. `postRegister` does nothing.
- `adminCode` in `authController.js` must be the student ID `2022065250`.
- `scripts/init_db.js` is empty. Charts only show loans from the last 3 months, so seed data with recent loan dates makes the demo work.
- The spec says admins can **add** categories, but the skeleton only has a delete route and button. Categories can currently be created only as a side effect of add-book.
- The README asks for a popular **author** chart too, but `charts.ejs` has only the two book tables.

## Data contract the views expect

Queries must return these field names. Alias them in SQL, because the 4-1 schema names differ.

| View / endpoint | Locals / fields |
|---|---|
| `pages/books` | `books[]`: `id, title, author, categories` (display string), `total_quantity, available_quantity`. Also `sortBy` (`title`/`author`/`categories`), `sortOrder` (`asc`/`desc`), `query`, `searchBy` (`title`/`author`/`category`). The controller destructures an unused `sortedBy` and reads `req.query.sortBy`. ORDER BY can't take a bind parameter, so whitelist the column and direction. The view's sort-header links send `query` and `searchBy` back as empty strings when no search is active, without URL-encoding them, so treat `''` as no search and default `searchBy`. |
| `GET /api/books/:id/instances` (JSON, rendered client-side in `books.ejs`) | `[{ id, status, borrowing_id, borrowed_by, borrowed_by_id, borrow_date }]`. Borrow shows only when `status === 'available'` (lowercase). Return shows only when `borrowed_by_id == session.userId`, and the dummy data omits `borrowed_by_id`. Here `borrowed_by` and `borrowed_by_id` are both `user_id`. `createInstancesTable` interpolates these fields into `innerHTML` unescaped, and `session.userId` reaches that script HTML-escaped inside a JS string, so restrict usernames to a safe character set at registration. |
| `POST /books/add` body | `title`, `quantity`, `authors` (one value), `categories` (missing, a string, or an array). Each value is `id:<n>` for an existing row or raw text for a name newly typed into Choices.js, so normalize and insert the new names. |
| `pages/borrowings` | `id` (the loan id, used by the Return form), `book_instance_id, book_title, book_author, borrow_date, return_date`. Return shows while `return_date` is falsy. |
| `pages/charts` | `popularBooks[]` and `popularBooksByCategory` (object keyed by category name, one table per key) with rows of `title, author, categories, borrow_count`. Also `categories[]` with `id, name`, and `selectedCategoryId`. The view compares `selectedCategoryId === category.id`, so ids must be JS numbers (`SERIAL`/int4; `BIGSERIAL` and `COUNT(*)` come back from `pg` as strings). When no `categoryId` is given, default to the first category so the table matches the dropdown. The view prints one table per key with no heading, so put only the selected category in the object. |
| `pages/categories` | `categories[]`: `id, name` |
| `pages/users` | `users[]`: `id, username, role` (`id` and `username` are both `user_id`), plus `searchBy` (`username`/`role`) and `query` |

`pg` returns DATE/TIMESTAMP columns as JS `Date` objects, and the views print values as-is. Format them with `to_char(...)` in SQL or in JS. This matters most in the instances JSON, where a `Date` serializes as a UTC ISO string, and a KST date then shows as the previous day.

## Schema (4-1 report, redesigned 2026-10-26)

`init_db.js` must match this exactly; the report's §2 has every type and default and §5.2–5.3 every constraint. 8 entities, 9 relations, all ids `SERIAL` except `user_id`. Every FK is `NOT NULL`, and every `created_at`/`reserved_at` defaults to `now()`:

- `Users(user_id VARCHAR(20) PK CHECK (user_id ~ '^[A-Za-z0-9_]{3,20}$'), password_hash NOT NULL, name NULL, email UQ NULL, role NOT NULL DEFAULT 'user' CHECK IN ('user','admin'), created_at)`. `user_id` is the login ID, and the CHECK is what keeps it safe to print unescaped in `books.ejs`. The admin code is checked at registration and never stored.
- `Author(author_id PK, author_name UQ NOT NULL)`
- `Book(book_id PK, isbn UQ NULL, title NOT NULL, author_id FK→Author ON DELETE RESTRICT, publisher NULL, published_year SMALLINT NULL, created_at)`: one row per title, one author per book. The add-book form only sends title, author, categories and quantity.
- `BookCopy(copy_id PK, book_id FK→Book ON DELETE CASCADE, call_number UQ NULL, status NOT NULL DEFAULT 'available' CHECK IN ('available','borrowed','maintenance'), acquired_date NOT NULL DEFAULT CURRENT_DATE)`: one row per physical copy. The skeleton calls these "book instances".
- `Category(category_id PK, category_name UQ NOT NULL, description NULL)`, `Book_Category(book_id, category_id)` composite PK, both FKs `ON DELETE CASCADE`
- `Loan(loan_id PK, user_id FK ON DELETE RESTRICT, copy_id FK→BookCopy ON DELETE CASCADE, loan_date NOT NULL DEFAULT CURRENT_DATE, due_date NOT NULL CHECK (due_date > loan_date), return_date NULL CHECK (return_date >= loan_date))`, plus `CREATE UNIQUE INDEX ... ON Loan(copy_id) WHERE return_date IS NULL`. The app inserts `due_date = loan_date + 7`; the CHECK is deliberately not an equality (report §8.1). Loans reference the **copy**, which is how the history records exactly which copy was borrowed.
- `Review(review_id PK, user_id FK ON DELETE RESTRICT, book_id FK ON DELETE CASCADE, rating SMALLINT NOT NULL CHECK 1–5, comment TEXT NULL, created_at, UNIQUE(user_id, book_id))`
- `Reservation(reservation_id PK, user_id FK ON DELETE RESTRICT, book_id FK ON DELETE CASCADE, status NOT NULL DEFAULT 'waiting' CHECK IN ('waiting','fulfilled','cancelled'), reserved_at)`, plus `CREATE UNIQUE INDEX ... ON Reservation(user_id, book_id) WHERE status = 'waiting'`

Seed `user_id`s must satisfy the CHECK (letters, digits, underscore, 3–20 chars).

The stored values are already lowercase, matching the views and middleware. Only the names need aliasing (`id`, `username`, `name`, `author`). There's no password-hashing dependency, but Node's built-in `crypto.scrypt` is enough.

## Business rules to enforce server-side

- **Borrow:** check all of these inside one transaction, locking the copy row (`SELECT ... FOR UPDATE`):
  - the copy is available
  - the user has fewer than 3 unreturned loans
  - the user has no unreturned loan of the same `book_id` (any copy)
  - the user is not overdue

  Overdue means an unreturned loan with `CURRENT_DATE >= due_date`, i.e. 7 days or more.
  While a book has `waiting` reservations, only the earliest reserver may borrow it, and borrowing marks that reservation `fulfilled`.
- **Return:** update only a loan that matches both `id` and the session user and is still unreturned. Users must not be able to return someone else's loan.
- **Delete copy:** refuse if the copy is currently borrowed. Otherwise delete it, and its loans cascade. When the last copy goes, delete the book, which cascades to its `Book_Category`, `Review` and `Reservation` rows.
- **Delete category:** remove only the `Book_Category` links. Books keep their other categories.
- **Charts:** count loans from the last 3 months, aggregated per **book** (all copies combined), both overall and per category.
