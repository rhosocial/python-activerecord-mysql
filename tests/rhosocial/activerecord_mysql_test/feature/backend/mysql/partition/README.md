# mysql/partition tests

MySQL partitioned-table coverage: partition expression construction and safety, ADD/DROP/REORGANIZE partition operations, strategies beyond RANGE COLUMNS (incl. subpartitions and production-style time partitions), and EXPLAIN on partitioned tables.

## Key files

- `test_partition_explain.py` — EXPLAIN on partitioned tables
- `test_partition_expressions.py` — partition expression construction and safety
- `test_partition_operations.py` — ADD/DROP/REORGANIZE partition operations
- `test_partition_strategy_operations.py` — partition strategies beyond RANGE COLUMNS
