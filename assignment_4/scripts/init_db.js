const db = require('../config/db');
const { hashPassword } = require('../utils/password');

const TABLES = ['Users', 'Author', 'Book', 'BookCopy', 'Category', 'Book_Category', 'Loan', 'Review', 'Reservation'];

const CREATE_SQL = 
`
CREATE TABLE Users
(
    user_id         VARCHAR(20) PRIMARY KEY CHECK (user_id ~ '^[A-Za-z0-9_]{3,20}$'),
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(50),
    email           VARCHAR(100) UNIQUE,
    role            VARCHAR(10) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at      TIMESTAMP NOT NULL DEFAULT now()   
);

CREATE TABLE Author
(
    author_id SERIAL PRIMARY KEY,
    author_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE Book
(
    book_id         SERIAL PRIMARY KEY,
    isbn            VARCHAR(20) UNIQUE,
    title           VARCHAR(200) NOT NULL,
    author_id       INTEGER NOT NULL REFERENCES Author(author_id) ON DELETE RESTRICT,
    publisher       VARCHAR(100),
    published_year  SMALLINT,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE BookCopy
(
    copy_id       SERIAL PRIMARY KEY,
    book_id       INTEGER NOT NULL REFERENCES Book(book_id) ON DELETE CASCADE,
    call_number   VARCHAR(30) UNIQUE,
    status        VARCHAR(12) NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'borrowed', 'maintenance')),
    acquired_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE Category
(
    category_id   SERIAL PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    description   VARCHAR(200)
);

CREATE TABLE Book_Category
(
    book_id     INTEGER REFERENCES Book(book_id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES Category(category_id) ON DELETE CASCADE,
    PRIMARY KEY (book_id, category_id)
);

CREATE TABLE Loan
(
    loan_id     SERIAL PRIMARY KEY,
    user_id     VARCHAR(20) NOT NULL REFERENCES Users(user_id) ON DELETE RESTRICT,
    copy_id     INTEGER NOT NULL REFERENCES BookCopy(copy_id) ON DELETE CASCADE,
    loan_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date    DATE NOT NULL,
    return_date DATE,
    CHECK (due_date > loan_date),
    CHECK (return_date >= loan_date)
);
CREATE UNIQUE INDEX loan_one_open_per_copy ON Loan(copy_id) WHERE return_date IS NULL;

CREATE TABLE Review
(
    review_id  SERIAL PRIMARY KEY,
    user_id    VARCHAR(20) NOT NULL REFERENCES Users(user_id) ON DELETE RESTRICT,
    book_id    INTEGER NOT NULL REFERENCES Book(book_id) ON DELETE CASCADE,
    rating     SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment    TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (user_id, book_id)
);

CREATE TABLE Reservation
(
    reservation_id SERIAL PRIMARY KEY,
    user_id        VARCHAR(20) NOT NULL REFERENCES Users(user_id) ON DELETE RESTRICT,
    book_id        INTEGER NOT NULL REFERENCES Book(book_id) ON DELETE CASCADE,
    status         VARCHAR(10) NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'fulfilled', 'cancelled')),
    reserved_at    TIMESTAMP NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX reservation_one_waiting ON Reservation(user_id, book_id) WHERE status = 'waiting';
`;

// ---------- seed data (dates are "days before today") ----------

const users = 
[
    // [user_id, password, name, role]
    ['admin', 'admin1234', 'Admin', 'admin'],
    ['alice', 'user1234' , 'Alice', 'user'],
    ['bob', 'user1234', 'Bob', 'user'],
    ['carol', 'user1234', 'Carol', 'user'],
    ['dave', 'user1234', 'Dave', 'user'],
    ['erin', 'user1234', 'Erin', 'user'],
    ['frank', 'user1234', 'Frank', 'user'],
];

const authors = ['J.R.R. Tolkien', 'Isaac Asimov', 'Agatha Christie', 'Frank Herbert', 'Yuval Noah Harari'];

const categories = ['Fantasy', 'Science Fiction', 'Mystery', 'History', 'Classic'];

