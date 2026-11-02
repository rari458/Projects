const db = require('../config/db');
const { httpError } = require('../utils/httpError');

const MAX_COMMENT_LENGTH = 1000;

// POST /books/:id/review - writes the session user's review, or replaces it if one exists
const postSaveReview = async (req, res, next) => {
    const bookId = Number(req.params.id);
    const rating = Number(req.body.rating);
    const comment = typeof req.body.comment === 'string' ? req.body.comment.trim() : '';

    try {
        if (!Number.isInteger(rating) || rating < 1 || rating > 5) throw httpError(400, 'Choose a rating from 1 to 5.');
        if (comment.length > MAX_COMMENT_LENGTH) throw httpError(400, `A comment can be at most ${MAX_COMMENT_LENGTH} characters.`);

        // the WHERE EXISTS lets only someone who has borrowed a copy in; UNIQUE (user_id, book_id) turns a second review into an edit
        const { rowCount } = await db.query(
            `INSERT INTO Review (user_id, book_id, rating, comment)
             SELECT $1::varchar, $2::int, $3::smallint, $4::text
             WHERE EXISTS (SELECT 1 FROM Loan l
                           JOIN BookCopy cp ON cp.copy_id = l.copy_id
                           WHERE l.user_id = $1::varchar AND cp.book_id = $2::int)
             ON CONFLICT (user_id, book_id) DO UPDATE SET rating = EXCLUDED.rating, comment = EXCLUDED.comment`,
             [req.session.userId, bookId, rating, comment || null]
        );
        if (rowCount === 0) throw httpError(403, 'Only members who have borrowed this book can review it.');
        res.redirect(`/books/${bookId}`);
    } catch (err) {
        next(err);
    }
};

// POST /books/:id/review/delete - the WHERE on user_id means only the author can delete a review
const postDeleteReview = async (req, res, next) => {
    const bookId = Number(req.params.id);

    try {
        const { rowCount } = await db.query('DELETE FROM Review WHERE user_id = $1 AND book_id = $2', [req.session.userId, bookId]);
        if (rowCount === 0) throw httpError(404, 'You have no review of this book.');
        res.redirect(`/books/${bookId}`);
    } catch (err) {
        next(err);
    }
};

module.exports = {
    postSaveReview,
    postDeleteReview
};