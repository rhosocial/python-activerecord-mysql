# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_ddl_improvements.py
"""Tests for MySQL DDL improvements: capability gating, UnsupportedFeatureError."""
import pytest
from unittest.mock import patch

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.expression import (
    Column,
    ColumnDefinition,
    CreateTableExpression,
    TableExpression,
    QueryExpression,
    CreateViewExpression,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.expression.statements import ViewOptions, ViewCheckOption
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class TestMySQLViewCapabilityGating:
    """Tests for MySQL VIEW DDL capability gating."""

    def test_create_or_replace_view_supported(self):
        """MySQL supports CREATE OR REPLACE VIEW."""
        dialect = MySQLDialect()
        assert dialect.supports_create_or_replace_view() is True

    def test_drop_view_if_exists_supported(self):
        """MySQL supports DROP VIEW IF EXISTS."""
        dialect = MySQLDialect()
        assert dialect.supports_if_exists_view() is True

    def test_drop_view_cascade_not_supported(self):
        """MySQL does not support DROP VIEW CASCADE."""
        dialect = MySQLDialect()
        assert dialect.supports_cascade_view() is False

    def test_materialized_view_not_supported(self):
        """MySQL does not support materialized views."""
        dialect = MySQLDialect()
        assert dialect.supports_materialized_view() is False

    def test_create_view_check_option_gated(self):
        """WITH CHECK OPTION must fail fast when the capability is off."""
        dialect = MySQLDialect()
        query = QueryExpression(
            dialect, select=[Column(dialect, "id")], from_=TableExpression(dialect, "t")
        )
        expr = CreateViewExpression(
            dialect,
            view_name="v",
            query=query,
            options=ViewOptions(check_option=ViewCheckOption.CASCADED),
        )
        with patch.object(type(dialect), "supports_view_check_option", return_value=False):
            with pytest.raises(UnsupportedFeatureError, match="CHECK OPTION"):
                expr.to_sql()


class TestMySQLColumnCapabilityGating:
    """Tests for MySQL COLUMN DDL capability gating."""

    def test_foreign_key_on_delete_supported(self):
        """MySQL supports FK ON DELETE."""
        dialect = MySQLDialect()
        assert dialect.supports_foreign_key_on_delete() is True

    def test_foreign_key_on_update_supported(self):
        """MySQL supports FK ON UPDATE."""
        dialect = MySQLDialect()
        assert dialect.supports_foreign_key_on_update() is True

    def test_fk_match_not_supported(self):
        """MySQL does not support FK MATCH."""
        dialect = MySQLDialect()
        assert dialect.supports_fk_match() is False


class TestMySQLTriggerCapabilityGating:
    """Tests for MySQL TRIGGER DDL capability gating."""

    def test_trigger_referencing_not_supported(self):
        """MySQL does not support trigger REFERENCING clause."""
        dialect = MySQLDialect()
        assert dialect.supports_trigger_referencing() is False

    def test_trigger_when_not_supported(self):
        """MySQL does not support trigger WHEN clause."""
        dialect = MySQLDialect()
        assert dialect.supports_trigger_when() is False

    def test_instead_of_trigger_not_supported(self):
        """MySQL does not support INSTEAD OF triggers."""
        dialect = MySQLDialect()
        assert dialect.supports_instead_of_trigger() is False


class TestMySQLFunctionCapabilityGating:
    """Tests for MySQL FUNCTION DDL capability gating."""

    def test_stored_function_supported(self):
        """MySQL supports stored functions."""
        dialect = MySQLDialect()
        assert dialect.supports_stored_function() is True


class TestMySQLSchemaCapabilityGating:
    """Tests for MySQL SCHEMA DDL capability gating."""

    def test_create_schema_supported(self):
        """MySQL supports CREATE SCHEMA (alias for CREATE DATABASE)."""
        dialect = MySQLDialect()
        assert dialect.supports_create_schema() is True

    def test_drop_schema_supported(self):
        """MySQL supports DROP SCHEMA (alias for DROP DATABASE)."""
        dialect = MySQLDialect()
        assert dialect.supports_drop_schema() is True


class InheritedTable(ActiveRecord):
    __table_name__ = "inherited"

    id: int

    @classmethod
    def table_inherits(cls):
        return ["parent_a", "parent_b"]


class TablespacedTable(ActiveRecord):
    __table_name__ = "tablespaced"

    id: int

    @classmethod
    def table_tablespace(cls):
        return "ts_data"


class TestMySQLTableDeclarationGating:
    def test_table_declaration_defaults_are_absent(self):
        class Plain(ActiveRecord):
            __table_name__ = "plain_table_defaults"

            id: int

        dialect = MySQLDialect()
        expression = CreateTableExpression(
            dialect,
            Plain.__table_name__,
            columns=[ColumnDefinition(dialect, "id", IntegerType(dialect))],
            inherits=Plain.table_inherits(),
            tablespace=Plain.table_tablespace(),
        )
        assert expression.inherits == []
        assert expression.tablespace is None

    def test_table_inherits_is_propagated_and_rejected(self):
        dialect = MySQLDialect(version=(8, 0, 0))
        assert dialect.supports_table_inheritance() is False
        expression = CreateTableExpression(
            dialect,
            InheritedTable.__table_name__,
            columns=[ColumnDefinition(dialect, "id", IntegerType(dialect))],
            inherits=InheritedTable.table_inherits(),
            tablespace=InheritedTable.table_tablespace(),
        )
        assert expression.inherits == ["parent_a", "parent_b"]
        with pytest.raises(UnsupportedFeatureError, match="INHERITS"):
            expression.to_sql()

    def test_table_tablespace_is_propagated_and_rejected(self):
        dialect = MySQLDialect(version=(8, 0, 0))
        assert dialect.supports_table_tablespace() is False
        expression = CreateTableExpression(
            dialect,
            TablespacedTable.__table_name__,
            columns=[ColumnDefinition(dialect, "id", IntegerType(dialect))],
            inherits=TablespacedTable.table_inherits(),
            tablespace=TablespacedTable.table_tablespace(),
        )
        assert expression.tablespace == "ts_data"
        with pytest.raises(UnsupportedFeatureError, match="TABLESPACE"):
            expression.to_sql()
