-- tests/rhosocial/activerecord_mysql_test/basic/fixtures/schema/mysql80/type_tests.sql
CREATE TABLE `type_tests` (
    `id` VARCHAR(36) NOT NULL,
    `string_field` VARCHAR(255) NOT NULL,
    `int_field` INT NOT NULL,
    `float_field` FLOAT NOT NULL,
    `decimal_field` DECIMAL(10,2) NOT NULL,
    `bool_field` BOOLEAN NOT NULL,
    `datetime_field` VARCHAR(50) NOT NULL,
    `json_field` JSON,           -- Native JSON type in MySQL 8.0
    `nullable_field` VARCHAR(255),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;