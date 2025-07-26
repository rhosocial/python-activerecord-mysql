-- tests/rhosocial/activerecord_mysql_test/basic/fixtures/schema/mysql80/validated_users.sql
CREATE TABLE `validated_users` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL CHECK (LENGTH(`username`) BETWEEN 3 AND 50 AND `username` REGEXP '^[a-zA-Z0-9]+$'),
    `email` VARCHAR(255) NOT NULL,
    `age` INT CHECK (`age` BETWEEN 0 AND 150),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;