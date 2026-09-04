# adapters tests

Offline round-trip coverage for the MySQL type adapters (to_database / from_database, including None semantics), plus ENUM adapter integration tests and unit tests for the SET / VECTOR adapter internals.

## Key files

- `test_adapters.py` — offline adapter round trips (BLOB, JSON, UUID, boolean, decimal, date/time, vector, ...)
- `test_adapters_backend.py` — SET / VECTOR adapter decode and integration helpers
- `test_date_adapter.py` — MySQLDateAdapter regressions (datetime-vs-date isinstance ordering)
- `test_enum_adapter.py` — ENUM adapter unit tests
- `test_enum_adapter_backend.py` — ENUM adapter against a live server (sync/async)
