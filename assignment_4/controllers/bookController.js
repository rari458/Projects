const db = require('../config/db');
const { containsPattern } = require('../utils/search');

// an Error that the generic handler renders with this HTTP status
const httpError = (status, message) => {
    const err = new Error(message);
    err.status = status;
    return err;
};

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
    const dummyCategories = [
        { id: 1, name: 'Fantasy' },
        { id: 2, name: 'Science Fiction' },
        { id: 3, name: 'Mystery' },
    ];
    const dummyAuthors = [
        { id: 1, name: 'J.R.R Tolkien' },
        { id: 2, name: 'Isaac Asimov' },
        { id: 3, name: 'Agatha Christie' },
    ];
    try {
        /*
            TODO: 책을 추가하는 페이지를 렌더링 하는 코드를 작성하세요.
            책 추가 시 작가와 카테고리를 선택해야하므로 현재 카테고리 목록과 작가 목록을 불러와야 합니다.
        */
        res.render('pages/add-book', {
            title: 'Add New Book',
            categories: dummyCategories, // 카테고리 리스트가 전달되어야 합니다.
            authors: dummyAuthors, // 저자 리스트가 전달되어야 합니다.
        });
    } catch (err) {
        next(err);
    }
};


const postAddBook = async (req, res, next) => {
    const { title, authors, quantity, categories } = req.body;

    try {
        /*
            TODO: 책을 DB에 추가하는 작업을 수행하는 코드를 작성하세요.
            기존에 없는 카테고리와 저자 또한 추가해줘야 합니다.
        */
        res.redirect('/books');
    } catch (err) {
        next(err);
    }
};


const postDeleteBookInstance = async (req, res, next) => {
    const bookInstanceId = Number(req.params.id);

    try {
        /*
            TODO: 책 한 권을 제거하는 작업을 수행하는 코드를 작성하세요.
            동일한 책을 모두 제거하면 해당 책에 대한 정보도 지워지도록 구현해주세요.
        */
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

module.exports = {
    getBooksPage,
    getAddBookPage,
    postAddBook,
    postDeleteBookInstance,
    postBorrowBook,
    postReturnBook,
    getBookInstances
};