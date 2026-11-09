# tests/rhosocial/activerecord_mysql_test/feature/backend/expression/test_mysql_routine_constraint_queries.py
"""The routine and constraint introspection SELECTs, rendered from their nodes.

Render-only assertions: a dialect is constructed, a node is built, and the SQL
is read back. What is pinned is the projection order the parser reads, the
parameter order (schema before name, so ``(schema, name)``), and the joins that
make one question answer both the routine's own facts and its arguments -- or
both a constraint's table and its optional side relations.
"""

import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.introspection import (
    MySQLConstraintListQueryStatement,
    MySQLRoutineInfoQueryStatement,
    MySQLRoutineListQueryStatement,
)


@pytest.fixture
def dialect():
    return MySQLDialect(version=(8, 0, 46))


ROUTINE_PROJECTION = (
    "`r`.`ROUTINE_SCHEMA`, `r`.`ROUTINE_NAME`, `r`.`ROUTINE_TYPE`, "
    "`r`.`DATA_TYPE`, `r`.`DTD_IDENTIFIER`, `r`.`ROUTINE_BODY`, "
    "`r`.`EXTERNAL_LANGUAGE`, `r`.`IS_DETERMINISTIC`, `r`.`SQL_DATA_ACCESS`, "
    "`r`.`SECURITY_TYPE`, `r`.`ROUTINE_COMMENT`, `r`.`DEFINER`, `r`.`CREATED`, "
    "`r`.`LAST_ALTERED`, `r`.`SQL_MODE`, "
    "`p`.`ORDINAL_POSITION` AS `PARAM_ORDINAL_POSITION`, `p`.`PARAMETER_MODE`, "
    "`p`.`PARAMETER_NAME`, `p`.`DATA_TYPE` AS `PARAM_DATA_TYPE`, "
    "`p`.`DTD_IDENTIFIER` AS `PARAM_DTD_IDENTIFIER`"
)

ROUTINE_FROM = (
    "FROM `information_schema`.`ROUTINES` AS `r` "
    "LEFT JOIN `information_schema`.`PARAMETERS` AS `p` "
    "ON `r`.`ROUTINE_SCHEMA` = `p`.`SPECIFIC_SCHEMA` "
    "AND `r`.`ROUTINE_NAME` = `p`.`SPECIFIC_NAME` "
    "AND `r`.`ROUTINE_TYPE` = `p`.`ROUTINE_TYPE`"
)

ROUTINE_ORDER = "ORDER BY `r`.`ROUTINE_NAME`, `r`.`ROUTINE_TYPE`, `p`.`ORDINAL_POSITION`"


class TestRoutineQueries:
    def test_list_binds_the_schema_and_orders_return_before_arguments(self, dialect):
        sql, params = MySQLRoutineListQueryStatement(dialect, schema="app").to_sql()

        assert sql == (
            f"SELECT {ROUTINE_PROJECTION} {ROUTINE_FROM} "
            "WHERE `r`.`ROUTINE_SCHEMA` = %s "
            f"{ROUTINE_ORDER}"
        )
        assert params == ("app",)

    def test_info_binds_the_name_last(self, dialect):
        sql, params = MySQLRoutineInfoQueryStatement(
            dialect, routine_name="f", schema="app"
        ).to_sql()

        assert sql == (
            f"SELECT {ROUTINE_PROJECTION} {ROUTINE_FROM} "
            "WHERE `r`.`ROUTINE_SCHEMA` = %s AND `r`.`ROUTINE_NAME` = %s "
            f"{ROUTINE_ORDER}"
        )
        assert params == ("app", "f")

    def test_kind_narrows_a_name_shared_by_both_object_kinds(self, dialect):
        sql, params = MySQLRoutineInfoQueryStatement(
            dialect, routine_name="f", kind="FUNCTION", schema="app"
        ).to_sql()

        assert sql.endswith(
            "WHERE `r`.`ROUTINE_SCHEMA` = %s AND `r`.`ROUTINE_NAME` = %s "
            "AND `r`.`ROUTINE_TYPE` = %s "
            f"{ROUTINE_ORDER}"
        )
        assert params == ("app", "f", "FUNCTION")

    def test_the_join_keeps_procedures_and_functions_apart(self, dialect):
        """The kind is part of the join, not only of the projection.

        A function and a procedure may share a name, so joining on schema and
        name alone would attach one routine's arguments to the other.
        """
        sql, _ = MySQLRoutineListQueryStatement(dialect, schema="app").to_sql()

        assert "`r`.`ROUTINE_TYPE` = `p`.`ROUTINE_TYPE`" in sql


