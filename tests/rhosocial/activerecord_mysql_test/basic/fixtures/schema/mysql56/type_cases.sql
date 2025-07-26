-- tests/rhosocial/activerecord_mysql_test/basic/fixtures/schema/mysql56/type_cases.sql
CREATE TABLE `type_cases` (
    `id` VARCHAR(36) NOT NULL,
    `username` VARCHAR(255) NOT NULL,
    `email` VARCHAR(255) NOT NULL,
    `tiny_int` TINYINT,
    `small_int` SMALLINT,
    `big_int` BIGINT,
    `float_val` FLOAT,
    `double_val` DOUBLE,
    `decimal_val` DECIMAL(10,2),
    `char_val` CHAR(255),
    `varchar_val` VARCHAR(255),
    `text_val` TEXT,
    `date_val` DATE,
    `time_val` TIME,
    `timestamp_val` TIMESTAMP,
    `blob_val` BLOB,
    `json_val` TEXT,          -- MySQL 5.6 doesn't have native JSON type
    `array_val` TEXT,          -- Arrays stored as TEXT in MySQL 5.6
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;