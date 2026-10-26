const db = require('../config/db');

const initDB = async () => {
    try {
        // Drop existing tables in the correct order
        console.log('Deleting existing tables...');
        // TODO: 기존 테이블 제거하는 코드를 작성하세요.

        // Create tables
        console.log('Creating new tables...');
        // TODO: 설계한 스키마에 맞춰 새로운 테이블을 생성하는 코드를 작성하세요.

        console.log('Database initialization completed successfully.');
    } catch (err) {
        console.error('Database initialization failed:', err);
    } finally {
        db.pool.end();
    }
};

initDB();
