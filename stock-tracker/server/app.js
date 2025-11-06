// server/app.js

const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const passport = require('passport');
require('dotenv').config();

const app = express();

app.use(cors());
app.use(express.json());

app.use(passport.initialize());
require('./config/passport')(passport);

app.get('/', (req, res) => {
    res.send('Hello from Stock Tracker Backend!');
});

const authRoutes = require('./routes/auth');
app.use('/api/auth', authRoutes);

const portfolioRoutes = require('./routes/portfolio');
app.use('/api/portfolio', portfolioRoutes);

const stockRoutes = require('./routes/stocks');
app.use('/api/stocks', stockRoutes);

const watchlistRoutes = require('./routes/watchlist');
app.use('/api/watchlist', watchlistRoutes);

module.exports = app;