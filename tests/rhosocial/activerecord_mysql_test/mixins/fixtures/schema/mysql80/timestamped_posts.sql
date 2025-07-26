-- tests/rhosocial/activerecord_mysql_test/mixins/fixtures/schema/mysql80/timestamped_posts.sql
CREATE TABLE timestamped_posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at VARCHAR(50) NOT NULL,
    updated_at VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;