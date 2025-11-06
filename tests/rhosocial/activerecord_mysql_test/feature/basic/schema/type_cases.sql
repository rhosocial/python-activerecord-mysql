-- tests/rhosocial/activerecord_mysql_test/feature/basic/schema/type_cases.sql
-- MySQL version of the type_cases table schema

CREATE TABLE `type_cases` (
    `id` CHAR(36) NOT NULL PRIMARY KEY, -- UUID as char(36)
    `username` VARCHAR(255) NOT NULL,
    `email` VARCHAR(255) NOT NULL,
    `tiny_int` TINYINT,
    `small_int` SMALLINT,
    `big_int` BIGINT,
    `float_val` FLOAT,
    `double_val` DOUBLE,
    `decimal_val` DECIMAL(10,4),
    `char_val` CHAR(10),
    `varchar_val` VARCHAR(255),
    `text_val` TEXT,
    `date_val` DATE,
    `time_val` TIME(6),
    `timestamp_val` DATETIME(6),
    `blob_val` BLOB,
    `json_val` JSON,
    `array_val` JSON, -- MySQL doesn't have native array type, using JSON
    `is_active` TINYINT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;