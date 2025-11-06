// server/routes/watchlist.js

const express = require('express');
const router = express.Router();
const User = require('../models/User');
const authMiddleware = require('../middleware/authMiddleware');

router.get('/', authMiddleware, async (req, res) => {
    try {
        const user = await User.findById(req.user.userId).select('watchlist');

        if (!user) {
            return res.status(404).json({ error: 'User not found' });
        }

        res.status(200).json(user.watchlist || []);
    } catch (error) {
        console.error('Get watchlist error:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

router.post('/add', authMiddleware, async (req, res) => {
    const { symbol } = req.body;

    if (!symbol) {
        return res.status(400).json({ error: 'Symbol is required' });
    }

    try {
        const userId = req.user.userId;
        const upperSymbol = symbol.toUpperCase();

        const user = await User.findById(userId);
        if (!user) {
            return res.status(404).json({ error: 'User not found' });
        }

        if (user.watchlist.includes(upperSymbol)) {
            return res.status(400).json({ error: 'Symbol already in watchlist' });
        }

        user.watchlist.push(upperSymbol);
        await user.save();
        res.status(200).json(user.watchlist);
    } catch (error) {
        console.error('Add watchlist error:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

router.delete('/remove/:symbol', authMiddleware, async (req, res) => {
    const symbol = req.params.symbol;

    try {
        const userId = req.user.userId;
        const upperSymbol = symbol.toUpperCase();

        const updatedUser = await User.findByIdAndUpdate(
            userId,
            { $pull: { watchlist: upperSymbol } },
            { new: true }
        ).select('watchlist');

        if (!updatedUser) {
            return res.status(404).json({ error: 'User not found' });
        }

        res.status(200).json(updatedUser.watchlist);
    } catch (error) {
        console.error('Remove watchlist error:', error);
        res.status(500).json({ error: 'Server error'});
    }
});

module.exports = router;