const db = require('../config/db');

// Loans of the last 3 months per book, all copies combined, top 10.
// $1 = NULL counts every book; $1 = a category id keeps only that category's books,
// though each row still lists all of the book's categories.
const POPULAR_BOOKS_SQL = `
    SELECT b.title,
           a.author_name AS author,
           COALESCE((SELECT string_agg(c.category_name, ', ' ORDER BY c.category_name)
                     FROM Book_Category bc
                     JOIN Category c ON c.category_id = bc.category_id
                     WHERE bc.book_id = b.book_id), '') AS categories,
           COUNT(*)::int AS borrow_count
    FROM Loan l
    JOIN BookCopy cp ON cp.copy_id = l.copy_id
    JOIN Book b ON b.book_id = cp.book_id
    JOIN Author a ON a.author_id = b.author_id
    WHERE l.loan_date >= CURRENT_DATE - INTERVAL '3 months'
      AND ($1::int IS NULL OR EXISTS (SELECT 1 FROM Book_Category bc
                                      WHERE bc.book_id = b.book_id AND bc.category_id = $1::int))
    GROUP BY b.book_id, a.author_id
    ORDER BY borrow_count DESC, b.title
    LIMIT 10`;

// the same loans per author, over all of the author's books
const POPULAR_AUTHORS_SQL = `
    SELECT a.author_name AS author,
           COUNT(*)::int AS borrow_count
    FROM Loan l
    JOIN BookCopy cp ON cp.copy_id = l.copy_id
    JOIN Book b ON b.book_id = cp.book_id
    JOIN Author a ON a.author_id = b.author_id
    WHERE l.loan_date >= CURRENT_DATE - INTERVAL '3 months'
    GROUP BY a.author_id
    ORDER BY borrow_count DESC, a.author_name
    LIMIT 10`;

const getChartsPage = async (req, res, next) => {
    try {
        const [categories, popularBooks, popularAuthors] = await Promise.all([
            db.query('SELECT category_id AS id, category_name AS name FROM Category ORDER BY category_name'),
            db.query(POPULAR_BOOKS_SQL, [null]),
            db.query(POPULAR_AUTHORS_SQL),
        ]);

        // an unknown, missing or malformed categoryId falls back to the first category in the dropdown
        const requestedId = Number(req.query.categoryId);
        const selected = categories.rows.find((category) => category.id === requestedId) || categories.rows[0];

        const popularBooksByCategory = {};
        if (selected) {
            const { rows } = await db.query(POPULAR_BOOKS_SQL, [selected.id]);
            popularBooksByCategory[selected.name] = rows;
        }

        res.render('pages/charts', {
            title: 'Charts',
            popularBooks: popularBooks.rows,
            popularAuthors: popularAuthors.rows,
            popularBooksByCategory,
            categories: categories.rows,
            selectedCategoryId: selected ? selected.id : null,
        });
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getChartsPage
};