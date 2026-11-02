const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const chartController = require('../controllers/chartController');
const bookController = require('../controllers/bookController');
const borrowingController = require('../controllers/borrowingController');
const categoryController = require('../controllers/categoryController');
const userController = require('../controllers/userController');
const reviewController = require('../controllers/reviewController');
const reservationController = require('../controllers/reservationController');
const statsController = require('../controllers/statsController');
const { isAuthenticated, isAdmin } = require('../middleware/authMiddleware');

// every :id in these routes is a SERIAL key; anything else is a 404 before any query runs
router.param('id', (req, res, next, id) => {
    if (/^\d{1,9}$/.test(id)) return next();
    const err = new Error('Not found.');
    err.status = 404;
    next(err);
});

// Login Page (no need login)
router.get('/login', authController.getLoginPage);
router.post('/login', authController.postLogin);

// Register Page (no need login)
router.get('/register', authController.getRegisterPage);
router.post('/register', authController.postRegister);

// Logout (need login only)
router.get('/logout', isAuthenticated, authController.logoutAndGetHomePage);

// Charts Page (no need login)
router.get('/charts', chartController.getChartsPage);


// Books Page (no need login)
router.get('/books', bookController.getBooksPage);

// Book Management (need login as admin)
router.get('/books/add', isAuthenticated, isAdmin, bookController.getAddBookPage);
router.post('/books/add', isAuthenticated, isAdmin, bookController.postAddBook);
router.post('/books/instances/:id/delete', isAuthenticated, isAdmin, bookController.postDeleteBookInstance);

// Borrow & Return (need login only)
router.post('/books/instances/:id/borrow', isAuthenticated, bookController.postBorrowBook);
router.post('/borrowings/:id/return', isAuthenticated, bookController.postReturnBook);

// Book Detail & Reviews (the page needs no login; writing or deleting a review needs login)
router.get('/books/:id', bookController.getBookDetailPage);
router.post('/books/:id/review', isAuthenticated, reviewController.postSaveReview);
router.post('/books/:id/review/delete', isAuthenticated, reviewController.postDeleteReview);

// Reservations (need login only)
router.post('/books/:id/reserve', isAuthenticated, reservationController.postReserveBook);
router.get('/reservations', isAuthenticated, reservationController.getReservationsPage);
router.post('/reservations/:id/cancel', isAuthenticated, reservationController.postCancelReservation);

// Statistics (rating statistics need no login; loan statistics need login, and only admins get their admin parts)
router.get('/stats/ratings', statsController.getRatingStatsPage);
router.get('/stats/loans', isAuthenticated, statsController.getLoanStatsPage);

// API route to get book instances
router.get('/api/books/:id/instances', isAuthenticated, bookController.getBookInstances);

// Borrowings Page (need login only)
router.get('/borrowings', isAuthenticated, borrowingController.getBorrowingsPage);


// Categories Page (need login as admin)
router.get('/categories', isAuthenticated, isAdmin, categoryController.getCategoriesPage);

// Category Management (need login as admin)
router.post('/categories/:id/delete', isAuthenticated, isAdmin, categoryController.postDeleteCategory);
router.post('/categories/add', isAuthenticated, isAdmin, categoryController.postAddCategory);


// Users Page (need login as admin)
router.get('/users', isAuthenticated, isAdmin, userController.getUsersPage);

module.exports = router;