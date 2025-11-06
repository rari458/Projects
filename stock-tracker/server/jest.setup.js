// server/jest.setup.js

const mongoose = require('mongoose');
require('dotenv').config();

if (process.env.NODE_ENV !== 'test') {
    throw new Error('Jest setup must be run in test environment');
}

beforeAll(async () => {
    await mongoose.connect(process.env.MONGO_URI_TEST);
});

beforeEach(async () => {
    const collections = await mongoose.connection.db.collections();
    for (let collection of collections) {
        await collection.deleteMany({});
    }
});

afterAll(async () => {
    await mongoose.connection.close();
});