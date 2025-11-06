// server/routes/portfolio.js

const express = require('express');
const router = express.Router();
const Transaction = require('../models/Transaction');
const authMiddleware = require('../middleware/authMiddleware');

router.post('/add', authMiddleware, async (req, res) => {
    try {
        const { symbol, shares, pricePerShare, transactionType, date } = req.body;
        const userId = req.user.userId;

        if (!symbol || !shares || !pricePerShare || !transactionType) {
            return res.status(400).json({ error: 'Missing required fields' });
        }

        const newTransaction = new Transaction({
            user: userId,
            symbol,
            shares,
            pricePerShare,
            transactionType,
            date: date || Date.now()
        });

        await newTransaction.save();

        res.status(201).json({
            message: 'Transaction added successful!',
            transaction: newTransaction
        });
    } catch (error) {
        console.error('Add transaction error:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

router.get('/', authMiddleware, async (req, res) => {
    try {
        const userId = req.user.userId;
        const transactions = await Transaction.find({ user: userId }).sort({ date: -1 });
        res.status(200).json(transactions);
    } catch (error) {
        console.error('Get transactions error:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

router.get('/summary', authMiddleware, async (req, res) => {
    try {
        const userId = req.user.userId;
        const transactions = await Transaction.find({ user: userId }).sort({ date: 1});

        if (transactions.length === 0) {
            return res.status(200).json({ holdings: [], realizedPnL: 0 });
        }

        const holdingsMap = new Map();
        let realizedPnL = 0;

        transactions.forEach((tx) => {
            const { symbol, shares, pricePerShare, transactionType } = tx;
            const holding = holdingsMap.get(symbol) || { shares: 0, totalCost: 0 };

            if (transactionType === 'buy') {
                holding.shares += shares;
                holding.totalCost += shares * pricePerShare;
            } else if (transactionType === 'sell') {
                const avgCostBeforeSell = (holding.shares > 0) ? (holding.totalCost / holding.shares) : 0;
                const profitFromThisSell = (pricePerShare - avgCostBeforeSell) * shares;
                realizedPnL += profitFromThisSell;
                holding.shares -= shares;
                holding.totalCost -= shares * avgCostBeforeSell;
            } else if (transactionType === 'dividend') {
                realizedPnL += pricePerShare;
            }

            if (transactionType !== 'dividend') {
                holdingsMap.set(symbol, holding);
            }
        });

        const holdings = [];
        holdingsMap.forEach((data, symbol) => {
            if (data.shares > 0.00001) {
                holdings.push({
                    symbol,
                    shares: data.shares,
                    avgCost: (data.shares > 0) ? (data.totalCost / data.shares) : 0,
                    totalCost: data.totalCost,
                });
            }
        });

        res.status(200).json({
            holdings: holdings,
            realizedPnL: realizedPnL,
        });
    } catch (error) {
        console.error('Get summary error:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

module.exports = router;