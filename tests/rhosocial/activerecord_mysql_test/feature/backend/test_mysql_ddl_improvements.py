# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_ddl_improvements.py
"""Tests for MySQL DDL improvements: capability gating, UnsupportedFeatureError."""
import pytest
from unittest.mock import patch, PropertyMock

from rhosocial.activerecord.backend.expression import (
    Column,
    TableExpression,
    QueryExpression,
    CreateViewExpression,
    DropViewExpression,
)
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
