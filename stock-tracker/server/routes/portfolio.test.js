// server/routes/portfolio.test.js

const request = require('supertest');
const app = require('../app');
const mongoose = require('mongoose');
const Transaction = require('../models/Transaction');
const User = require('../models/User');
const jwt = require('jsonwebtoken');

let token;
let userId;

describe('Portfolio API - /api/portfolio', () => {

    beforeEach(async () => {
        const user = new User({
            email: 'test-portfolio@example.com',
            password: 'password123'
        });
        const savedUser = await user.save();
        userId = savedUser._id;

        token = jwt.sign(
            { userId: userId, email: savedUser.email },
            process.env.JWT_SECRET,
            { expiresIn: '1h' }
        );
    });

    it('should add a new transaction (POST /add)', async () => {
        const transactionData = {
            symbol: 'AAPL',
            shares: 10,
            pricePerShare: 150,
            transactionType: 'buy',
        };

        const response = await request(app)
          .post('/api/portfolio/add')
          .set('Authorization', `Bearer ${token}`)
          .send(transactionData);

        expect(response.statusCode).toBe(201);
        expect(response.body.transaction.symbol).toBe('AAPL');
        expect(response.body.transaction.user).toBe(userId.toString());
    });

    it('should return holdings summary (GET /summary)', async () => {

        await Transaction.insertMany([
            {user: userId, symbol: 'AAPL', shares: 10, pricePerShare: 150, transactionType: 'buy', date: new Date('2025-01-01')},
            {user: userId, symbol: 'AAPL', shares: 5, pricePerShare: 200, transactionType: 'sell', date: new Date('2025-01-05')},
            {user: userId, symbol: 'MSFT', shares: 10, pricePerShare: 100, transactionType: 'buy', date: new Date('2025-01-10')},
        ]);

        const response = await request(app)
          .get('/api/portfolio/summary')
          .set('Authorization', `Bearer ${token}`);

        expect(response.statusCode).toBe(200);
        expect(response.body.holdings).toHaveLength(2);

        const aapl = response.body.holdings.find(h => h.symbol === 'AAPL');
        const msft = response.body.holdings.find(h => h.symbol === 'MSFT');

        expect(aapl.shares).toBe(5);
        expect(aapl.avgCost).toBeCloseTo(150);
        expect(aapl.totalCost).toBeCloseTo(750);

        expect(msft.shares).toBe(10);
        expect(msft.totalCost).toBeCloseTo(1000);
        expect(response.body.realizedPnL).toBeCloseTo(250);
    });
});