-- tests/rhosocial/activerecord_mysql_test/feature/basic/schema/type_tests.sql
-- MySQL version of the type_tests table schema

CREATE TABLE `type_tests` (
    `id` CHAR(36) NOT NULL PRIMARY KEY, -- UUID as char(36)
    `string_field` VARCHAR(255) NOT NULL DEFAULT 'test string',
    `int_field` INT NOT NULL DEFAULT 42,
    `float_field` FLOAT NOT NULL DEFAULT 3.14,
    `decimal_field` DECIMAL(10,2) NOT NULL DEFAULT 10.99,
    `bool_field` TINYINT NOT NULL DEFAULT 1,
    `datetime_field` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `json_field` JSON,
    `nullable_field` VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;