-- tests/rhosocial/activerecord_mysql_test/basic/fixtures/schema/mysql80/validated_field_users.sql
CREATE TABLE `validated_field_users` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(255) NOT NULL,
    `email` VARCHAR(255) NOT NULL,
    `age` INT,
    `balance` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `credit_score` INT NOT NULL DEFAULT 300,
    `status` ENUM('active', 'inactive', 'banned', 'pending', 'suspended') NOT NULL DEFAULT 'active',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;