CONSTRAINT_PROJECTION = (
    "`tc`.`CONSTRAINT_SCHEMA`, `tc`.`TABLE_NAME`, `tc`.`CONSTRAINT_NAME`, "
    "`tc`.`CONSTRAINT_TYPE`, `tc`.`ENFORCED`, `cc`.`CHECK_CLAUSE`, "
    "`kcu`.`COLUMN_NAME`, `kcu`.`ORDINAL_POSITION`"
)

CONSTRAINT_FROM = (
    "FROM (`information_schema`.`TABLE_CONSTRAINTS` AS `tc` "
    "LEFT JOIN `information_schema`.`CHECK_CONSTRAINTS` AS `cc` "
    "ON `tc`.`CONSTRAINT_SCHEMA` = `cc`.`CONSTRAINT_SCHEMA` "
    "AND `tc`.`CONSTRAINT_NAME` = `cc`.`CONSTRAINT_NAME`) "
    "LEFT JOIN `information_schema`.`KEY_COLUMN_USAGE` AS `kcu` "
    "ON `tc`.`CONSTRAINT_SCHEMA` = `kcu`.`CONSTRAINT_SCHEMA` "
    "AND `tc`.`CONSTRAINT_NAME` = `kcu`.`CONSTRAINT_NAME` "
    "AND `tc`.`TABLE_SCHEMA` = `kcu`.`TABLE_SCHEMA` "
    "AND `tc`.`TABLE_NAME` = `kcu`.`TABLE_NAME`"
)

CONSTRAINT_ORDER = (
    "ORDER BY `tc`.`TABLE_NAME`, `tc`.`CONSTRAINT_NAME`, `kcu`.`ORDINAL_POSITION`"
)


class TestConstraintQueries:
    def test_list_is_left_joined_so_either_shape_survives(self, dialect):
        """A constraint has rows in at most one side relation.

        An inner join would answer only the CHECK constraints or only the
        column-bearing ones; both LEFT JOINs are what let one listing carry
        the whole family.
        """
        sql, params = MySQLConstraintListQueryStatement(dialect, schema="app").to_sql()

        assert sql == (
            f"SELECT {CONSTRAINT_PROJECTION} {CONSTRAINT_FROM} "
            "WHERE `tc`.`CONSTRAINT_SCHEMA` = %s "
            f"{CONSTRAINT_ORDER}"
        )
        assert params == ("app",)
        assert sql.count("LEFT JOIN") == 2

    def test_a_table_name_narrows_the_listing_and_binds_second(self, dialect):
        sql, params = MySQLConstraintListQueryStatement(
            dialect, table_name="orders", schema="app"
        ).to_sql()

        assert sql.endswith(
            "WHERE `tc`.`CONSTRAINT_SCHEMA` = %s AND `tc`.`TABLE_NAME` = %s "
            f"{CONSTRAINT_ORDER}"
        )
        assert params == ("app", "orders")

    def test_enforced_and_check_clause_are_projected(self, dialect):
        """The two facts a caller cannot recover from the constraint type alone."""
        sql, _ = MySQLConstraintListQueryStatement(dialect, schema="app").to_sql()

        assert "`tc`.`ENFORCED`" in sql
        assert "`cc`.`CHECK_CLAUSE`" in sql
