const db = require('../config/db');

const getBooksPage = async (req, res, next) => {
    const { query: searchQuery, searchBy, sortedBy, sortOrder } = req.query;
    const sortedByWithDefault = req.query.sortBy || 'title';
    const sortOrderWithDefault = req.query.sortOrder || 'asc';

    const dummyBooks = [ // 이 변수는 더미데이터입니다. 구현을 다하면 제거해주세요.
        {
            id: 1, title: 'The Hobbit', author: 'J.R.R Tolkien', categories: 'Fantasy', total_quantity: 4, available_quantity: 4
        },
        {
            id: 2, title: 'The Lord of the Rings', author: 'J.R.R Tolkien', categories: 'Fantasy', total_quantity: 3, available_quantity: 2
        },
        {
            id: 3, title: 'The Silmarillion', author: 'J.R.R Tolkien', categories: 'Fantasy', total_quantity: 2, available_quantity: 1
        },
        {
            id: 4, title: 'The Children of Húrin', author: 'J.R.R Tolkien', categories: 'Fantasy', total_quantity: 1, available_quantity: 0
        },
        {
            id: 5, title: 'Foundation', author: 'Isaac Asimov', categories: 'Science Fiction', total_quantity: 5, available_quantity: 5
        },
        {
            id: 6, title: 'And Then There Were None', author: 'Agatha Christie', categories: 'Mystery', total_quantity: 3, available_quantity: 1
        },
        {
            id: 7, title: 'Dune', author: 'Frank Herbert', categories: 'Science Fiction, Fantasy', total_quantity: 4, available_quantity: 4
        },
    ];

    try {
        /*
            TODO: 검색어, 정렬 기준에 맞춰 책 목록을 출력하는 페이지를 렌더링하는 코드를 작성하세요.
        */
        res.render('pages/books', {
            title: 'All Books',
            books: dummyBooks, // 정렬된 검색 결과 리스트가 전달되어야 합니다.
            sortBy: sortedByWithDefault,
            sortOrder: sortOrderWithDefault,
            query: searchQuery,
            searchBy: searchBy
        });
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
    const dummyInstances = [
        { id: 1, book_id: 1, borrowing_id: null, borrowed_by: null, borrow_date: null, status: 'available' },
        { id: 2, book_id: 1, borrowing_id: 1, borrowed_by: 'user1', borrow_date: '2025.10.01',status: 'borrowed' },
        { id: 3, book_id: 1, borrowing_id: null, borrowed_by: null, borrow_date: null,status: 'available' },
    ];

    try {
        /*
            TODO: 특정 동일한 책의 개별 리스트를 불러오는 코드를 작성해주세요.
        */
        res.json(dummyInstances);
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