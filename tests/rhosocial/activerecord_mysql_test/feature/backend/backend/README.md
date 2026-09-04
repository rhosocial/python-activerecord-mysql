# backend tests

MySQLBackend integration tests: connection resilience (timeout, kill, ping/reconnect, interruption recovery), cursor result-set pollution, error-class handling (sync/async) and operational maintenance scenarios. EXPLAIN and real-server CRUD live in `query/` and `dml/` respectively.

## Key files

- `test_connection_resilience.py` — connection loss / recovery matrix, shared backends
- `test_cursor_pollution.py` — result-set pollution after get_server_version()
- `test_error_handling_async.py` — MySQL error classes surfaced by the async backend (sync twin pending, Tier-2 fill)
- `test_operational_maintenance.py` — operational maintenance scenarios
