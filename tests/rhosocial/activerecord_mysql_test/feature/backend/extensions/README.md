# extensions tests

Vendor extension features: FULLTEXT index protocol and MATCH usage, JSON duality view execution on MySQL 9.7, partition EXPLAIN / operations / strategies (incl. subpartitions and production-style time partitions), and the SET type (protocol + real-database integration).

## Key files

- `test_fulltext_index.py` — FULLTEXT protocol and MATCH expressions
- `test_json_duality_view_execution.py` — duality view DDL/DML execution
- `test_partition_explain.py` — EXPLAIN on partitioned tables
- `test_partition_expressions.py` — partition expression construction and safety
- `test_partition_operations.py` — ADD/DROP/REORGANIZE partition operations
- `test_partition_strategy_operations.py` — partition strategies beyond RANGE COLUMNS
- `test_set_type.py` — SET type protocol
- `test_set_type_backend.py` — SET type integration
