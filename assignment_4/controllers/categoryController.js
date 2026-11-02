const db = require('../config/db');
const { httpError } = require('../utils/httpError');

const getCategoriesPage = async (req, res,next) => {
    try {
        const { rows } = await db.query('SELECT category_id AS id, category_name AS name FROM Category ORDER BY category_id');
        res.render('pages/categories', {
            title: 'Category Management',
            categories: rows,
        });
    } catch (err) {
        next(err);
    }
};

const postAddCategory = async (req, res, next) => {
    const name = typeof req.body.name === 'string' ? req.body.name.trim() : '';

    try {
        if (!name || name.length > 50) throw httpError(400, 'A category name must be 1-50 characters.');
        // skip the insert if the name exists in any letter case; ON CONFLICT covers two admins adding it at once
        const { rowCount } = await db.query(
            `INSERT INTO Category (category_name)
             SELECT $1::text
             WHERE NOT EXISTS (SELECT 1 FROM Category WHERE lower(category_name) = lower($1::text))
             ON CONFLICT (category_name) DO NOTHING`,
            [name]
        );
        if (rowCount === 0) throw httpError(400, `The category "${name}" already exists.`);
        res.redirect('/categories');
    } catch (err) {
        next(err);
    }
};

const postDeleteCategory = async (req, res, next) => {
    const categoryId = Number(req.params.id);
    try {
        // its Book_Category links cascade, so books lose only this category and keep the rest
        const { rowCount } = await db.query('DELETE FROM Category WHERE category_id = $1', [categoryId]);
        if (rowCount === 0) throw httpError(404, 'Category not found.');
        res.redirect('/categories');
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getCategoriesPage,
    postAddCategory,
    postDeleteCategory
};
