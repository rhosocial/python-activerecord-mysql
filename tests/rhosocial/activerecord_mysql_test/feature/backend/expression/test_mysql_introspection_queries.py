# tests/rhosocial/activerecord_mysql_test/feature/backend/expression/test_mysql_introspection_queries.py
"""The introspection SELECTs, rendered from their nodes.

These are render-only assertions (org rules §12): a dialect is constructed, a
node is built, and the SQL is read back. No connection is opened.

What is pinned here is the part of each query that a caller depends on and
that a rewrite can silently change: the **projection order** (the parsers below
read columns positionally in places), the **parameter order** (schema before
name, so ``(schema, table_name)``), and whether a filter is bound or inline.
The identifier quoting, on the other hand, is deliberately not pinned
character for character -- it is the dialect's to choose, and these tests say
only what the query *asks*.
"""

import pytest

from rhosocial.activerecord.backend.expression.introspection import (
    ColumnInfoQueryStatement,
    DatabaseInfoQueryStatement,
    ForeignKeyQueryStatement,
    IndexInfoQueryStatement,
    TableListQueryStatement,
    TriggerListQueryStatement,
    ViewInfoQueryStatement,
    ViewListQueryStatement,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


@pytest.fixture
def dialect():
    return MySQLDialect(version=(8, 0, 0))


class TestDatabaseInfo:
    def test_projection_and_bound_schema(self, dialect):
        sql, params = DatabaseInfoQueryStatement(dialect, schema="app").to_sql()
        assert sql == (
            "SELECT `DEFAULT_CHARACTER_SET_NAME`, `DEFAULT_COLLATION_NAME` "
            "FROM `information_schema`.`SCHEMATA` WHERE `SCHEMA_NAME` = %s"
        )
        assert params == ("app",)

    def test_a_missing_schema_is_bound_as_null(self, dialect):
        _, params = DatabaseInfoQueryStatement(dialect).to_sql()
        assert params == (None,)


class TestTableList:
    """The relation is ``information_schema.TABLES`` with the filters as nodes."""

    def test_default_excludes_the_engine_s_own_schemas(self, dialect):
        sql, params = TableListQueryStatement(dialect, schema="app").to_sql()
        assert sql.startswith(
            "SELECT `TABLE_NAME`, `TABLE_TYPE`, `TABLE_COMMENT`, `TABLE_ROWS`, "
            "`DATA_LENGTH`, `AUTO_INCREMENT`, `CREATE_TIME`, `UPDATE_TIME` "
            "FROM `information_schema`.`TABLES` WHERE `TABLE_SCHEMA` = %s"
        )
        # The exclusion list is a fact about the engine, not caller data, so it
        # is inline and the parameter tuple stays at one entry.
        assert "'information_schema', 'performance_schema', 'mysql', 'sys'" in sql
        assert params == ("app",)

    def test_include_system_drops_the_exclusion(self, dialect):
        sql, params = TableListQueryStatement(dialect, schema="app", include_system=True).to_sql()
        assert "NOT" not in sql
        assert params == ("app",)

    def test_without_views_is_an_inline_type_filter(self, dialect):
        sql, params = TableListQueryStatement(dialect, schema="app", include_views=False).to_sql()
        assert "`TABLE_TYPE` = 'BASE TABLE'" in sql
        assert params == ("app",)

    def test_explicit_table_type_is_bound_last(self, dialect):
        sql, params = TableListQueryStatement(dialect, schema="app", table_type="VIEW").to_sql()
        assert sql.endswith("`TABLE_TYPE` = %s")
        assert params == ("app", "VIEW")


class TestColumnAndIndexInfo:
    def test_columns_projection_order_and_ordering(self, dialect):
        sql, params = ColumnInfoQueryStatement(dialect, "users", schema="app").to_sql()
        assert sql == (
            "SELECT `COLUMN_NAME`, `ORDINAL_POSITION`, `COLUMN_DEFAULT`, `IS_NULLABLE`, "
            "`DATA_TYPE`, `CHARACTER_MAXIMUM_LENGTH`, `NUMERIC_PRECISION`, `NUMERIC_SCALE`, "
            "`COLUMN_TYPE`, `COLUMN_KEY`, `EXTRA`, `COLUMN_COMMENT`, "
            "`CHARACTER_SET_NAME`, `COLLATION_NAME` "
            "FROM `information_schema`.`COLUMNS` "
            "WHERE `TABLE_SCHEMA` = %s AND `TABLE_NAME` = %s "
            "ORDER BY `ORDINAL_POSITION`"
        )
        assert params == ("app", "users")

    def test_indexes_projection_and_ordering(self, dialect):
        sql, params = IndexInfoQueryStatement(dialect, "users", schema="app").to_sql()
        assert sql == (
            "SELECT `INDEX_NAME`, `NON_UNIQUE`, `SEQ_IN_INDEX`, `COLUMN_NAME`, "
            "`INDEX_TYPE`, `SUB_PART`, `NULLABLE` "
            "FROM `information_schema`.`STATISTICS` "
            "WHERE `TABLE_SCHEMA` = %s AND `TABLE_NAME` = %s "
            "ORDER BY `INDEX_NAME`, `SEQ_IN_INDEX`"
        )
        assert params == ("app", "users")


class TestForeignKey:
    """Two relations joined, filtered to rows that actually reference a table."""

    def test_join_projection_and_predicates(self, dialect):
        sql, params = ForeignKeyQueryStatement(dialect, "orders", schema="app").to_sql()
        assert sql == (
            "SELECT `kcu`.`CONSTRAINT_NAME`, `kcu`.`COLUMN_NAME`, `kcu`.`ORDINAL_POSITION`, "
            "`kcu`.`REFERENCED_TABLE_NAME`, `kcu`.`REFERENCED_COLUMN_NAME`, "
            "`rc`.`UPDATE_RULE`, `rc`.`DELETE_RULE` "
            "FROM `information_schema`.`KEY_COLUMN_USAGE` AS `kcu` "
            "JOIN `information_schema`.`REFERENTIAL_CONSTRAINTS` AS `rc` "
            "ON `kcu`.`CONSTRAINT_NAME` = `rc`.`CONSTRAINT_NAME` "
            "AND `kcu`.`CONSTRAINT_SCHEMA` = `rc`.`CONSTRAINT_SCHEMA` "
            "WHERE `kcu`.`TABLE_SCHEMA` = %s AND `kcu`.`TABLE_NAME` = %s "
            "AND `kcu`.`REFERENCED_TABLE_NAME` IS NOT NULL "
            "ORDER BY `kcu`.`CONSTRAINT_NAME`, `kcu`.`ORDINAL_POSITION`"
        )
        assert params == ("app", "orders")


class TestViews:
    def test_view_list_has_the_system_exclusion_and_ordering(self, dialect):
        sql, params = ViewListQueryStatement(dialect, schema="app").to_sql()
        assert sql.startswith(
            "SELECT `TABLE_NAME`, `VIEW_DEFINITION`, `CHECK_OPTION`, `IS_UPDATABLE` "
            "FROM `information_schema`.`VIEWS` WHERE `TABLE_SCHEMA` = %s"
        )
        assert "'information_schema', 'performance_schema', 'mysql', 'sys'" in sql
        assert sql.endswith("ORDER BY `TABLE_NAME`")
        assert params == ("app",)

    def test_view_list_with_system_objects(self, dialect):
        sql, params = ViewListQueryStatement(dialect, schema="app", include_system=True).to_sql()
        assert "NOT" not in sql
        assert params == ("app",)

    def test_view_info_names_one_view(self, dialect):
        sql, params = ViewInfoQueryStatement(dialect, "v_users", schema="app").to_sql()
        assert sql == (
            "SELECT `TABLE_NAME`, `VIEW_DEFINITION`, `CHECK_OPTION`, `IS_UPDATABLE` "
            "FROM `information_schema`.`VIEWS` "
            "WHERE `TABLE_SCHEMA` = %s AND `TABLE_NAME` = %s"
        )
        assert params == ("app", "v_users")


class TestTriggers:
    def test_list_all(self, dialect):
        sql, params = TriggerListQueryStatement(dialect, schema="app").to_sql()
        assert sql == (
            "SELECT `TRIGGER_NAME`, `EVENT_MANIPULATION`, `EVENT_OBJECT_TABLE`, "
            "`ACTION_TIMING`, `ACTION_STATEMENT`, `CREATED` "
            "FROM `information_schema`.`TRIGGERS` "
            "WHERE `TRIGGER_SCHEMA` = %s ORDER BY `TRIGGER_NAME`"
        )
        assert params == ("app",)

    def test_list_for_one_table_binds_the_name_last(self, dialect):
        sql, params = TriggerListQueryStatement(dialect, schema="app", table_name="users").to_sql()
        assert sql.endswith("`EVENT_OBJECT_TABLE` = %s ORDER BY `TRIGGER_NAME`")
        assert params == ("app", "users")


class TestNoStatementTextSurvives:
    """The formatters build nodes; they do not assemble text.

    The concatenated forms this replaced were ``sql = "SELECT ..."`` plus
    ``+=``; if one comes back, this fails rather than waiting for a reviewer to
    notice a quoted keyword in a formatter.
    """

    def test_formatters_hold_no_sql_text(self):
        import inspect

        from rhosocial.activerecord.backend.impl.mysql.mixins import introspection

        source = inspect.getsource(introspection.MySQLIntrospectionMixin)
        for keyword in ('"SELECT ', '"FROM ', '"WHERE ', '"ORDER BY ', "sql += "):
            assert keyword not in source, f"{keyword!r} is statement text, not a node"
