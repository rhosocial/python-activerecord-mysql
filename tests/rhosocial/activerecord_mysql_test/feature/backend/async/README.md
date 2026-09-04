# async tests

AsyncMySQLBackend coverage: async CRUD and column mapping, asyncio.create_task concurrency limits of the driver, error-class handling, and the actual effects of async transaction isolation levels and modes.

## Key files

- `test_async_column_mapping_backend.py` — async column type mapping
- `test_async_concurrency.py` — asyncio.create_task scenarios and driver limitations
- `test_async_crud_backend.py` — async CRUD against a live server
- `test_async_error_handling.py` — MySQL error classes surfaced by the async backend
- `test_async_transaction_backend.py` — async transaction begin/commit/rollback
- `test_async_transaction_isolation_effect.py` — isolation level / mode effects, nested transactions
