# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/dialect/test_schema_support.py
"""Tests for the namespace capability declared on the MySQL dialect.

MySQL has no schema namespace layer inside a database: ``SCHEMA`` is only an
alias for ``DATABASE``. The naming protocol is therefore
``NamespaceSupport``, which MySQL satisfies by qualifying names with the
database -- the outer ``catalog_name`` slot -- and declining the inner one.
A name carrying a ``schema_name`` cannot be expressed and is reported rather
than dropped; one carrying ``catalog_name`` renders as `` `app`.`users` ``.

The granular DDL flags stay True because servers do accept CREATE/DROP SCHEMA
as synonyms of their DATABASE counterparts.
"""
import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.protocols import NamespaceSupport
from rhosocial.activerecord.backend.expression.objects import Schema, Table
from rhosocial.activerecord.backend.expression.statements.ddl_schema import (
    CreateSchemaStatement,
    DropSchemaStatement,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


class TestSchemaCapability:
    """Umbrella flag and granular schema DDL capability bits."""

    def _dialect(self) -> MySQLDialect:
        return MySQLDialect()

    def test_supports_schema_is_false(self):
        assert self._dialect().supports_schema() is False

    def test_does_not_qualify_names_with_a_schema(self):
        """MySQL has no inner schema, so a name must never claim one."""
        assert self._dialect().supports_schema_qualification() is False

    def test_implements_namespace_support_protocol(self):
        """The naming protocol is NamespaceSupport, and MySQL satisfies it."""
        assert isinstance(self._dialect(), NamespaceSupport) is True

    def test_create_drop_schema_are_database_aliases(self):
        """Servers accept the SCHEMA spelling, but it creates a database."""
        d = self._dialect()
        assert d.supports_create_schema() is True
        assert d.supports_drop_schema() is True
        assert d.supports_schema_if_not_exists() is True
        assert d.supports_schema_if_exists() is True


class TestCatalogQualification:
    """The catalog slot is where a database name belongs."""

    def _dialect(self) -> MySQLDialect:
        return MySQLDialect()

    def test_supports_catalog(self):
        d = self._dialect()
        assert d.supports_catalog() is True
        assert d.supports_catalog_qualification() is True

    def test_catalog_name_renders_qualified(self):
        d = self._dialect()
        sql, params = Table(d, "users", catalog_name="app").to_sql()
        assert sql == "`app`.`users`"
        assert params == ()

    def test_absent_catalog_renders_bare(self):
        d = self._dialect()
        assert Table(d, "users").to_sql()[0] == "`users`"

    def test_schema_name_is_reported_not_dropped(self):
        """MySQL cannot express a three-part name, so it raises instead."""
        d = self._dialect()
        with pytest.raises(UnsupportedFeatureError, match="schema-qualified"):
            Table(d, "users", schema_name="app").to_sql()

    def test_catalog_name_rejects_name_separator(self):
        """MySQL reserves ``.`` because it separates qualified name parts."""
        d = self._dialect()
        with pytest.raises(UnsupportedFeatureError, match="name-separator"):
            Table(d, "users", catalog_name="ap.p").to_sql()

    def test_catalog_name_rejects_over_length(self):
        d = self._dialect()
        with pytest.raises(UnsupportedFeatureError, match="64 characters"):
            Table(d, "users", catalog_name="a" * 65).to_sql()


class TestSchemaStatementRendering:
    """CREATE/DROP SCHEMA render as the DATABASE synonyms MySQL parses.

    The probes answered True before these formatters existed, so a caller could
    be told the capability was present and then be refused by the dispatch.
    These tests are the other half of that claim: the statements render, and
    the clauses MySQL's grammar does not have are refused by name.
    """

    def _dialect(self) -> MySQLDialect:
        return MySQLDialect()

    def test_create_schema_renders(self):
        d = self._dialect()
        sql, params = CreateSchemaStatement(d, Schema(d, "app")).to_sql()
        assert sql == "CREATE SCHEMA `app`"
        assert params == ()

    def test_create_schema_if_not_exists_renders(self):
        d = self._dialect()
        sql, params = CreateSchemaStatement(
            d, Schema(d, "app"), if_not_exists=True
        ).to_sql()
        assert sql == "CREATE SCHEMA IF NOT EXISTS `app`"
        assert params == ()

    def test_create_schema_authorization_is_refused(self):
        """MySQL has no AUTHORIZATION owner clause on CREATE SCHEMA."""
        d = self._dialect()
        expression = CreateSchemaStatement(
            d, Schema(d, "app"), authorization="app_user"
        )
        with pytest.raises(UnsupportedFeatureError, match="AUTHORIZATION"):
            expression.to_sql()

    def test_drop_schema_renders(self):
        d = self._dialect()
        sql, params = DropSchemaStatement(d, Schema(d, "app")).to_sql()
        assert sql == "DROP SCHEMA `app`"
        assert params == ()

    def test_drop_schema_if_exists_renders(self):
        d = self._dialect()
        sql, params = DropSchemaStatement(
            d, Schema(d, "app"), if_exists=True
        ).to_sql()
        assert sql == "DROP SCHEMA IF EXISTS `app`"
        assert params == ()

    def test_drop_schema_cascade_is_refused(self):
        """MySQL's DROP SCHEMA grammar ends at the name; no CASCADE."""
        d = self._dialect()
        expression = DropSchemaStatement(d, Schema(d, "app"), cascade=True)
        with pytest.raises(UnsupportedFeatureError, match="CASCADE"):
            expression.to_sql()

    def test_drop_schema_restrict_is_refused(self):
        """MySQL has no RESTRICT clause on DROP SCHEMA."""
        d = self._dialect()
        expression = DropSchemaStatement(d, Schema(d, "app"), restrict=True)
        with pytest.raises(UnsupportedFeatureError, match="RESTRICT"):
            expression.to_sql()
