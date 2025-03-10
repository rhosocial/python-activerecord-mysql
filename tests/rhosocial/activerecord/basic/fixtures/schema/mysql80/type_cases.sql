CREATE TABLE `type_cases` (
    `id` VARCHAR(36) NOT NULL,
    `username` VARCHAR(255) NOT NULL,
    `email` VARCHAR(255) NOT NULL,
    `tiny_int` TINYINT,
    `small_int` SMALLINT,
    `big_int` BIGINT,
    `float_val` FLOAT,
    `double_val` DOUBLE,
    `decimal_val` DECIMAL(10,4),
    `char_val` CHAR(255),
    `varchar_val` VARCHAR(255),
    `text_val` TEXT,
    `date_val` DATE,
    `time_val` TIME,
    `timestamp_val` FLOAT,
    `blob_val` BLOB,
    `json_val` JSON,             -- Native JSON type in MySQL 8.0
    `array_val` JSON,            -- Using JSON for array storage in MySQL 8.0
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;