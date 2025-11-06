// server/config/passport.js

const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;
const mongoose = require('mongoose');
const User = require('../models/User');
require('dotenv').config();

module.exports = function(passport) {
    passport.use(
        new GoogleStrategy(
            {
                clientID: process.env.GOOGLE_CLIENT_ID,
                clientSecret: process.env.GOOGLE_CLIENT_SECRET,
                callbackURL: 'https://stock-tracker-server.onrender.com/api/auth/google/callback',
            },
            async (accessToken, refreshToken, Profiler, done) => {
                try {
                    let user = await User.findOne({ googleId: Profiler.id });

                    if (user) {
                        return done(null, user);
                    } else {
                        const newUser = new User({
                            googleId: Profiler.id,
                            email: Profiler.emails[0].value,
                        });

                        await newUser.save();
                        return done(null, newUser);
                    }
                } catch (err) {
                    console.error('Passport Google Strategy Error:', err);
                    return done(err, null);
                }
            }
        )
    );
};