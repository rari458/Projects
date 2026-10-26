const db = require('../config/db');

const getChartsPage = async (req, res, next) => {
    let selectedCategoryId = req.query.categoryId ? Number(req.query.categoryId) : null;

    const dummyPopularBooks = [ // 이 변수는 더미데이터입니다. 구현을 다하면 제거해주세요.
        { title: 'The Hobbit', author: 'J.R.R Tolkien', categories: 'Fantasy', borrow_count: 10 },
        { title: 'The Lord of the Rings', author: 'J.R.R Tolkien', categories: 'Fantasy', borrow_count: 8 },
        { title: 'Foundation', author: 'Isaac Asimov', categories: 'Science Fiction', borrow_count: 12 },
        { title: 'And Then There Were None', author: 'Agatha Christie', categories: 'Mystery', borrow_count: 15 },
        { title: 'Dune', author: 'Frank Herbert', categories: 'Science Fiction, Fantasy', borrow_count: 9 },
        { title: 'The Silmarillion', author: 'J.R.R Tolkien', categories: 'Fantasy', borrow_count: 5 },
    ];

    const dummyPopularBooksByCategory = { // 이 변수는 더미데이터입니다. 구현을 다하면 제거해주세요.
        'Fantasy': [
            { title: 'The Hobbit', author: 'J.R.R Tolkien', categories: 'Fantasy', borrow_count: 10 },
            { title: 'The Lord of the Rings', author: 'J.R.R Tolkien', categories: 'Fantasy', borrow_count: 8 },
            { title: 'Dune', author: 'Frank Herbert', categories: 'Science Fiction, Fantasy', borrow_count: 9 },
            { title: 'The Silmarillion', author: 'J.R.R Tolkien', categories: 'Fantasy', borrow_count: 5 },
        ],
    };

    const dummyCategories = [ // 이 변수는 더미데이터입니다. 구현을 다하면 제거해주세요.
        { id: 1, name: 'Fantasy' },
        { id: 2, name: 'Science Fiction' },
        { id: 3, name: 'Mystery' },
    ];

    try {
        /*
            TODO: 차트 페이지를 렌더링하는 코드를 작성하세요.
        */
        res.render('pages/charts', {
            title: 'Charts',
            popularBooks: dummyPopularBooks,
            popularBooksByCategory: dummyPopularBooksByCategory,
            categories: dummyCategories,
            selectedCategoryId
        });
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getChartsPage
};