CREATE TABLE `orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `total` DECIMAL(10,2) NOT NULL,
    `created_at` TEXT,
    `updated_at` TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
