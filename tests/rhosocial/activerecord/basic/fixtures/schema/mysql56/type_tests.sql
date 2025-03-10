CREATE TABLE `type_tests` (
    `id` VARCHAR(36) NOT NULL,
    `string_field` VARCHAR(255) NOT NULL,
    `int_field` INT NOT NULL,
    `float_field` FLOAT NOT NULL,
    `decimal_field` DECIMAL(10,2) NOT NULL,
    `bool_field` TINYINT(1) NOT NULL,
    `datetime_field` DATETIME NOT NULL,
    `json_field` TEXT,           -- Using TEXT for JSON in MySQL 5.6
    `nullable_field` VARCHAR(255),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;