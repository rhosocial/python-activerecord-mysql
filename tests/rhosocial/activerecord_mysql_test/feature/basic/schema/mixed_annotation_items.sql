-- tests/rhosocial/activerecord_mysql_test/feature/basic/schema/mixed_annotation_items.sql
CREATE TABLE `mixed_annotation_items` (
    `id` INT NOT NULL,
    `name` TEXT NOT NULL,
    `tags` TEXT,
    `meta` TEXT,
    `description` TEXT,
    `status` VARCHAR(255),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB;
