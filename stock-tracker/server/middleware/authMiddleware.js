// server/middleware/authMiddleware.js

const jwt = require('jsonwebtoken');
require('dotenv').config();

const authMiddleware = (req, res, next) => {
    const authHeader = req.header('Authorization');

    if (!authHeader) {
        return res.status(401).json( { error: 'No token, authorization denied' });
    }

    try {
        const token = authHeader.split(' ')[1];

        if (!token) {
            return res.status(401).json({ error: 'Token format is invalid' });
        }

        const decoded = jwt.verify(token, process.env.JWT_SECRET);
        req.user= decoded;
        next();
    } catch (err) {
        res.status(401).json({ error: 'Token is not valid' });
    }
};

module.exports = authMiddleware;