const books = 
[
    // [key, title, author, published_year, copies, categories]
    ['hobbit', 'The Hobbit', 'J.R.R. Tolkien', 1937, 3, ['Fantasy', 'Classic']],
    ['lotr', 'The Lord of the Rings', 'J.R.R. Tolkien', 1954, 2, ['Fantasy', 'Classic']],
    ['foundation', 'Foundation', 'Isaac Asimov', 1951, 3, ['Science Fiction', 'Classic']],
    ['robot', 'I, Robot', "Isaac Asimov", 1950, 2, ['Science Fiction']],
    ['dune', 'Dune', 'Frank Herbert', 1965, 2, ['Science Fiction', 'Fantasy']],
    ['andthen', 'And Then There Were None', 'Agatha Christie', 1939, 2, ['Mystery', 'Classic']],
    ['orient', 'Murder on the Orient Express', 'Agatha Christie', 1934, 2, ['Mystery']],
    ['sapiens', 'Sapiens', 'Yuval Noah Harari', 2011, 2, ['History']],
    ['deus', 'Homo Deus', 'Yuval Noah Harari', 2015, 1, ['History']],
    ['lessons', '21 Lessons for the 21st Century', 'Yuval Noah Harari', 2018, 1, ['History']],
];

const loans = 
[
    // [user, book key, copy index, loaned days ago, returned days ago or null]
    // still borrowed: bob is at the limit, carol is overdue, both orient copies are out
    ['alice', 'hobbit', 0, 2, null],
    ['alice', 'orient', 0, 1, null],
    ['bob', 'foundation', 0, 3, null],
    ['bob', 'sapiens', 0, 4, null],
    ['bob', 'robot', 0, 1, null],
    ['carol', 'andthen', 0, 10, null],
    ['dave', 'orient', 1, 2, null],
    // returned, within the last 3 months
    ['alice', 'hobbit', 1, 80, 75],
    ['bob', 'hobbit', 2, 60, 52],
    ['carol', 'hobbit', 1, 40, 35],
    ['dave', 'hobbit', 2, 20, 15],
    ['erin', 'hobbit', 1, 12, 8],
    ['alice', 'dune', 0, 70, 64],
    ['carol', 'dune', 1, 50, 41],
    ['erin', 'dune', 0, 30, 25],
    ['bob', 'dune', 0, 15, 10],
    ['dave', 'dune', 1, 14, 9],
    ['dave', 'foundation', 1, 65, 60],
    ['alice', 'foundation', 2, 45, 38],
    ['erin', 'foundation', 1, 25, 20],
    ['carol', 'orient', 0, 35, 30],
    ['bob', 'orient', 0, 9, 2],
    ['erin', 'orient', 1, 8, 3],
    ['dave', 'andthen', 1, 55, 48],
    ['alice', 'andthen', 1, 22, 18],
    ['erin', 'sapiens', 1, 33, 27],
    ['dave', 'sapiens', 1, 10, 6],
    ['carol', 'lotr', 0, 75, 70],
    ['dave', 'robot', 1, 85, 79],
    ['frank', 'robot', 1, 30, 24],
    ['alice', 'deus', 0, 50, 44],
    ['frank', 'deus', 0, 25, 19],
    ['bob', 'lessons', 0, 42, 37],
    // older than 3 months: in the monthly statistics, not in the charts
    ['alice', 'lotr', 0, 170, 163],
    ['bob', 'lotr', 1, 160, 150],
    ['carol', 'lessons', 0, 150, 144],
    ['dave', 'deus', 0, 140, 133],
    ['erin', 'lotr', 0, 130, 124],
    ['alice', 'robot', 1, 120, 112],
    ['erin', 'lessons', 0, 115, 108],
    ['bob', 'andthen', 0, 110, 105],
    ['dave', 'lotr', 1, 100, 95],
    ['carol', 'robot', 0, 95, 88],
];

const reviews = 
[
    // [user, book key, rating, comment] - every reviewer has borrowed the book
    ['alice', 'hobbit', 5, '처음 읽어도, 다시 읽어도 즐거운 모험.'],
    ['carol', 'hobbit', 4, '반지의 제왕 입문용으로 딱 좋다.'],
    ['erin', 'hobbit', 5, '아이와 같이 읽기 좋았어요.'],
    ['alice', 'dune', 4, '세계관이 압도적이다. 초반은 조금 어렵다.'],
    ['carol', 'dune', 3, '설정이 방대해서 읽는 데 오래 걸렸다.'],
    ['bob', 'dune', 5, 'SF를 좋아한다면 꼭 읽어야 할 책.'],
    ['dave', 'andthen', 5, '마지막까지 범인을 못 맞혔다.'],
    ['alice', 'andthen', 4, '긴장감이 대단하다.'],
    ['erin', 'sapiens', 4, '인류사를 보는 시각이 넓어졌다.'],
    ['dave', 'sapiens', 3, '흥미롭지만 일부 주장은 과감하다.'],
    ['bob', 'lotr', 5, '판타지의 교과서.'],
    ['carol', 'orient', 4, '반전이 인상적이다.'],
    ['dave', 'foundation', 4, '아이디어가 지금 읽어도 신선하다.'],
    ['alice', 'deus', 3, '사피엔스보다는 덜 인상적이었다.'],
];

