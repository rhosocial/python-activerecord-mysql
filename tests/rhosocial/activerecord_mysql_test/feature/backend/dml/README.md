# dml tests

MySQL-specific DML: real-database CRUD (sync/async), backend-integrated column type mapping (sync/async), INSERT IGNORE, ON CONFLICT mapped to ON DUPLICATE KEY UPDATE (capability + rendering), LOAD DATA INFILE, and REPLACE INTO. Dialect security integration tests live in `../dialect/`.

## Key files

- `test_column_mapping_backend.py` — backend-integrated column type mapping (sync)
- `test_column_mapping_backend_async.py` — async twin of `test_column_mapping_backend.py`
- `test_crud_backend.py` — real-database CRUD (sync)
- `test_crud_backend_async.py` — async CRUD against a live server
- `test_insert_ignore.py` — INSERT IGNORE (sync/async)
- `test_insert_on_conflict_clauses.py` — ON DUPLICATE KEY UPDATE capabilities/rendering
- `test_load_data.py` — LOAD DATA INFILE
- `test_replace_into.py` — REPLACE INTO
