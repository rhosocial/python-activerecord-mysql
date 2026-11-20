# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/introspection/
# test_show_introspector_offline.py
"""
Pure-mock offline unit tests for the MySQL SHOW sub-introspectors.

No socket, no driver, no database is touched. Every I/O seam is replaced:

* the executor's ``execute`` method is a MagicMock (sync) or AsyncMock (async);
* a real :class:`MySQLDialect` is used only to build the SHOW statements, so
  ``expr.to_sql()`` produces genuine SQL without any connection;
* the ``parse_*`` static helpers are also called directly with representative
  rows to cover their fallbacks and empty/malformed branches.

Both :class:`ShowIntrospector` and :class:`AsyncShowIntrospector` are covered
symmetrically because MySQL ships a native async driver.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.introspection.show_introspector import (
    AsyncShowIntrospector,
    ShowIntrospector,
    ShowMixin,
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
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def dialect():
    """A real dialect is enough to render SHOW expressions; no connection needed."""
    return MySQLDialect(version=(8, 0, 36))


@pytest.fixture
def sync_env(dialect):
    backend = MagicMock()
    backend.dialect = dialect
    executor = MagicMock()
    introspector = ShowIntrospector(backend, executor)
    return SimpleNamespace(backend=backend, executor=executor, introspector=introspector)


@pytest.fixture
def async_env(dialect):
    backend = MagicMock()
    backend.dialect = dialect
    executor = MagicMock()
    executor.execute = AsyncMock()
    introspector = AsyncShowIntrospector(backend, executor)
    return SimpleNamespace(backend=backend, executor=executor, introspector=introspector)


# --------------------------------------------------------------------------- #
# Shared table of public-method cases: (id, method, kwargs, rows, expected)
# --------------------------------------------------------------------------- #

PUBLIC_CASES = [
    (
        "create_table",
        "create_table",
        {"table_name": "users"},
        [{"Table": "users", "Create Table": "CREATE TABLE users (id INT)"}],
        ShowCreateTableResult(table_name="users", create_statement="CREATE TABLE users (id INT)"),
    ),
    ("create_table_empty", "create_table", {"table_name": "users"}, [], None),
    (
        "create_table_info_schema_keys",
        "create_table",
        {"table_name": "users"},
        [{"TABLE": "users", "CREATE TABLE": "INFO_SCHEMA_DDL"}],
        ShowCreateTableResult(table_name="users", create_statement="INFO_SCHEMA_DDL"),
    ),
    (
        "create_view",
        "create_view",
        {"view_name": "v_active"},
        [
            {
                "View": "v_active",
                "Create View": "CREATE VIEW v_active AS SELECT 1",
                "character_set_client": "utf8mb4",
                "collation_connection": "utf8mb4_general_ci",
            }
        ],
        ShowCreateViewResult(
            view_name="v_active",
            create_statement="CREATE VIEW v_active AS SELECT 1",
            character_set_client="utf8mb4",
            collation_connection="utf8mb4_general_ci",
        ),
    ),
    ("create_view_empty", "create_view", {"view_name": "v"}, [], None),
    (
        "columns_basic",
        "columns",
        {"table_name": "users"},
        [{"Field": "id", "Type": "int", "Null": "NO", "Key": "PRI", "Default": None, "Extra": "auto_increment"}],
        [ShowColumnResult(field="id", type="int", null="NO", key="PRI", default=None, extra="auto_increment")],
    ),
    (
        "columns_full",
        "columns",
        {"table_name": "users", "full": True},
        [
            {
                "COLUMN_NAME": "name",
                "COLUMN_TYPE": "varchar(64)",
                "IS_NULLABLE": "YES",
                "COLUMN_KEY": "",
                "COLUMN_DEFAULT": "anon",
                "EXTRA": "",
                "Privileges": "select,insert",
                "Comment": "display name",
            }
        ],
        [
            ShowColumnResult(
                field="name",
                type="varchar(64)",
                null="YES",
                key="",
                default="anon",
                extra="",
                privileges="select,insert",
                comment="display name",
            )
        ],
    ),
    ("columns_empty", "columns", {"table_name": "users"}, [], []),
    (
        "indexes_basic",
        "indexes",
        {"table_name": "users"},
        [
            {
                "Table": "users",
                "Non_unique": 0,
                "Key_name": "PRIMARY",
                "Seq_in_index": 1,
                "Column_name": "id",
                "Collation": "A",
                "Cardinality": 7,
                "Sub_part": None,
                "Packed": None,
                "Null": "",
                "Index_type": "BTREE",
                "Comment": "",
                "Index_comment": "",
                "Visible": "YES",
                "Expression": None,
            }
        ],
        [
            ShowIndexResult(
                table="users",
                non_unique=0,
                key_name="PRIMARY",
                seq_in_index=1,
                column_name="id",
                collation="A",
                cardinality=7,
                sub_part=None,
                packed=None,
                null="",
                index_type="BTREE",
                comment="",
                index_comment="",
                visible="YES",
                expression=None,
            )
        ],
    ),
    (
        "indexes_default_type",
        "indexes",
        {"table_name": "users"},
        [{"Table": "users", "Non_unique": 1, "Key_name": "idx_name", "Seq_in_index": 1, "Column_name": "name"}],
        [ShowIndexResult(table="users", non_unique=1, key_name="idx_name", seq_in_index=1, column_name="name")],
    ),
    ("indexes_empty", "indexes", {"table_name": "users"}, [], []),
    (
        "tables_single_column",
        "tables",
        {},
        [{"Tables_in_testdb": "users"}, {"Tables_in_testdb": "orders"}],
        [ShowTableResult(name="users"), ShowTableResult(name="orders")],
    ),
    (
        "tables_full",
        "tables",
        {"full": True},
        [
            {"Tables_in_testdb": "users", "Table_type": "BASE TABLE"},
            {"Tables_in_testdb": "v_active", "Table_type": "VIEW"},
        ],
        [
            ShowTableResult(name="users", table_type="BASE TABLE"),
            ShowTableResult(name="v_active", table_type="VIEW"),
        ],
    ),
    ("tables_no_prefixed_key", "tables", {}, [{"foo": "bar", "baz": "qux"}], []),
    ("tables_empty", "tables", {}, [], []),
    (
        "databases",
        "databases",
        {},
        [{"Database": "db1"}, {"Database": "db2"}],
        [ShowDatabaseResult(name="db1"), ShowDatabaseResult(name="db2")],
    ),
    (
        "table_status",
        "table_status",
        {},
        [
            {
                "Name": "users",
                "Engine": "InnoDB",
                "Version": 10,
                "Row_format": "Dynamic",
                "Rows": 100,
                "Avg_row_length": 50,
                "Data_length": 5000,
                "Max_data_length": 0,
                "Index_length": 2048,
                "Data_free": 0,
                "Auto_increment": 101,
                "Create_time": "2024-01-01 00:00:00",
                "Update_time": "2024-06-01 12:00:00",
                "Check_time": None,
                "Collation": "utf8mb4_general_ci",
                "Checksum": None,
                "Create_options": "",
                "Comment": "user table",
            }
        ],
        [
            ShowTableStatusResult(
                name="users",
                engine="InnoDB",
                version=10,
                row_format="Dynamic",
                rows=100,
                avg_row_length=50,
                data_length=5000,
                max_data_length=0,
                index_length=2048,
                data_free=0,
                auto_increment=101,
                create_time="2024-01-01 00:00:00",
                update_time="2024-06-01 12:00:00",
                check_time=None,
                collation="utf8mb4_general_ci",
                checksum=None,
                create_options="",
                comment="user table",
            )
        ],
    ),
    (
        "table_status_falsy_times",
        "table_status",
        {},
        [{"Name": "t", "Create_time": None, "Update_time": "", "Check_time": None}],
        [ShowTableStatusResult(name="t", create_time=None, update_time=None, check_time=None)],
    ),
    (
        "triggers",
        "triggers",
        {},
        [
            {
                "Trigger": "bi_users",
                "Event": "INSERT",
                "Table": "users",
                "Statement": "SET NEW.created = NOW()",
                "Timing": "BEFORE",
                "Created": "2024-01-01",
                "sql_mode": "STRICT_TRANS_TABLES",
                "Definer": "root@localhost",
                "character_set_client": "utf8mb4",
                "collation_connection": "utf8mb4_general_ci",
                "Database Collation": "utf8mb4_general_ci",
            }
        ],
        [
            ShowTriggerResult(
                trigger="bi_users",
                event="INSERT",
                table="users",
                statement="SET NEW.created = NOW()",
                timing="BEFORE",
                created="2024-01-01",
                sql_mode="STRICT_TRANS_TABLES",
                definer="root@localhost",
                character_set_client="utf8mb4",
                collation_connection="utf8mb4_general_ci",
                database_collation="utf8mb4_general_ci",
            )
        ],
    ),
    (
        "triggers_info_schema_keys",
        "triggers",
        {},
        [
            {
                "TRIGGER_NAME": "trg",
                "EVENT_MANIPULATION": "UPDATE",
                "EVENT_OBJECT_TABLE": "t",
                "ACTION_STATEMENT": "BEGIN END",
                "ACTION_TIMING": "AFTER",
            }
        ],
        [ShowTriggerResult(trigger="trg", event="UPDATE", table="t", statement="BEGIN END", timing="AFTER")],
    ),
    (
        "create_trigger",
        "create_trigger",
        {"trigger_name": "trg"},
        [
            {
                "Trigger": "trg",
                "SQL Original Statement": "CREATE TRIGGER trg ...",
                "character_set_client": "utf8mb4",
                "collation_connection": "utf8mb4_general_ci",
                "Database Collation": "utf8mb4_general_ci",
            }
        ],
        ShowCreateTriggerResult(
            trigger_name="trg",
            create_statement="CREATE TRIGGER trg ...",
            character_set_client="utf8mb4",
            collation_connection="utf8mb4_general_ci",
            database_collation="utf8mb4_general_ci",
        ),
    ),
    ("create_trigger_empty", "create_trigger", {"trigger_name": "trg"}, [], None),
    (
        "variables",
        "variables",
        {},
        [{"Variable_name": "port", "Value": "3306"}],
        [ShowVariableResult(variable_name="port", value="3306")],
    ),
    (
        "status",
        "status",
        {},
        [{"Variable_name": "Queries", "Value": "42"}],
        [ShowStatusResult(variable_name="Queries", value="42")],
    ),
    (
        "processlist",
        "processlist",
        {},
        [
            {
                "Id": 1,
                "User": "root",
                "Host": "localhost",
                "Command": "Query",
                "Time": 0,
                "db": "testdb",
                "State": "executing",
                "Info": "SELECT 1",
            }
        ],
        [
            ShowProcessListResult(
                id=1,
                user="root",
                host="localhost",
                command="Query",
                time=0,
                db="testdb",
                state="executing",
                info="SELECT 1",
            )
        ],
    ),
    (
        "processlist_uppercase_id",
        "processlist",
        {},
        [{"ID": 2, "User": "app", "Host": "%", "Command": "Sleep", "Time": 5}],
        [ShowProcessListResult(id=2, user="app", host="%", command="Sleep", time=5)],
    ),
    (
        "warnings",
        "warnings",
        {},
        [{"Level": "Warning", "Code": 1234, "Message": "deprecated"}],
        [ShowWarningResult(level="Warning", code=1234, message="deprecated")],
    ),
    (
        "errors",
        "errors",
        {},
        [{"Level": "Error", "Code": 1064, "Message": "syntax"}],
        [ShowWarningResult(level="Error", code=1064, message="syntax")],
    ),
    (
        "engines",
        "engines",
        {},
        [{"Engine": "InnoDB", "Support": "DEFAULT", "Transactions": "YES", "XA": "YES", "Savepoints": "YES"}],
        [ShowEngineResult(engine="InnoDB", support="DEFAULT", transactions="YES", xa="YES", savepoints="YES")],
    ),
    (
        "charset",
        "charset",
        {},
        [
            {
                "Charset": "utf8mb4",
                "Description": "UTF-8 Unicode",
                "Default collation": "utf8mb4_general_ci",
                "Maxlen": 4,
            }
        ],
        [
            ShowCharsetResult(
                charset="utf8mb4",
                description="UTF-8 Unicode",
                default_collation="utf8mb4_general_ci",
                maxlen=4,
            )
        ],
    ),
    (
        "collation",
        "collation",
        {},
        [
            {
                "Collation": "utf8mb4_general_ci",
                "Charset": "utf8mb4",
                "Id": 45,
                "Default": "Yes",
                "Compiled": "Yes",
                "Sortlen": 1,
            }
        ],
        [
            ShowCollationResult(
                collation="utf8mb4_general_ci",
                charset="utf8mb4",
                id=45,
                default="Yes",
                compiled="Yes",
                sortlen=1,
            )
        ],
    ),
    (
        "grants",
        "grants",
        {},
        [{"Grants for": "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost'"}],
        [ShowGrantResult(grants="GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost'")],
    ),
    (
        "plugins",
        "plugins",
        {},
        [{"Name": "InnoDB", "Status": "ACTIVE", "Type": "STORAGE ENGINE", "Library": None, "License": "GPL"}],
        [ShowPluginResult(name="InnoDB", status="ACTIVE", type="STORAGE ENGINE", library=None, license="GPL")],
    ),
]

_CASE_IDS = [case[0] for case in PUBLIC_CASES]
_CASE_PARAMS = ("case_id", "method", "kwargs", "rows", "expected")


# --------------------------------------------------------------------------- #
# Direct parse_* helper tests (pure, no executor involved)
# --------------------------------------------------------------------------- #


class TestShowMixinParsers:
    """Call the pure parse helpers directly with representative row shapes."""

    def test_dialect_property_reads_backend(self, sync_env):
        assert sync_env.introspector.dialect is sync_env.backend.dialect

    def test_parse_create_table_returns_dataclass_and_none(self):
        parsed = ShowMixin.parse_create_table(
            [{"Table": "users", "Create Table": "DDL"}], "fallback"
        )
        assert isinstance(parsed, ShowCreateTableResult)
        assert parsed.table_name == "users"
        assert parsed.create_statement == "DDL"
        assert ShowMixin.parse_create_table([], "fallback") is None

    def test_parse_create_table_uses_fallback_name(self):
        parsed = ShowMixin.parse_create_table([{}], "fallback")
        assert parsed.table_name == "fallback"
        assert parsed.create_statement == ""

    def test_parse_create_view_optional_metadata(self):
        parsed = ShowMixin.parse_create_view([{"View": "v", "Create View": "DDL"}], "fallback")
        assert isinstance(parsed, ShowCreateViewResult)
        assert parsed.view_name == "v"
        assert parsed.character_set_client is None
        assert parsed.collation_connection is None
        assert ShowMixin.parse_create_view([], "fallback") is None

    def test_parse_columns_sets_full_fields_only_when_present(self):
        basic = ShowMixin.parse_columns([{"Field": "id", "Type": "int", "Null": "NO", "Key": "PRI"}])[0]
        assert isinstance(basic, ShowColumnResult)
        assert basic.privileges is None
        assert basic.comment is None

        full = ShowMixin.parse_columns([{"Collation": "utf8mb4_bin", "Privileges": "select", "Comment": "c"}])[0]
        assert full.privileges == "select"
        assert full.comment == "c"

        collation_only = ShowMixin.parse_columns([{"Collation": "utf8mb4_bin"}])[0]
        assert collation_only.privileges is None

    def test_parse_indexes_default_index_type(self):
        parsed = ShowMixin.parse_indexes([{"Table": "t", "Non_unique": 1, "Key_name": "k", "Seq_in_index": 1}])[0]
        assert isinstance(parsed, ShowIndexResult)
        assert parsed.index_type == "BTREE"
        assert ShowMixin.parse_indexes([]) == []

    def test_parse_tables_single_value_and_prefixed(self):
        single = ShowMixin.parse_tables([{"anything": "users"}])
        assert single == [ShowTableResult(name="users", table_type=None)]

        full = ShowMixin.parse_tables([{"Tables_in_db": "users", "Table_type": "BASE TABLE"}])
        assert full == [ShowTableResult(name="users", table_type="BASE TABLE")]

        assert ShowMixin.parse_tables([]) == []

    def test_parse_table_status_stringifies_truthy_times(self):
        from datetime import datetime

        stamp = datetime(2024, 1, 2, 3, 4, 5)
        parsed = ShowMixin.parse_table_status([{"Name": "t", "Create_time": stamp}])[0]
        assert isinstance(parsed, ShowTableStatusResult)
        assert parsed.create_time == "2024-01-02 03:04:05"
        assert parsed.update_time is None

    def test_parse_create_trigger_fallbacks(self):
        parsed = ShowMixin.parse_create_trigger([{}], "fallback")
        assert isinstance(parsed, ShowCreateTriggerResult)
        assert parsed.trigger_name == "fallback"
        assert parsed.create_statement == ""
        assert ShowMixin.parse_create_trigger([], "fallback") is None

    def test_parse_variables_status_processlist_warnings(self):
        assert ShowMixin.parse_variables([{"Variable_name": "v", "Value": "1"}]) == [
            ShowVariableResult(variable_name="v", value="1")
        ]
        assert ShowMixin.parse_status([{"Variable_name": "s", "Value": "2"}]) == [
            ShowStatusResult(variable_name="s", value="2")
        ]
        assert ShowMixin.parse_processlist([{"ID": 9, "User": "u", "Host": "h", "Command": "Sleep", "Time": 1}]) == [
            ShowProcessListResult(id=9, user="u", host="h", command="Sleep", time=1)
        ]
        assert ShowMixin.parse_warnings([{"Level": "Note", "Code": 1, "Message": "m"}]) == [
            ShowWarningResult(level="Note", code=1, message="m")
        ]

    def test_parse_remaining_helpers_with_empty_rows(self):
        assert ShowMixin.parse_databases([]) == []
        assert ShowMixin.parse_triggers([]) == []
        assert ShowMixin.parse_engines([]) == []
        assert ShowMixin.parse_charset([]) == []
        assert ShowMixin.parse_collation([]) == []
        assert ShowMixin.parse_grants([]) == []
        assert ShowMixin.parse_plugins([]) == []


# --------------------------------------------------------------------------- #
# Synchronous public API
# --------------------------------------------------------------------------- #


class TestShowIntrospectorSync:
    """All sync public methods map controlled executor rows onto result types."""

    @pytest.mark.parametrize(_CASE_PARAMS, PUBLIC_CASES, ids=_CASE_IDS)
    def test_public_method_maps_rows(self, sync_env, case_id, method, kwargs, rows, expected):
        sync_env.executor.execute.return_value = rows
        result = getattr(sync_env.introspector, method)(**kwargs)
        assert result == expected
        sync_env.executor.execute.assert_called_once()

    def test_generates_real_show_sql(self, sync_env):
        sync_env.executor.execute.return_value = []
        sync_env.introspector.columns("users", schema="db", full=True, like="id%")
        sql, params = sync_env.executor.execute.call_args.args
        assert "SHOW" in sql.upper()
        assert "COLUMNS" in sql.upper()
        assert "FULL" in sql.upper()
        assert "id%" in params

    def test_executor_seam_is_used(self, sync_env):
        sync_env.executor.execute.return_value = []
        sync_env.introspector.databases(like="d%")
        assert sync_env.backend.dialect is not None
        assert sync_env.executor.execute.call_count == 1


# --------------------------------------------------------------------------- #
# Asynchronous public API (native async driver)
# --------------------------------------------------------------------------- #


class TestAsyncShowIntrospector:
    """All async public methods mirror the sync coverage with an AsyncMock seam."""

    @pytest.mark.parametrize(_CASE_PARAMS, PUBLIC_CASES, ids=_CASE_IDS)
    async def test_public_method_maps_rows(self, async_env, case_id, method, kwargs, rows, expected):
        async_env.executor.execute.return_value = rows
        result = await getattr(async_env.introspector, method)(**kwargs)
        assert result == expected
        async_env.executor.execute.assert_awaited_once()

    async def test_generates_real_show_sql(self, async_env):
        async_env.executor.execute.return_value = []
        await async_env.introspector.create_table("users", schema="db")
        sql, params = async_env.executor.execute.await_args.args
        assert "SHOW CREATE TABLE" in sql.upper()
        assert params == () or isinstance(params, tuple)

    async def test_executor_seam_is_used(self, async_env):
        async_env.executor.execute.return_value = []
        await async_env.introspector.plugins()
        assert async_env.backend.dialect is not None
        assert async_env.executor.execute.await_count == 1
