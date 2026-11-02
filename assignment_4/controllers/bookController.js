const db = require('../config/db');
const { containsPattern } = require('../utils/search');
const { httpError } = require('../utils/httpError');

// One row per book. Categories and copy counts come from separate subqueries,
// so they can't multiply each other's rows the way a double join would.
const BOOK_LIST_SQL = `
    SELECT b.book_id AS id,
           b.title,
           a.author_name AS author,
           COALESCE((SELECT string_agg(c.category_name, ', ' ORDER BY c.category_name)
                     FROM Book_Category bc
                     JOIN Category c ON c.category_id = bc.category_id
                     WHERE bc.book_id = b.book_id), '') AS categories,
           (SELECT COUNT(*)::int FROM BookCopy cp
            WHERE cp.book_id = b.book_id) AS total_quantity,
           (SELECT COUNT(*)::int FROM BookCopy cp
            WHERE cp.book_id = b.book_id AND cp.status = 'available') AS available_quantity
    FROM Book b
    JOIN Author a ON a.author_id = b.author_id  
`;

// searchBy -> WHERE clause; a category match still lists all of the book's categories
const SEARCH_CONDITIONS = {
    title: 'b.title ILIKE $1',
    author: 'a.author_name ILIKE $1',
    category: `EXISTS (SELECT 1 FROM Book_Category bc
                       JOIN Category c ON c.category_id = bc.category_id
                       WHERE bc.book_id = b.book_id AND c.category_name ILIKE $1)`,
};
// sortBy values are output column names of BOOK_LIST_SQL
const SORT_COLUMNS = ['title', 'author', 'categories'];

const getBooksPage = async (req, res, next) => {
    const searchQuery = typeof req.query.query === 'string' ? req.query.query.trim() : '';
    const searchBy = Object.hasOwn(SEARCH_CONDITIONS, req.query.searchBy) ? req.query.searchBy : 'title';
    const sortBy = SORT_COLUMNS.includes(req.query.sortBy) ? req.query.sortBy : 'title';
    const sortOrder = req.query.sortOrder === 'desc' ? 'desc' : 'asc';

    try {
        const where = searchQuery ? `WHERE ${SEARCH_CONDITIONS[searchBy]}` : '';
        const params = searchQuery ? [containsPattern(searchQuery)] : [];
        // ORDER BY can't take a bind parameter; sortBy and sortOrder are whitelisted above
        const { rows } = await db.query(
            `${BOOK_LIST_SQL} ${where} ORDER BY ${sortBy} ${sortOrder}, title, id`, params
        );

        res.render(
            'pages/books',
            {
                title: 'All Books',
                books: rows,
                sortBy,
                sortOrder,
                query: searchQuery,
                searchBy,
            }
        );
    } catch (err) {
        next(err);
    }
};

const getAddBookPage = async (req, res, next) => {
    try {
        const [authors, categories] = await Promise.all([
            db.query('SELECT author_id AS id, author_name AS name FROM Author ORDER BY author_name'),
            db.query('SELECT category_id AS id, category_name AS name FROM Category ORDER BY category_name'),
        ]);
        res.render('pages/add-book', {
            title: 'Add New Book',
            categories: categories.rows,
            authors: authors.rows,
        });
    } catch (err) {
        next(err);
    }
};

// The two kinds of row add-book can pick or create. Table and column names come
// from here, never from the request, so interpolating them into SQL is safe.
const NAMED_ROWS = {
    author: { table: 'Author', id: 'author_id', name: 'author_name', maxLength: 100 },
    category: { table: 'Category', id: 'category_id', name: 'category_name', maxLength: 50},
};
const MAX_NEW_COPIES = 100;

// Turns one add-book value into a row id. 'id:<n>' is a row picked from the list and must
// still exist. Anything else is a typed name: reuse a row with that name in any letter
// case, or insert a new one.
const resolveNamedRow = async (client, kind, value) => {
    const { table, id, name, maxLength } = NAMED_ROWS[kind];

    const picked = /^id:(\d{1,9})$/.exec(value);
    if (picked) {
        const { rows } = await client.query(`SELECT ${id} AS id FROM ${table} WHERE ${id} = $1`, [Number(picked[1])]);
        if (rows.length === 0) throw httpError(400, `The selected ${kind} no longer exists.`);
        return rows[0].id;
    }

    const typed = value.trim();
    if (!typed || typed.length > maxLength) {
        throw httpError(400, `A new ${kind} name must be 1-${maxLength} characters.`);
    }
    const existing = await client.query(`SELECT ${id} AS id FROM ${table} WHERE lower(${name}) = lower($1) ORDER BY ${id} LIMIT 1`, [typed]);
    if (existing.rows.length > 0) return existing.rows[0].id;
    // ON CONFLICT returns the other row if another admin inserts the same name at the same moment
    const { rows } = await client.query(
        `INSERT INTO ${table} (${name}) VALUES ($1)
         ON CONFLICT (${name}) DO UPDATE SET ${name} = EXCLUDED.${name}
         RETURNING ${id} AS id`,
        [typed]
    );
    return rows[0].id;
};

