const db = require('../config/db');
const { httpError } = require('../utils/httpError');

// GET /reservations - the session user's reservations, waiting ones first, each with its place in the queue
const getReservationsPage = async (req, res, next) => {
    try {
        const { rows } = await db.query(
            `SELECT r.reservation_id AS id,
                    r.book_id,
                    b.title AS book_title,
                    a.author_name AS book_author,
                    to_char(r.reserved_at, 'YYYY.MM.DD HH24:MI') AS reserved_date,
                    r.status,
                    (SELECT COUNT(*)::int FROM Reservation q
                     WHERE r.status = 'waiting' AND q.book_id = r.book_id AND q.status = 'waiting'
                       AND (q.reserved_at, q.reservation_id) <= (r.reserved_at, r.reservation_id)) AS queue_position
             FROM Reservation r
             JOIN Book b ON b.book_id = r.book_id
             JOIN Author a ON a.author_id = b.author_id
             WHERE r.user_id = $1
             ORDER BY r.status = 'waiting' DESC, r.reserved_at DESC, r.reservation_id DESC`,
            [req.session.userId]
        );

        res.render('pages/reservations', {
            title: 'My Reservations',
            reservations: rows,
        });
    } catch (err) {
        next (err);
    }
};

// POST /books/:id/reserve - joins the queue for a book whose copies are all out
const postReserveBook = async (req, res, next) => {
    const bookId = Number(req.params.id);
    const userId = req.session.userId;

    try {
        await db.transaction(async (client) => {
            // FOR SHARE holds off any borrow or return of these copies until this commits, so the check stays true
            const copies = await client.query('SELECT status FROM BookCopy WHERE book_id = $1 FOR SHARE', [bookId]);
            if (copies.rowCount === 0) throw httpError(404, 'Book not found.');
            if (copies.rows.some((copy) => copy.status === 'available')) {
                throw httpError(400, 'A copy of this book is available. Borrow it instead of reserving.');
            }

            const holding = await client.query(
                `SELECT 1 FROM Loan l
                 JOIN BookCopy cp ON cp.copy_id = l.copy_id
                 WHERE l.user_id = $1 AND cp.book_id = $2 AND l.return_date IS NULL`,
                [userId, bookId]
            );
            if (holding.rowCount > 0) throw httpError(400, 'You are already borrowing a copy of this book.');

            // the partial unique index allows one waiting reservation per user and book
            const inserted = await client.query(
                `INSERT INTO Reservation (user_id, book_id) VALUES ($1, $2)
                 ON CONFLICT (user_id, book_id) WHERE status = 'waiting' DO NOTHING`,
                [userId, bookId]
            );
            if (inserted.rowCount === 0) throw httpError(400, 'You already have a reservation for this book.');
        });
        res.redirect('/reservations');
    } catch (err) {
        next(err);
    }
};

// POST /reservations/:id/cancel - only the session user's own reservation, and only while it is waiting
const postCancelReservation = async (req, res, next) => {
    const reservationId = Number(req.params.id);

    try {
        const { rowCount } = await db.query(
            `UPDATE Reservation SET status = 'cancelled'
             WHERE reservation_id = $1 AND user_id = $2 AND status = 'waiting'`,
            [reservationId, req.session.userId]
        );
        if (rowCount === 0) throw httpError(400, 'This reservation is not yours or is no longer waiting.');
        res.redirect('/reservations');
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getReservationsPage,
    postReserveBook,
    postCancelReservation
};