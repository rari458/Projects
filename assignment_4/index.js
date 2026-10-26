const express = require('express');
const app = express();
const port = 3000;
const session = require('express-session');

const routes = require('./routes/routes');

app.set('view engine', 'ejs');
app.use(express.static('public'));
app.use('/modules', express.static('node_modules'));
app.use(express.urlencoded({ extended: true }));

app.use(session({
    secret: '32e97126-8be4-433d-ba34-338f12df99a6',
    resave: false,
    saveUninitialized: true,
    cookie: { secure: false }
}));

// Middleware to make session available in EJS templates
app.use((req, res, next) => {
    res.locals.session = req.session;
    next();
});

app.use('/', routes);
app.get('/', (req, res) => res.redirect('/charts'));

// Generic error handler
app.use((err, req, res, next) => {
    console.error(err.stack);

    const status = err.status || 500;
    const message = err.message || 'Internal Server Error';

    res.status(status);
    res.render('pages/error', {
        title: `Error ${status}`,
        status: status,
        message: message,
    });
});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});