const postAddBook = async (req, res, next) => {
    const { title, authors, quantity, categories } = req.body;

    try {
        const bookTitle = typeof title === 'string' ? title.trim() : '';
        if (!bookTitle || bookTitle.length > 200) {
            throw httpError(400, 'Title must be 1-200 characters.');
        }
        if (typeof authors !== 'string' || !authors.trim()) {
            throw httpError(400, 'Choose or type an author.');
        }
        const copies = Number(quantity);
        if (!Number.isInteger(copies) || copies < 1 || copies > MAX_NEW_COPIES) {
            throw httpError(400, `Quantity must be a whole number from 1 to ${MAX_NEW_COPIES}.`);
        }
        // categories is missing when none is picked, a string for one, and an array for several
        const categoryValues = categories === undefined ? [] : [].concat(categories);
        if (!categoryValues.every((value) => typeof value === 'string')) {
            throw httpError(400, "Invalid categories.");
        }

        await db.transaction(async (client) => {
            const authorId = await resolveNamedRow(client, 'author', authors);
            const categoryIds = [];
            for (const value of categoryValues) {
                categoryIds.push(await resolveNamedRow(client, 'category', value));
            }

            // the same title by the same author gets the new copies instead of a second Book row
            const existing = await client.query(
                'SELECT book_id FROM Book WHERE author_id = $1 AND lower(title) = lower($2) ORDER BY book_id LIMIT 1',
                [authorId, bookTitle]
            );
            let bookId;
            if (existing.rows.length > 0) bookId = existing.rows[0].book_id;
            else
            {
                const inserted = await client.query('INSERT INTO Book (title, author_id) VALUES ($1, $2) RETURNING book_id', [bookTitle, authorId]);
                bookId = inserted.rows[0].book_id;
            }

            await client.query('INSERT INTO BookCopy (book_id) SELECT $1::int FROM generate_series(1, $2::int)', [bookId, copies]);
            // DO NOTHING skips links the book already has and a category picked twice
            await client.query(
                `INSERT INTO Book_Category (book_id, category_id)
                 SELECT $1::int, unnest($2::int[])
                 ON CONFLICT DO NOTHING`,
                [bookId, categoryIds]
            );
        });
        // land on the list filtered to this title, so the new copies are visible right away
        res.redirect(`/books?query=${encodeURIComponent(bookTitle)}`);
    } catch (err) {
        next(err);
    }
};


const postDeleteBookInstance = async (req, res, next) => {
    const bookInstanceId = Number(req.params.id);

    try {
        await db.transaction(async (client) => {
            // lock the copy so a borrow can't slip in between the check and the delete
            const copy = await client.query('SELECT book_id, status FROM BookCopy WHERE copy_id = $1 FOR UPDATE', [bookInstanceId]);
            if (copy.rowCount === 0) throw httpError(404, 'Book copy not found.');
            const { book_id: bookId, status } = copy.rows[0];
            if (status === 'borrowed') {
                throw httpError(400, 'This copy is borrowed. Delete it after it is returned.');
            }
            // and the book, so two admins deleting its last two copies at once still remove it
            await client.query('SELECT 1 FROM Book WHERE book_id = $1 FOR UPDATE', [bookId]);

            // the copy's past loans go with it (ON DELETE CASCADE)
            await client.query('DELETE FROM BookCopy WHERE copy_id = $1', [bookInstanceId]);
            // after the last copy the book goes too, and with it its categories, reviews and reservations
            await client.query(
                'DELETE FROM Book WHERE book_id = $1 AND NOT EXISTS (SELECT 1 FROM BookCopy WHERE book_id = $1)',
                [bookId]
            );
        });
        res.redirect('/books');
    } catch (err) {
        next(err);
    }
};


