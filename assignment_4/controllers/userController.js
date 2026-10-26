const db = require('../config/db');

const getUsersPage = async (req, res, next) => {
    const { searchBy, query } = req.query;

    const dummyUsers = [ // 이 변수는 더미데이터입니다. 구현을 다하면 제거해주세요.
        { id: 1, username: 'admin', role: 'admin' },
        { id: 2, username: 'user1', role: 'user' },
        { id: 3, username: 'user2', role: 'user' },
    ];

    try {
        /*
            TODO: 검색어에 맞춰 유저 목록을 출력하는 페이지를 렌더링하는 코드를 작성하세요.
        */
        res.render('pages/users', {
            title: 'User Management',
            users: dummyUsers,
            searchBy,
            query
        });
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getUsersPage
};