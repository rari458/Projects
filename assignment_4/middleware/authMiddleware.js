const isAuthenticated = (req, res, next) => {
    if (req.session.userId) {
        next();
    } else {
        res.redirect('/login');
    }
};

const isAdmin = (req, res, next) => {
    if (req.session.userId && req.session.role === 'admin') {
        next();
    } else {
        const err = new Error('Access Denied: Admins only.');
        err.status = 403;
        next(err);
    }
};

module.exports = {
    isAuthenticated,
    isAdmin
};