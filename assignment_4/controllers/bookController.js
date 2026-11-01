const db = require('../config/db');
const { containsPattern } = require('../utils/search');

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
        /*
            TODO: 특정 책을 대여하는 작업을 수행하는 코드를 작성하세요.
            명세에 있는 조건들을 어기는 작업일 경우에는 다음과 같이 에러페이지로 유도하면 됩니다.

            ```
                const err = new Error('You have reached the maximum borrowing limit (3 books).');
                err.status = 400;
                return next(err);
            ```
        */
        res.redirect('/books');
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
        /*
            TODO: 자신이 책을 빌린 기록을 반납 처리하는 코드를 작성해주세요.
            다른 사람이 빌린 책은 반납할 수 없어야 합니다.
        */
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