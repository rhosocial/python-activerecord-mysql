# concurrency tests

Concurrency protocol coverage: ConcurrencyAware implementation checks for MySQLBackend / AsyncMySQLBackend, and asyncio.create_task scenarios including driver concurrency-limit behaviors.

## Key files

- `test_concurrency_protocol.py` — ConcurrencyAware implementation checks (sync)
- `test_concurrency_protocol_async.py` — asyncio.create_task scenarios and driver limitations
