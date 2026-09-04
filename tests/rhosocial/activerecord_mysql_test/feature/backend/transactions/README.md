# transactions tests

Real-server transaction behavior: the actual effects of isolation levels, transaction access modes and their combinations, nested transactions, plus backend-level transaction handling for sync and async backends.

## Key files

- `test_isolation_effect.py` — isolation level / mode effects and nesting
- `test_transaction_backend.py` — begin/commit/rollback against a live server
