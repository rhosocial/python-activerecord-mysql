-- tests/rhosocial/activerecord_mysql_test/query/fixtures/schema/mysql80/extended_orders.sql
CREATE TABLE extended_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    order_number VARCHAR(255) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    status VARCHAR(255) NOT NULL DEFAULT 'pending',
    priority VARCHAR(255) DEFAULT 'medium',
    region VARCHAR(255) DEFAULT 'default',
    category VARCHAR(255) DEFAULT '',
    product VARCHAR(255) DEFAULT '',
    department VARCHAR(255) DEFAULT '',
    year VARCHAR(255) DEFAULT '',
    quarter VARCHAR(255) DEFAULT '',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);