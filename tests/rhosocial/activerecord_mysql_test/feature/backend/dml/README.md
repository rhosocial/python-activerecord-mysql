# dml tests

MySQL-specific DML: INSERT IGNORE, ON CONFLICT mapped to ON DUPLICATE KEY UPDATE (capability + rendering), LOAD DATA INFILE bulk import, REPLACE INTO, and integration tests for the dialect security fixes.

## Key files

- `test_dialect_security_integration.py` — security fixes executed against a real server
- `test_insert_ignore.py` — INSERT IGNORE (sync/async)
- `test_insert_on_conflict_clauses.py` — ON DUPLICATE KEY UPDATE capabilities/rendering
- `test_load_data.py` — LOAD DATA INFILE
- `test_replace_into.py` — REPLACE INTO
