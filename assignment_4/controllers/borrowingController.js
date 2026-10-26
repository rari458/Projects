const db = require('../config/db');

const getBorrowingsPage = async (req, res, next) => {
    const userId = req.session.userId;

    if (!userId) {
        return res.redirect('/login');
    }

    const dummyBorrowings = [ // 이 변수는 더미데이터입니다. 구현을 다하면 제거해주세요.
        {
            id: 1, book_instance_id: 13, book_title: 'The Hobbit', book_author: 'J.R.R Tolkien', borrow_date: '2023.10.01', return_date: '2023.10.15', status: 'returned'
        },
        {
            id: 2, book_instance_id: 11, book_title: 'The Lord of the Rings', book_author: 'J.R.R Tolkien', borrow_date: '2023.10.05', return_date: null, status: 'borrowed'
        },
        {
            id: 3, book_instance_id: 10, book_title: 'The Silmarillion', book_author: 'J.R.R Tolkien', borrow_date: '2023.10.10', return_date: null, status: 'borrowed'
        },
    ];
    try {
        /*
            TODO: 유저의 대여 기록을 모두 출력하는 페이지를 렌더링하는 코드를 작성하세요.
        */
        res.render('pages/borrowings', {
            title: 'My Borrowing History',
            borrowings: dummyBorrowings // 대여 기록 리스트가 전달되어야 합니다.
        });
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getBorrowingsPage
};