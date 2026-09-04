# backend tests

MySQLBackend integration tests: explain() (sync/async), connection resilience (timeout, kill, ping/reconnect, interruption recovery), real-server CRUD, cursor result-set pollution, datetime-interval EXPLAIN examples and operational maintenance scenarios.

## Key files

- `test_backend_explain.py` — Backend.explain() protocol and formats
- `test_connection_resilience.py` — connection loss / recovery matrix, shared backends
- `test_crud_backend.py` — real-database CRUD
- `test_cursor_pollution.py` — result-set pollution after get_server_version()
- `test_datetime_interval_explain_examples.py` — EXPLAIN plans for interval expressions/indexes
- `test_operational_maintenance.py` — operational maintenance scenarios
