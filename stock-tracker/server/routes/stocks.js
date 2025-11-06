// server/routes/stocks.js

const express = require('express');
const router = express.Router();
const axios = require('axios');
const authMiddleware = require('../middleware/authMiddleware');
const FINNHUB_BASE_URL = 'https://finnhub.io/api/v1';
const API_KEY = process.env.FINNHUB_API_KEY;

router.get('/search', authMiddleware, async (req, res) => {
    const query = req.query.q;

    if (!query) {
        return res.status(400).json({ error: 'Search query (q) is required'});
    }

    if (!API_KEY) {
        return res.status(500).json({ error: 'Finnhub API key is not configured' });
    }

    try {
        const response = await axios.get(`${FINNHUB_BASE_URL}/search`, {
            params: {
                q: query,
                token: API_KEY,
            }
        });

        res.status(200).json(response.data);
    } catch (error) {
        console.error('Finnhub search error:', error.response ? error.response.data : error.message);
        res.status(500).json({ error: 'Failed to search stocks from Finnhub' });
    }
});

router.get('/quote', authMiddleware, async (req, res) => {
    const symbol = req.query.symbol;

    if (!symbol) {
        return res.status(400).json({ error: 'Stock symbol is required' });
    }

    if (!API_KEY) {
        return res.status(500).json({ error: 'Finnhub API key is not configured'});
    }

    try {
        const response = await axios.get(`${FINNHUB_BASE_URL}/quote`, {
            params: {
                symbol: symbol,
                token: API_KEY,
            }
        });

        res.status(200).json(response.data);
    } catch (error) {
        console.error('Finnhub quote error:', error.response ? error.response.data : error.message);
        res.status(500).json({ error: 'Failed to fetch stock quote from Finnhub' });
    }
});

module.exports = router;