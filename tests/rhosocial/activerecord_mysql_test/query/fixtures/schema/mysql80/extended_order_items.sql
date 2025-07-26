-- tests/rhosocial/activerecord_mysql_test/query/fixtures/schema/mysql80/extended_order_items.sql
CREATE TABLE extended_order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(255) DEFAULT '',
    region VARCHAR(255) DEFAULT '',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES extended_orders(id)
);