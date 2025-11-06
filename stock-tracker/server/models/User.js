// server/models/User.js

const mongoose = require('mongoose');
const bcrypt = require('bcrypt');

const userSchema = new mongoose.Schema({
    email: {
        type: String,
        required: true,
        unique: true,
        lowercase: true,
        trim: true,
    },
    password: {
        type: String,
        required: false,
        minlength: 6,
    },
    googleId: {
        type: String,
        unique: true,
        sparse: true,
    },
    watchlist: [
        {
            type: String,
            uppercase: true,
            trim: true,
        }
    ]
});

userSchema.pre('save', async function (next) {
    if (!this.password || !this.isModified('password')) {
        return next();
    }

    try {
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(this.password, salt);
        this.password = hashedPassword;
        next();
    } catch (error) {
        next(error);
    }
});

module.exports = mongoose.model('User', userSchema);