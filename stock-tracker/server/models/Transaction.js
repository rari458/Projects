// server/models/Transaction.js

const mongoose = require('mongoose');

const transactionSchema = new mongoose.Schema({
    user: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true,
    },
    symbol: {
        type: String,
        required: true,
        uppercase: true,
        trim: true,
    },
    shares: {
        type: Number,
        required: true,
        min: 0,
    },
    pricePerShare: {
        type: Number,
        required: true,
        min: 0,
    },
    transactionType: {
        type: String,
        enum: ['buy', 'sell', 'dividend'],
        required: true,
    },
    date: {
        type: Date,
        default: Date.now,
    },
});

module.exports = mongoose.model('Transaction', transactionSchema);