const reservations = [
    // [user, book key, status, reserved days ago]
    ['alice', 'dune', 'cancelled', 12],
    ['dave', 'orient', 'fulfilled', 5],
    ['erin', 'orient', 'waiting', 1],
    ['frank', 'orient', 'waiting', 0],
];

const seed = async (client) =>
{
    for (const [userId, password, name, role] of users)
    {
        await client.query('INSERT INTO Users (user_id, password_hash, name, role) VALUES ($1, $2, $3, $4)', [userId, await hashPassword(password), name, role]);
    }

    const authorIds = {};
    for (const name of authors)
    {
        const { rows } = await client.query('INSERT INTO Author (author_name) VALUES ($1) RETURNING author_id', [name]);
        authorIds[name] = rows[0].author_id;
    }

    const categoryIds = {};
    for (const name of categories)
    {
        const { rows } = await client.query('INSERT INTO Category (category_name) VALUES ($1) RETURNING category_id', [name]);
        categoryIds[name] = rows[0].category_id;
    }

    const bookIds = {};
    const copyIds = {};
    for (const [key, title, author, year, copies, cats] of books)
    {
        const { rows } = await client.query('INSERT INTO Book (title, author_id, published_year) VALUES ($1, $2, $3) RETURNING book_id', [title, authorIds[author], year]);
        const bookId = rows[0].book_id;
        bookIds[key] = bookId;
        copyIds[key] = [];
        for (let n = 1; n <= copies; n++)
        {
            const copy = await client.query(
                `INSERT INTO BookCopy (book_id, call_number, acquired_date)
                VALUES ($1, $2, CURRENT_DATE - 200) RETURNING copy_id`,
                [bookId, `B${bookId}-${n}`]
            );
            copyIds[key].push(copy.rows[0].copy_id);
        }
        for (const cat of cats)
        {
            await client.query(
                'INSERT INTO Book_Category (book_id, category_id) VALUES ($1, $2)',
                [bookId, categoryIds[cat]]
            );
        }
    }

    for (const [userId, key, copy, loanedAgo, returnedAgo] of loans)
    {
        await client.query(
            `INSERT INTO Loan (user_id, copy_id, loan_date, due_date, return_date)
            VALUES ($1, $2, CURRENT_DATE - $3::int, CURRENT_DATE - $3::int + 7, CURRENT_DATE - $4::int)`,
            [userId, copyIds[key][copy], loanedAgo, returnedAgo]
        );
    }
    // a copy is 'borrowed' exactly when it has an unreturned loan
    await client.query(
        `UPDATE BookCopy SET status = 'borrowed'
        WHERE copy_id IN (SELECT copy_id FROM Loan WHERE return_date IS NULL)`
    );

    for (const [userId, key, rating, comment] of reviews)
    {
        await client.query
        (
            `INSERT INTO Review (user_id, book_id, rating, comment) VALUES ($1, $2, $3, $4)`,
            [userId, bookIds[key], rating, comment]
        );
    }

    for (const [userId, key, status, daysAgo] of reservations)
    {
        await client.query
        (
            `INSERT INTO Reservation (user_id, book_id, status, reserved_at)
            VALUES ($1, $2, $3, now() - make_interval(days => $4))`,
            [userId, bookIds[key], status, daysAgo]
        );
    }
};

const initDB = async () =>
{
    const client = await db.pool.connect();
    try
    {
        await client.query('BEGIN');

        console.log('Deleting existing tables...');
        await client.query(`DROP TABLE IF EXISTS ${TABLES.join(', ')} CASCADE`);

        console.log('Creating new tables...');
        await client.query(CREATE_SQL);

        console.log('Inserting seed data...');
        await seed(client);

        await client.query('COMMIT');

        for (const table of TABLES)
        {
            const { rows } = await client.query(`SELECT COUNT(*) AS n FROM ${table}`);
            console.log(`  ${table.padEnd(14)} ${rows[0].n}`);
        }
        console.log('Database initialization completed successfully.');
    }
    catch (err)
    {
        await client.query('ROLLBACK');
        console.error('Database initialization failed:', err);
        process.exitCode = 1;
    }
    finally
    {
        client.release();
        await db.pool.end();
    }
};

initDB();
