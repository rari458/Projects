const db = require('../config/db');
const { containsPattern } = require('../utils/search');

// searchBy -> WHERE clause; user_id is both the id and the username
const SEARCH_CONDITIONS = {
    username: 'user_id ILIKE $1',
    role: 'role ILIKE $1',
};

const getUsersPage = async (req, res, next) => {
    const searchQuery = typeof req.query.query === 'string' ? req.query.query.trim() : '';
    const searchBy = Object.hasOwn(SEARCH_CONDITIONS, req.query.searchBy) ? req.query.searchBy : 'username';

    try {
        const where = searchQuery ? `WHERE ${SEARCH_CONDITIONS[searchBy]}` : '';
        const params = searchQuery ? [containsPattern(searchQuery)] : [];
        const { rows } = await db.query(`SELECT user_id AS id, user_id AS username, role FROM Users ${where} ORDER BY user_id`, params);

        res.render('pages/users',{
            title: 'User Management',
            users: rows,
            searchBy,
            query: searchQuery,
        });
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getUsersPage
};