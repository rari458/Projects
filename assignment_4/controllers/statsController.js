const db = require('../config/db');

// S1 (1): every book's average rating and review count; books without reviews sort last
const BOOK_RATINGS_SQL = `
    SELECT b.book_id AS id,
           b.title,
           a.author_name AS author,
           COUNT(r.review_id)::int AS review_count,
           ROUND(AVG(r.rating), 2) AS avg_rating
    FROM Book b
    JOIN Author a ON a.author_id = b.author_id
    LEFT JOIN Review r ON r.book_id = b.book_id
    GROUP BY b.book_id, a.author_id
    ORDER BY avg_rating DESC NULLS LAST, review_count DESC, b.title`;

// S1 (2): per category, the reviews of all its books, plus its best-rated book
// (highest average, then more reviews, then title)
const CATEGORY_RATINGS_SQL = `
    SELECT c.category_name AS category,
           COUNT(r.review_id)::int AS review_count,
           ROUND(AVG(r.rating), 2) AS avg_rating,
           (SELECT b.title
            FROM Book_Category tbc
            JOIN Book b ON b.book_id = tbc.book_id
            JOIN Review tr ON tr.book_id = b.book_id
            WHERE tbc.category_id = c.category_id
            GROUP BY b.book_id
            ORDER BY AVG(tr.rating) DESC, COUNT(*) DESC, b.title
            LIMIT 1) AS top_book
    FROM Category c
    LEFT JOIN Book_Category bc ON bc.category_id = c.category_id
    LEFT JOIN Review r ON r.book_id = bc.book_id
    GROUP BY c.category_id
    ORDER BY avg_rating DESC NULLS LAST, review_count DESC, category`;

// a loan is overdue when it came back on or after its due date, or is still out past it (4-1 report, S2)
const OVERDUE = 'COALESCE(return_date, CURRENT_DATE) >= due_date';

// S2 (1), admin: loans and overdue rate per month of loan_date
const MONTHLY_SQL = `
    SELECT to_char(loan_date, 'YYYY-MM') AS month,
           COUNT(*)::int AS loans,
           COUNT(*) FILTER (WHERE ${OVERDUE})::int AS overdue,
           ROUND(100.0 * COUNT(*) FILTER (WHERE ${OVERDUE}) / COUNT(*), 1) AS overdue_rate
    FROM Loan
    GROUP BY month
    ORDER BY month DESC`;

// S2 (2), admin only because it shows other members' records: total loans per member
const RANKING_SQL = `
    SELECT RANK() OVER (ORDER BY COUNT(l.loan_id) DESC)::int AS rank,
           u.user_id AS username,
           COUNT(l.loan_id)::int AS loans
    FROM Users u
    LEFT JOIN Loan l ON l.user_id = u.user_id
    GROUP BY u.user_id
    ORDER BY rank, u.user_id`;

// S2 (3), any member: their own totals; the on-time rate is over returned loans only
const PERSONAL_SQL = `
    SELECT COUNT(*)::int AS loans,
           COUNT(return_date)::int AS returned,
           COUNT(*) FILTER (WHERE return_date < due_date)::int AS on_time,
           ROUND(100.0 * COUNT(*) FILTER (WHERE return_date < due_date) / NULLIF(COUNT(return_date), 0), 1) AS on_time_rate
    FROM Loan
    WHERE user_id = $1`;

// GET /stats/ratings (public, like the reviews it summarizes)
const getRatingStatsPage = async (req, res, next) => {
    try {
        const [books, categories] = await Promise.all([
            db.query(BOOK_RATINGS_SQL),
            db.query(CATEGORY_RATINGS_SQL),
        ]);
        res.render('pages/rating-stats', {
            title: 'Rating Statistics',
            bookRatings: books.rows,
            categoryRatings: categories.rows,
        });
    } catch (err) {
        next(err);
    }
};

// GET /stats/loans - the admin-only parts are queried only for an admin, so no one else ever receives them
const getLoanStatsPage = async (req, res, next) => {
    const isAdmin = req.session.role === 'admin';

    try {
        const [personal, monthly, ranking] = await Promise.all([
            db.query(PERSONAL_SQL, [req.session.userId]),
            isAdmin ? db.query(MONTHLY_SQL) : null,
            isAdmin ? db.query(RANKING_SQL) : null,
        ]);
        res.render('pages/loan-stats', {
            title: 'Loan Statistics',
            personal: personal.rows[0],
            monthly: monthly ? monthly.rows : [],
            ranking: ranking ? ranking.rows : [],
        });
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getRatingStatsPage,
    getLoanStatsPage
};