const postBorrowBook = async (req, res, next) => {
    const bookInstanceId = Number(req.params.id);
    const userId = req.session.userId;

    if (!userId) {
        return res.redirect('/login');
    }

    try {
        await db.transaction(async (client) => {
            // lock the user first, so two borrows by the same user wait for each other
            // instead of both passing the limit checks below
            const user = await client.query('SELECT 1 FROM Users WHERE user_id = $1 FOR UPDATE', [userId]);
            if (user.rowCount === 0) {
                throw httpError(401, 'Your account no longer exists. Please log in again.');
            }

            // then the copy, so nobody else can take it before this commits
            const copy = await client.query('SELECT book_id, status FROM BookCopy WHERE copy_id = $1 FOR UPDATE', [bookInstanceId]);
            if (copy.rowCount === 0) throw httpError(404, 'Book copy not found.');
            const { book_id: bookId, status } = copy.rows[0];
            if (status !== 'available') throw httpError(400, 'This copy is not available.');

            // the user's unreturned loans: how many, how many of this book, how many overdue
            const { rows: [loans] } = await client.query(
                `SELECT COUNT(*)::int AS open_count,
                        COUNT(*) FILTER (WHERE cp.book_id = $2)::int AS same_book,
                        COUNT(*) FILTER (WHERE CURRENT_DATE >= l.due_date)::int AS overdue
                FROM Loan l
                JOIN BookCopy cp ON cp.copy_id = l.copy_id
                WHERE l.user_id = $1 AND l.return_date IS NULL`,
                [userId, bookId]
            );
            if (loans.open_count >= 3) throw httpError(400, 'You have reached the maximum borrowing limit (3 books).');
            if (loans.same_book > 0) throw httpError(400, 'You are already borrowing a copy of this book.');
            if (loans.overdue > 0) throw httpError(400, 'You have an overdue book. Return it before borrowing another.');

            // while the book has a queue, only the earliest waiting reserver may borrow it
            const queue = await client.query(
                `SELECT user_id FROM Reservation
                 WHERE book_id = $1 AND status = 'waiting'
                 ORDER BY reserved_at, reservation_id
                 LIMIT 1`,
                [bookId]
            );
            if (queue.rowCount > 0 && queue.rows[0].user_id !== userId) {
                throw httpError(400, 'This book is reserved for another user.');
            }

            await client.query(
                `INSERT INTO Loan (user_id, copy_id, loan_date, due_date)
                 VALUES ($1, $2, CURRENT_DATE, CURRENT_DATE + 7)`,
                [userId, bookInstanceId]
            );
            await client.query(`UPDATE BookCopy SET status = 'borrowed' WHERE copy_id = $1`, [bookInstanceId]);
            await client.query(
                `UPDATE Reservation SET status = 'fulfilled'
                 WHERE user_id = $1 AND book_id = $2 AND status = 'waiting'`,
                [userId, bookId]
            );
        });
        res.redirect('/borrowings');
    } catch (err) {
        next(err);
    }
};


const postReturnBook = async (req, res, next) => {
    const borrowingId = Number(req.params.id);
    const userId = req.session.userId;

    if (!userId) {
        return res.redirect('/login');
    }

    try {
        await db.transaction(async (client) => {
            // matching user_id as well means a crafted POST can't return someone else's loan
            const { rows } = await client.query(
                `UPDATE Loan SET return_date = CURRENT_DATE
                WHERE loan_id = $1 AND user_id = $2 AND return_date IS NULL
                RETURNING copy_id`,
                [borrowingId, userId]
            );
            if (rows.length === 0) {
                throw httpError(400, 'This loan is not yours or has already been returned.');
            }
            await client.query(`UPDATE BookCopy SET status = 'available' WHERE copy_id = $1`, [rows[0].copy_id]);
        });
        res.redirect('/borrowings');
    } catch (err) {
        next(err);
    }
};

const getBookInstances = async (req, res, next) => {
    const bookId = Number(req.params.id);

    try {
        // one row per copy; the partial unique index allows at most one open loan per copy
        const { rows } = await db.query(
            `SELECT cp.copy_id AS id,
                    cp.status,
                    l.loan_id AS borrowing_id,
                    l.user_id AS borrowed_by,
                    l.user_id AS borrowed_by_id,
                    to_char(l.loan_date, 'YYYY.MM.DD') AS borrow_date
            FROM BookCopy cp
            LEFT JOIN Loan l ON l.copy_id = cp.copy_id AND l.return_date IS NULL
            WHERE cp.book_id = $1
            ORDER BY cp.copy_id`,
            [bookId]
        );
        res.json(rows);
    } catch (err) {
        next(err);
    }
};

// GET /books/:id - the book, its reviews, and whether the session user may write one
const getBookDetailPage = async (req, res, next) => {
    const bookId = Number(req.params.id);
    const userId = req.session.userId || null;

    try {
        const [book, summary, reviews, borrowed] = await Promise.all([
            db.query(`${BOOK_LIST_SQL} WHERE b.book_id = $1`, [bookId]),
            db.query('SELECT COUNT(*)::int AS count, ROUND(AVG(rating), 1) AS average FROM Review WHERE book_id = $1', [bookId]),
            db.query(
                `SELECT user_id AS username, rating, comment, to_char(created_at, 'YYYY.MM.DD') AS review_date
                 FROM Review
                 WHERE book_id = $1
                 ORDER BY created_at DESC, review_id DESC`,
                [bookId]
            ),
            //only a user who has borrowed some copy of the book may review it
            db.query(
                `SELECT EXISTS (SELECT 1 FROM Loan l
                                JOIN BookCopy cp ON cp.copy_id = l.copy_id
                                WHERE l.user_id = $1 AND cp.book_id = $2) AS has_borrowed`,
                [userId, bookId]
            ),
        ]);
        if (book.rows.length === 0) throw httpError(404, 'Book not found.');

        res.render('pages/book-detail', {
            title: book.rows[0].title,
            book: book.rows[0],
            reviewSummary: summary.rows[0],
            reviews: reviews.rows,
            canReview: borrowed.rows[0].has_borrowed,
            myReview: reviews.rows.find((review) => review.username === userId) || null,
        });
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getBooksPage,
    getAddBookPage,
    postAddBook,
    postDeleteBookInstance,
    postBorrowBook,
    postReturnBook,
    getBookInstances,
    getBookDetailPage
};