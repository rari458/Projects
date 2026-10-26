const db = require('../config/db');
const { hashPassword, verifyPassword } = require('../utils/password');

const adminCode = '2022065250'
// Same rule as the Users.user_id CHECK; book.ejs prints user ids unescaped
const USERNAME_PATTERN = /^[A-Za-z0-9_]{3,20}$/;

const fail = (next, status, message) => {
    const err = new Error(message);
    err.status = status;
    return next(err);
};

const getLoginPage = (req, res) => {
    res.render('pages/login', { title: 'Login' });
};

const getRegisterPage = (req, res) => {
    res.render('pages/register', { title: 'Register' });
};

const logoutAndGetHomePage = (req, res, next) => {
    req.session.destroy(err => {
        if (err) {
            return next(err);
        }
        res.redirect('/');
    });
};

const postLogin = async (req, res, next) => {
    const { username, password } = req.body;
    try {
        const { rows } = await db.query('SELECT user_id, password_hash, role FROM Users WHERE user_id = $1', [(username || '').trim()]);
        const user = rows[0];
        if (!user || !password || !(await verifyPassword(password, user.password_hash)))
        {
            return fail(next, 401, 'Invalid username or password.');
        }

        // a fresh session id on login, so an id issued before login can't be reused
        req.session.regenerate(err => {
            if (err) return next(err);
            req.session.userId = user.user_id;
            req.session.username = user.user_id;
            req.session.role = user.role;
            res.redirect('/');
        });
    } catch (err) {
        return next(err);
    }
};

const postRegister = async (req, res, next) => {
    const { username, password, role, admin_code } = req.body;

    try {
        const userId = (username || '').trim();
        if (!USERNAME_PATTERN.test(userId)) return fail(next, 400, 'Username must be 3-20 letters, digits or underscores.');
        if (!password) return fail(next, 400, 'Password is required.');
        if (role === 'admin' && admin_code !== adminCode) return fail(next, 403, 'Invalid admin code.');

        const { rowCount } = await db.query(
            `INSERT INTO Users (user_id, password_hash, role) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING`,
            [userId, await hashPassword(password), role === 'admin' ? 'admin' : 'user']
        );
        if (rowCount === 0) return fail(next, 400, 'Username is already taken.');
        res.redirect('/login');
    } catch (err) {
        return next(err);
    }
};

module.exports = {
    getLoginPage,
    getRegisterPage,
    logoutAndGetHomePage,
    postLogin,
    postRegister,
};