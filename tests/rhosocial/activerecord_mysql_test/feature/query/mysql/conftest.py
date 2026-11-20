# tests/rhosocial/activerecord_mysql_test/feature/query/mysql/conftest.py
"""L2 backend fixtures for the MySQL-only query tests.

These tests are backend-specific, so the fixture group lives here rather than
in the shared suite; the table definitions still come from the query topic.

- ``database``: one database per directory (session scope, emptied at start);
- ``schema``: only the tables this module declares in ``TABLES``, dropped and
  recreated for every test (function scope), so each test starts from empty
  tables.

A module declares what it needs and nothing else: a dialect-only module needs
no table at all, and a directory-wide "create every table" would make it fail
on a server whose index limit refuses ``order_items``.
"""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

from pathlib import Path

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.testsuite.feature.query.conftest import *  # noqa: F401,F403
from rhosocial.activerecord.testsuite.feature.query.fixtures.definitions import (
    JsonUsersDefinition,
    OrderItemsDefinition,
    OrdersDefinition,
    UsersDefinition,
)

DDL = ExecutionOptions(stmt_type=StatementType.DDL)

#: Table name -> the definition that declares it.  The suite's definitions are
#: used unchanged; a server that cannot hold one of their keys skips the module
#: rather than seeing the concept shrunk for it.
FAMILIES = {
    "json_users": JsonUsersDefinition,
    "users": UsersDefinition,
    "orders": OrdersDefinition,
    "order_items": OrderItemsDefinition,
}


def _database_name() -> str:
    """Database name from this directory's namespace (below ``feature``)."""
    parts = Path(__file__).parent.parts
    start = parts.index("feature") + 1
    return "test_" + "_".join(parts[start:])


def _declared(request) -> tuple:
    """The families the module declares in ``TABLES``."""
    names = tuple(getattr(request.module, "TABLES", ()))
    unknown = [name for name in names if name not in FAMILIES]
    if unknown:
        raise LookupError(
            f"{request.module.__name__} declares unknown query tables: {unknown}"
        )
    return names


def _key_too_long(error) -> bool:
    """Whether the server refused a key for exceeding its length limit.

    MySQL 5.6 answers ``1071 (42000): Specified key was too long`` for the
    suite's ``VARCHAR(255)`` key columns (767 bytes with ``utf8mb4``).
    """
    return getattr(error, "driver_code", None) == 1071 or "1071" in str(error)




# This directory owns a database shared by all its tests within a scenario;
# pin them to one worker so setup/teardown never races on the same database.
DECLARATION = Declaration(
    # This scope opens a database; the plugin enforces this declaration.
    uses_database=True,
    parallel=True,
    purpose="Directory-owned database shared by this test group.",
)

@pytest.fixture(scope="session")
def database_config(backend_scenario):
    """The scenario, its connection configuration, and the database name."""
    name = _database_name()
    return backend_scenario, backend_scenario.make_config(name), name


@pytest.fixture(scope="session")
def database(database_config):
    """The directory's database, prepared once and left for later files."""
    scenario, config, name = database_config
    scenario.reset_database(name)
    backend = scenario.backend_class(connection_config=config)
    backend.connect()
    backend.introspect_and_adapt()
    yield backend
    backend.disconnect()


@pytest.fixture(scope="function", autouse=True)
def schema(database, request):
    """Drop and recreate only the tables this module declares, before every test."""
    created = []
    try:
        for name in _declared(request):
            fixture = FAMILIES[name](database.dialect)
            try:
                database.execute(*fixture.create_table.to_sql(), options=DDL)
            except DatabaseError as error:
                if not _key_too_long(error):
                    raise
                pytest.skip(
                    f"this server refuses {name}'s unique key: {error} -- "
                    "the suite's VARCHAR(255) key column exceeds this server's "
                    "index length limit"
                )
            created.append(fixture)
        yield
    finally:
        for fixture in reversed(created):
            database.execute(*fixture.drop_table.to_sql(), options=DDL)
