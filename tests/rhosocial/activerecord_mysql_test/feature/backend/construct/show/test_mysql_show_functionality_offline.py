# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/show/
# test_mysql_show_functionality_offline.py
"""Pure-mock unit tests for MySQL SHOW ``functionality`` (sync and async).

MySQL ships a native async driver (``mysql.connector.aio``), so both
``MySQLShowFunctionality`` and ``AsyncMySQLShowFunctionality`` must be covered.
Neither class is exercised against a real server here: ``backend.execute`` is a
``MagicMock`` / ``AsyncMock`` that returns a tiny result object whose ``.data``
holds controlled rows, and the dialect is a real :class:`MySQLDialect` so the
expressions still render actual SQL.

Every test verifies two things for its method:

* the returned value is mapped into the expected dataclass from ``.types``; and
* ``backend.execute`` received the rendered ``(sql, params)`` pair.

No socket, no driver, no database is touched.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.show.functionality import (
    AsyncMySQLShowFunctionality,
    MySQLShowFunctionality,
)
from rhosocial.activerecord.backend.impl.mysql.show.types import (
    ShowCharsetResult,
    ShowCollationResult,
    ShowColumnResult,
    ShowCreateTableResult,
    ShowCreateTriggerResult,
    ShowCreateViewResult,
    ShowDatabaseResult,
    ShowEngineResult,
    ShowGrantResult,
    ShowIndexResult,
    ShowPluginResult,
    ShowProcessListResult,
    ShowStatusResult,
    ShowTableResult,
    ShowTableStatusResult,
    ShowTriggerResult,
    ShowVariableResult,
    ShowWarningResult,
)

# --------------------------------------------------------------------------- #
# Helpers and controlled rows
# --------------------------------------------------------------------------- #


def _result(rows):
    """The shape the parsing helpers read: an object with a ``.data`` list."""
    return SimpleNamespace(data=rows)


CREATE_TABLE_ROWS = [{"Table": "users", "Create Table": "CREATE TABLE `users` (`id` int)"}]
CREATE_VIEW_ROWS = [
    {
        "View": "active_users",
        "Create View": "CREATE VIEW `active_users` AS SELECT 1",
        "character_set_client": "utf8mb4",
        "collation_connection": "utf8mb4_general_ci",
    }
]
COLUMN_ROWS = [
    {
        "Field": "id",
        "Type": "int",
        "Null": "NO",
        "Key": "PRI",
        "Default": None,
        "Extra": "auto_increment",
    },
    {
        "Field": "name",
        "Type": "varchar(255)",
        "Null": "YES",
        "Key": "",
        "Default": None,
        "Extra": "",
    },
]
FULL_COLUMN_ROWS = [
    {
        "Field": "id",
        "Type": "int",
        "Null": "NO",
        "Key": "PRI",
        "Default": None,
        "Extra": "",
        "Collation": None,
        "Privileges": "select,insert,update",
        "Comment": "primary key",
    }
]
INDEX_ROWS = [
    {
        "Table": "users",
        "Non_unique": 0,
        "Key_name": "PRIMARY",
        "Seq_in_index": 1,
        "Column_name": "id",
        "Collation": "A",
        "Cardinality": 12,
        "Sub_part": None,
        "Packed": None,
        "Null": None,
        "Index_type": "BTREE",
        "Comment": "",
        "Index_comment": "cmt",
        "Visible": "YES",
        "Expression": None,
    }
]
TABLE_ROWS_BASIC = [{"Tables_in_testdb": "users"}]
TABLE_ROWS_FULL = [
    {"Tables_in_testdb": "users", "Table_type": "BASE TABLE"},
    {"Tables_in_testdb": "active_users", "Table_type": "VIEW"},
]
DATABASE_ROWS = [{"Database": "mysql"}, {"Database": "testdb"}]
TABLE_STATUS_ROWS = [
    {
        "Name": "users",
        "Engine": "InnoDB",
        "Version": 10,
        "Row_format": "Dynamic",
        "Rows": 42,
        "Avg_row_length": 100,
        "Data_length": 4096,
        "Max_data_length": 0,
        "Index_length": 2048,
        "Data_free": 0,
        "Auto_increment": 43,
        "Create_time": "2026-01-01 00:00:00",
        "Update_time": "2026-01-02 00:00:00",
        "Check_time": None,
        "Collation": "utf8mb4_general_ci",
        "Checksum": None,
        "Create_options": "",
        "Comment": "user table",
    }
]
TRIGGER_ROWS = [
    {
        "Trigger": "bi_users",
        "Event": "INSERT",
        "Table": "users",
        "Statement": "SET NEW.x = 1",
        "Timing": "BEFORE",
        "Created": "2026-01-01 00:00:00",
        "sql_mode": "STRICT_TRANS_TABLES",
        "Definer": "root@localhost",
        "character_set_client": "utf8mb4",
        "collation_connection": "utf8mb4_general_ci",
        "Database Collation": "utf8mb4_general_ci",
    }
]
CREATE_TRIGGER_ROWS = [
    {
        "Trigger": "bi_users",
        "SQL Original Statement": "CREATE TRIGGER bi_users BEFORE INSERT ...",
        "character_set_client": "utf8mb4",
        "collation_connection": "utf8mb4_general_ci",
        "Database Collation": "utf8mb4_general_ci",
    }
]
VARIABLE_ROWS = [{"Variable_name": "max_connections", "Value": "151"}]
STATUS_ROWS = [{"Variable_name": "Threads_connected", "Value": "5"}]
PROCESSLIST_ROWS = [
    {
        "Id": 7,
        "User": "root",
        "Host": "localhost:52144",
        "Command": "Query",
        "Time": 0,
        "db": "testdb",
        "State": "executing",
        "Info": "SELECT 1",
    }
]
WARNING_ROWS = [{"Level": "Warning", "Code": 1265, "Message": "Data truncated"}]
ENGINE_ROWS = [
    {
        "Engine": "InnoDB",
        "Support": "DEFAULT",
        "Transactions": "YES",
        "XA": "YES",
        "Savepoints": "YES",
    }
]
CHARSET_ROWS = [
    {
        "Charset": "utf8mb4",
        "Description": "UTF-8 Unicode",
        "Default collation": "utf8mb4_general_ci",
        "Maxlen": 4,
    }
]
COLLATION_ROWS = [
    {
        "Collation": "utf8mb4_general_ci",
        "Charset": "utf8mb4",
        "Id": 45,
        "Default": "Yes",
        "Compiled": "Yes",
        "Sortlen": 1,
    }
]
GRANT_ROWS = [{"Grants for": "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost'"}]
PLUGIN_ROWS = [
    {
        "Name": "InnoDB",
        "Status": "ACTIVE",
        "Type": "STORAGE ENGINE",
        "Library": "ha_innodb.so",
        "License": "GPL",
    }
]


# --------------------------------------------------------------------------- #
# Shared field assertions (used by both sync and async tests)
# --------------------------------------------------------------------------- #


def _assert_create_table(obj):
    assert isinstance(obj, ShowCreateTableResult)
    assert obj.table_name == "users"
    assert "CREATE TABLE" in obj.create_statement


def _assert_create_view(obj):
    assert isinstance(obj, ShowCreateViewResult)
    assert obj.view_name == "active_users"
    assert "CREATE VIEW" in obj.create_statement
    assert obj.character_set_client == "utf8mb4"
    assert obj.collation_connection == "utf8mb4_general_ci"


def _assert_columns(items):
    assert len(items) == 2
    assert all(isinstance(item, ShowColumnResult) for item in items)
    assert items[0].field == "id"
    assert items[0].type == "int"
    assert items[0].null == "NO"
    assert items[0].key == "PRI"
    assert items[0].extra == "auto_increment"
    assert items[1].field == "name"
    assert items[1].privileges is None  # not FULL


def _assert_full_columns(items):
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ShowColumnResult)
    assert item.privileges == "select,insert,update"
    assert item.comment == "primary key"


def _assert_indexes(items):
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ShowIndexResult)
    assert item.table == "users"
    assert item.non_unique == 0
    assert item.key_name == "PRIMARY"
    assert item.seq_in_index == 1
    assert item.column_name == "id"
    assert item.index_type == "BTREE"
    assert item.visible == "YES"


def _assert_tables(items):
    assert len(items) == 2
    assert all(isinstance(item, ShowTableResult) for item in items)
    assert items[0].name == "users"
    assert items[0].table_type == "BASE TABLE"
    assert items[1].name == "active_users"
    assert items[1].table_type == "VIEW"


def _assert_basic_tables(items):
    assert len(items) == 1
    assert isinstance(items[0], ShowTableResult)
    assert items[0].name == "users"
    assert items[0].table_type is None


def _assert_databases(items):
    assert [item.name for item in items] == ["mysql", "testdb"]
    assert all(isinstance(item, ShowDatabaseResult) for item in items)


def _assert_table_status(items):
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ShowTableStatusResult)
    assert item.name == "users"
    assert item.engine == "InnoDB"
    assert item.rows == 42
    assert item.auto_increment == 43
    assert item.create_time == "2026-01-01 00:00:00"
    assert item.check_time is None
    assert item.comment == "user table"


def _assert_triggers(items):
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ShowTriggerResult)
    assert item.trigger == "bi_users"
    assert item.event == "INSERT"
    assert item.table == "users"
    assert item.timing == "BEFORE"
    assert item.database_collation == "utf8mb4_general_ci"


def _assert_create_trigger(obj):
    assert isinstance(obj, ShowCreateTriggerResult)
    assert obj.trigger_name == "bi_users"
    assert "CREATE TRIGGER" in obj.create_statement
    assert obj.database_collation == "utf8mb4_general_ci"


def _assert_variables(items):
    assert len(items) == 1
    assert isinstance(items[0], ShowVariableResult)
    assert items[0].variable_name == "max_connections"
    assert items[0].value == "151"


def _assert_status(items):
    assert len(items) == 1
    assert isinstance(items[0], ShowStatusResult)
    assert items[0].variable_name == "Threads_connected"
    assert items[0].value == "5"


def _assert_processlist(items):
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ShowProcessListResult)
    assert item.id == 7
    assert item.user == "root"
    assert item.command == "Query"
    assert item.db == "testdb"
    assert item.info == "SELECT 1"


def _assert_warnings(items):
    assert len(items) == 1
    assert isinstance(items[0], ShowWarningResult)
    assert items[0].level == "Warning"
    assert items[0].code == 1265
    assert items[0].message == "Data truncated"


def _assert_engines(items):
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ShowEngineResult)
    assert item.engine == "InnoDB"
    assert item.support == "DEFAULT"
    assert item.transactions == "YES"


def _assert_charset(items):
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ShowCharsetResult)
    assert item.charset == "utf8mb4"
    assert item.default_collation == "utf8mb4_general_ci"
    assert item.maxlen == 4


def _assert_collation(items):
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ShowCollationResult)
    assert item.collation == "utf8mb4_general_ci"
    assert item.charset == "utf8mb4"
    assert item.id == 45


def _assert_grants(items):
    assert len(items) == 1
    assert isinstance(items[0], ShowGrantResult)
    assert "GRANT ALL PRIVILEGES" in items[0].grants


def _assert_plugins(items):
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ShowPluginResult)
    assert item.name == "InnoDB"
    assert item.status == "ACTIVE"
    assert item.type == "STORAGE ENGINE"
    assert item.license == "GPL"


# (method name, positional args, rows, assertion helper) for every single-row
# or list-returning public method. Used by the "maps rows" and "empty rows"
# parametrized tests below.
METHOD_CASES = [
    ("create_table", ("users",), CREATE_TABLE_ROWS, _assert_create_table),
    ("create_view", ("active_users",), CREATE_VIEW_ROWS, _assert_create_view),
    ("columns", ("users",), COLUMN_ROWS, _assert_columns),
    ("indexes", ("users",), INDEX_ROWS, _assert_indexes),
    ("tables", (), TABLE_ROWS_FULL, _assert_tables),
    ("databases", (), DATABASE_ROWS, _assert_databases),
    ("table_status", (), TABLE_STATUS_ROWS, _assert_table_status),
    ("triggers", (), TRIGGER_ROWS, _assert_triggers),
    ("create_trigger", ("bi_users",), CREATE_TRIGGER_ROWS, _assert_create_trigger),
    ("variables", (), VARIABLE_ROWS, _assert_variables),
    ("status", (), STATUS_ROWS, _assert_status),
    ("processlist", (), PROCESSLIST_ROWS, _assert_processlist),
    ("warnings", (), WARNING_ROWS, _assert_warnings),
    ("errors", (), WARNING_ROWS, _assert_warnings),
    ("engines", (), ENGINE_ROWS, _assert_engines),
    ("charset", (), CHARSET_ROWS, _assert_charset),
    ("collation", (), COLLATION_ROWS, _assert_collation),
    ("grants", (), GRANT_ROWS, _assert_grants),
    ("plugins", (), PLUGIN_ROWS, _assert_plugins),
]

# Methods whose single-object result becomes ``None`` on an empty result set.
SINGLETON_METHODS = {"create_table", "create_view", "create_trigger"}


@pytest.fixture
def sync_env():
    """A sync functionality backed by a mock backend with a real dialect."""
    backend = MagicMock()
    backend.dialect = MySQLDialect(version=(8, 0, 0))
    return backend, MySQLShowFunctionality(backend)


@pytest.fixture
def async_env():
    """An async functionality backed by a mock backend with an AsyncMock."""
    backend = MagicMock()
    backend.dialect = MySQLDialect(version=(8, 0, 0))
    backend.execute = AsyncMock()
    return backend, AsyncMySQLShowFunctionality(backend)


# --------------------------------------------------------------------------- #
# Sync class
# --------------------------------------------------------------------------- #


class TestMySQLShowFunctionalityOffline:
    """Offline coverage of the synchronous SHOW facade."""

    @pytest.mark.parametrize(
        "version,supports_invisible",
        [(None, True), ((5, 7, 0), False), ((8, 0, 0), True)],
    )
    def test_init_version_flags(self, version, supports_invisible):
        backend = MagicMock()
        backend.dialect = MySQLDialect(version=(8, 0, 0))
        func = MySQLShowFunctionality(backend, version=version)
        assert func._version == version
        assert func._supports_invisible_columns is supports_invisible
        assert func.dialect is backend.dialect

    @pytest.mark.parametrize("method,args,rows,assert_rows", METHOD_CASES)
    def test_maps_rows_into_dataclasses(self, sync_env, method, args, rows, assert_rows):
        backend, func = sync_env
        backend.execute.return_value = _result(rows)
        result = getattr(func, method)(*args)
        assert_rows(result)
        backend.execute.assert_called_once()
        sql, params = backend.execute.call_args[0]
        assert isinstance(sql, str) and sql.startswith("SHOW")
        assert isinstance(params, tuple)

    @pytest.mark.parametrize("method,args,rows,assert_rows", METHOD_CASES)
    def test_empty_rows(self, sync_env, method, args, rows, assert_rows):
        backend, func = sync_env
        backend.execute.return_value = _result([])
        result = getattr(func, method)(*args)
        if method in SINGLETON_METHODS:
            assert result is None
        else:
            assert result == []

    def test_single_column_tables_row(self, sync_env):
        backend, func = sync_env
        backend.execute.return_value = _result(TABLE_ROWS_BASIC)
        _assert_basic_tables(func.tables())

    def test_columns_full_sets_privileges_and_comment(self, sync_env):
        backend, func = sync_env
        backend.execute.return_value = _result(FULL_COLUMN_ROWS)
        _assert_full_columns(func.columns("users", full=True))

    def test_columns_like_binds_pattern(self, sync_env):
        backend, func = sync_env
        backend.execute.return_value = _result(COLUMN_ROWS)
        func.columns("users", schema="testdb", full=True, like="id%")
        sql, params = backend.execute.call_args[0]
        assert "FULL" in sql and "LIKE" in sql and "testdb" in sql
        assert params == ("id%",)

    def test_tables_full_and_like(self, sync_env):
        backend, func = sync_env
        backend.execute.return_value = _result(TABLE_ROWS_FULL)
        func.tables(schema="testdb", full=True, like="u%")
        sql, params = backend.execute.call_args[0]
        assert "SHOW FULL TABLES" in sql and "LIKE" in sql
        assert params == ("u%",)

    @pytest.mark.parametrize(
        "method,keyword",
        [("variables", "VARIABLES"), ("status", "STATUS")],
    )
    def test_session_false_emits_global(self, sync_env, method, keyword):
        backend, func = sync_env
        backend.execute.return_value = _result(
            VARIABLE_ROWS if method == "variables" else STATUS_ROWS
        )
        getattr(func, method)(session=False)
        sql = backend.execute.call_args[0][0]
        assert "GLOBAL" in sql and keyword in sql

    def test_processlist_full(self, sync_env):
        backend, func = sync_env
        backend.execute.return_value = _result(PROCESSLIST_ROWS)
        _assert_processlist(func.processlist(full=True))
        assert "FULL" in backend.execute.call_args[0][0]

    @pytest.mark.parametrize("method", ["warnings", "errors"])
    def test_warnings_errors_limit_is_inlined(self, sync_env, method):
        backend, func = sync_env
        backend.execute.return_value = _result(WARNING_ROWS)
        getattr(func, method)(limit=5)
        sql, params = backend.execute.call_args[0]
        assert "LIMIT 5" in sql
        assert params == ()

    def test_grants_for_user_and_host(self, sync_env):
        backend, func = sync_env
        backend.execute.return_value = _result(GRANT_ROWS)
        _assert_grants(func.grants(user="root", host="localhost"))
        sql, params = backend.execute.call_args[0]
        assert "SHOW GRANTS FOR" in sql
        assert params == ("root", "localhost")

    def test_like_patterns_bind_param(self, sync_env):
        backend, func = sync_env
        backend.execute.return_value = _result(DATABASE_ROWS)
        func.databases(like="test%")
        sql, params = backend.execute.call_args[0]
        assert "LIKE" in sql
        assert params == ("test%",)


# --------------------------------------------------------------------------- #
# Async class (native async driver)
# --------------------------------------------------------------------------- #


class TestAsyncMySQLShowFunctionalityOffline:
    """Offline coverage of the native-async SHOW facade."""

    @pytest.mark.parametrize(
        "version,supports_invisible",
        [(None, True), ((5, 7, 0), False), ((8, 0, 0), True)],
    )
    def test_init_version_flags(self, version, supports_invisible):
        backend = MagicMock()
        backend.dialect = MySQLDialect(version=(8, 0, 0))
        backend.execute = AsyncMock()
        func = AsyncMySQLShowFunctionality(backend, version=version)
        assert func._version == version
        assert func.dialect is backend.dialect
        # The async facade delegates parsing (and the version flag) to the
        # shared sync implementation rather than duplicating it.
        assert func._sync_impl._supports_invisible_columns is supports_invisible

    @pytest.mark.parametrize("method,args,rows,assert_rows", METHOD_CASES)
    async def test_maps_rows_into_dataclasses(self, async_env, method, args, rows, assert_rows):
        backend, func = async_env
        backend.execute.return_value = _result(rows)
        result = await getattr(func, method)(*args)
        assert_rows(result)
        backend.execute.assert_awaited_once()
        sql, params = backend.execute.call_args[0]
        assert isinstance(sql, str) and sql.startswith("SHOW")
        assert isinstance(params, tuple)

    @pytest.mark.parametrize("method,args,rows,assert_rows", METHOD_CASES)
    async def test_empty_rows(self, async_env, method, args, rows, assert_rows):
        backend, func = async_env
        backend.execute.return_value = _result([])
        result = await getattr(func, method)(*args)
        if method in SINGLETON_METHODS:
            assert result is None
        else:
            assert result == []

    async def test_single_column_tables_row(self, async_env):
        backend, func = async_env
        backend.execute.return_value = _result(TABLE_ROWS_BASIC)
        _assert_basic_tables(await func.tables())

    async def test_columns_full_sets_privileges_and_comment(self, async_env):
        backend, func = async_env
        backend.execute.return_value = _result(FULL_COLUMN_ROWS)
        _assert_full_columns(await func.columns("users", full=True))

    async def test_columns_like_binds_pattern(self, async_env):
        backend, func = async_env
        backend.execute.return_value = _result(COLUMN_ROWS)
        await func.columns("users", schema="testdb", full=True, like="id%")
        sql, params = async_env[0].execute.call_args[0]
        assert "FULL" in sql and "LIKE" in sql and "testdb" in sql
        assert params == ("id%",)

    async def test_tables_full_and_like(self, async_env):
        backend, func = async_env
        backend.execute.return_value = _result(TABLE_ROWS_FULL)
        await func.tables(schema="testdb", full=True, like="u%")
        sql, params = backend.execute.call_args[0]
        assert "SHOW FULL TABLES" in sql and "LIKE" in sql
        assert params == ("u%",)

    @pytest.mark.parametrize(
        "method,keyword",
        [("variables", "VARIABLES"), ("status", "STATUS")],
    )
    async def test_session_false_emits_global(self, async_env, method, keyword):
        backend, func = async_env
        backend.execute.return_value = _result(
            VARIABLE_ROWS if method == "variables" else STATUS_ROWS
        )
        await getattr(func, method)(session=False)
        sql = backend.execute.call_args[0][0]
        assert "GLOBAL" in sql and keyword in sql

    async def test_processlist_full(self, async_env):
        backend, func = async_env
        backend.execute.return_value = _result(PROCESSLIST_ROWS)
        _assert_processlist(await func.processlist(full=True))
        assert "FULL" in backend.execute.call_args[0][0]

    @pytest.mark.parametrize("method", ["warnings", "errors"])
    async def test_warnings_errors_limit_is_inlined(self, async_env, method):
        backend, func = async_env
        backend.execute.return_value = _result(WARNING_ROWS)
        await getattr(func, method)(limit=5)
        sql, params = backend.execute.call_args[0]
        assert "LIMIT 5" in sql
        assert params == ()

    async def test_grants_for_user_and_host(self, async_env):
        backend, func = async_env
        backend.execute.return_value = _result(GRANT_ROWS)
        _assert_grants(await func.grants(user="root", host="localhost"))
        sql, params = backend.execute.call_args[0]
        assert "SHOW GRANTS FOR" in sql
        assert params == ("root", "localhost")

    async def test_like_patterns_bind_param(self, async_env):
        backend, func = async_env
        backend.execute.return_value = _result(DATABASE_ROWS)
        await func.databases(like="test%")
        sql, params = backend.execute.call_args[0]
        assert "LIKE" in sql
        assert params == ("test%",)
