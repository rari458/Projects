// server/routes/auth.test.js

const request = require('supertest');
const app = require('../app');
const mongoose = require('mongoose');
const User = require('../models/User');

describe('Authentication API - /api/auth', () => {
    it('should register a new user successfully (POST /register)', async () => {

        const testUser = {
            email: 'test@example.com',
            password: 'password123',
        };

        const response = await request(app)
          .post('/api/auth/register')
          .send(testUser)

        expect(response.statusCode).toBe(201);
        expect(response.body).toHaveProperty('token');
        expect(response.body.user.email).toBe(testUser.email);

        const dbUser = await User.findOne({ email: testUser.email });
        expect(dbUser).not.toBeNull();
        expect(dbUser.password).not.toBe(testUser.password);
    });

    it('should fail registration if email is already in use (POST /register)', async () => {
        const existingUser = new User({
            email: 'test@example.com',
            password: 'password123',
        });
        await existingUser.save();

        const response = await request(app)
          .post('/api/auth/register')
          .send({
            email: 'test@example.com',
            password: 'anotherpassword',
          });

        expect(response.statusCode).toBe(400);
        expect(response.body.error).toBe('This email is already in use');
    });

    it('should login an existing user successfully (POST /login)', async () => {
        const userEmail = 'login@example.com';
        const userPassword = 'password123';

        const user = new User({
            email: userEmail,
            password: userPassword,
        });
        await user.save();

        const response = await request(app)
          .post('/api/auth/login')
          .send({
            email: userEmail,
            password: userPassword,
          });

        expect(response.statusCode).toBe(200);
        expect(response.body).toHaveProperty('token');
        expect(response.body.user.email).toBe(userEmail);
    });

    it('should fail login with incorrect password (POST /login)', async () => {
        const userEmail = 'loginfail@example.com';
        const userPassword = 'password123';

        const user = new User({
            email: userEmail,
            password: userPassword,
        });
        await user.save();

        const response = await request(app)
          .post('/api/auth/login')
          .send({
            email: userEmail,
            password: 'wrongpassword',
          });

        expect(response.statusCode).toBe(400);
        expect(response.body.error).toBe('Invalid email or password');
    });
});