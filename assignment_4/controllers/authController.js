const db = require('../config/db');
const adminCode = '' // TODO: admin code(본인 학번)를 추가하세요.

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
        /*
            TODO: username과 password를 이용해 로그인을 진행하는 코드를 작성하세요.
        */
        req.session.userId = 1;
        req.session.username = username;
        req.session.role = 'admin';
        res.redirect('/');
    } catch (err) {
        return next(err);
    }
};

const postRegister = async (req, res, next) => {
    const { username, password, role, admin_code } = req.body;

    try {
        /*
            TODO: username, password, role, admin_code를 이용해 새로운 계정을 추가하는 코드를 작성하세요.
        */
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