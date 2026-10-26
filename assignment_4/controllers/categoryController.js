const db = require('../config/db');

const getCategoriesPage = async (req, res, next) => {
    const dummyCategories = [ // 이 변수는 더미데이터입니다. 구현을 다하면 제거해주세요.
        { id: 1, name: 'Fantasy' },
        { id: 2, name: 'Science Fiction' },
        { id: 3, name: 'Mystery' },
    ];
    try {
        /*
            TODO: 모든 카테고리를 출력하는 페이지를 렌더링하는 코드를 작성하세요.
        */
        res.render('pages/categories', {
            title: 'Category Management',
            categories: dummyCategories // 카테고리 리스트가 전달되어야 합니다.
        });
    } catch (err) {
        next(err);
    }
};

const postDeleteCategory = async (req, res, next) => {
    const categoryId = Number(req.params.id);
    try {
        /*
            TODO: 카테고리를 제거하는 코드를 작성하세요.
            만약 해당 카테고리에 포함된 책이 있다면 책에서 해당 카테고리만 지우고 나머지 카테고리는 유지하면 됩니다.
        */
        res.redirect('/categories');
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getCategoriesPage,
    postDeleteCategory
};