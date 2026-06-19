CREATE TABLE `store_inventory` (
    `store_id` INT NOT NULL,
    `product_id` INT NOT NULL,
    `batch_id` VARCHAR(64) NOT NULL,
    `stock` INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`store_id`, `product_id`, `batch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
