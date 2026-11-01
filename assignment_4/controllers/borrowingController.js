const db = require('../config/db');

const getBorrowingsPage = async (req, res, next) => {
    const userId = req.session.userId;

    if (!userId) return res.redirect('/login');
    
    try {
        // every loan of this user, newest first; to_char(NULL) stays NULL, which shows '-' and the Return button
        const { rows } = await db.query(
            `SELECT l.loan_id AS id,
                    l.copy_id AS book_instance_id,
                    b.title AS book_title,
                    a.author_name AS book_author,
                    to_char(l.loan_date, 'YYYY.MM.DD') AS borrow_date,
                    to_char(l.return_date, 'YYYY.MM.DD') AS return_date
            FROM Loan l
            JOIN BookCopy cp ON cp.copy_id = l.copy_id
            JOIN Book b ON b.book_id = cp.book_id
            JOIN Author a ON a.author_id = b.author_id
            WHERE l.user_id = $1
            ORDER BY l.loan_date DESC, l.loan_id DESC`,
            [userId]
        );

        res.render('pages/borrowings', {
            title: 'My Borrowing History',
            borrowings: rows,
        });
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getBorrowingsPage
};