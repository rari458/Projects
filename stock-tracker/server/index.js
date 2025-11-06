// server/index.js

require('dotenv').config();
const mongoose = require('mongoose');
const app = require('./app');

const PORT = process.env.PORT || 5001;

mongoose.connect(process.env.MONGO_URI)
    .then(() => {
        console.log('MongDB connected successfully!');

        app.listen(PORT, () => {
            console.log(`Server is running on port ${PORT}`);
        });
    })
    .catch((err) => console.error('MongDB connection error:', err));