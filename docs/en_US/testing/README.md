# Testing

This section covers testing for the MySQL backend.

## Contents

- [Test Configuration](configuration.md): MySQL-specific test setup
- [Local Testing](local.md): Docker-based local test environment

## Testing Principles

### Sync/Async Parity

All tests involving IO operations must prepare paired sync and async tests for equivalent scenarios:

```python
# Sync test
def test_create_user():
    user = User(name="Alice").create()
    assert user.id is not None

# Async test -- same logic, async API
async def test_async_create_user():
    user = await AsyncUser(name="Alice").create()
    assert user.id is not None
```

### Expression Tests -- No IO

Expression tests involve no database IO -- they only build SQL and validate the generated SQL:

```python
def test_expression_sql():
    expr = Eq(User.name, "Alice")
    assert expr.to_sql(dialect) == "`name` = %s"
    assert expr.params == ["Alice"]
```

No async counterpart is needed for expression tests.

### ActiveRecord Tests -- Use Testsuite

ActiveRecord feature tests (model CRUD, relationships, queries) use the testsuite:

```bash
cd python-activerecord-mysql
PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/pytest \
    ../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/relation/
```

### Test Categories Summary

| What to Test | Approach | IO? | Async? |
|-------------|----------|-----|--------|
| Expression classes (dialect SQL generation) | Unit tests, no DB | No | No |
| Type adapters (type conversion) | Unit tests, no DB | No | No |
| Named features (expression, procedure, migration) | CLI scripts | Yes | If supported |
| ActiveRecord features (CRUD, relations, queries) | Testsuite + provider | Yes | Yes |
| MySQL-specific features (JSON, spatial, etc.) | Project-specific tests | Yes | Yes |

## MySQL-Specific Notes

### Async Cursor Cleanup

Failing to close cursors before disconnecting can cause `RuntimeError: Set changed size during iteration`. Always ensure cursors are properly closed in async test teardown.

### Table Conflicts

Not dropping tables between test runs causes "table already exists" errors. Use `DROP TABLE IF EXISTS` in test setup or fixtures.

### Provider Implementation

For provider implementation guidelines, see the [Core Testsuite Provider Guide](provider_guide.md).

AI Prompt: "How do I set up a MySQL test database with Docker for CI?"
