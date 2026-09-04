# extensions tests

Vendor extension features: FULLTEXT index protocol and MATCH usage, JSON duality view execution on MySQL 9.7, and the SET type (protocol + real-database integration). Partition tests moved to `mysql/partition/`.

## Key files

- `test_fulltext_index.py` — FULLTEXT protocol and MATCH expressions
- `test_json_duality_view_execution.py` — duality view DDL/DML execution
- `test_set_type.py` — SET type protocol
- `test_set_type_backend.py` — SET type integration
