-- tests/rhosocial/activerecord_mysql_test/feature/basic/schema/column_mapping_items.sql
CREATE TABLE `column_mapping_items` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name` TEXT NOT NULL,
    `item_total` INT NOT NULL,
    `remarks` INT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB;
