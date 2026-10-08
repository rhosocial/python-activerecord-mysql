# tests/rhosocial/activerecord_mysql_test/feature/backend/test_schema_support.py
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
from rhosocial.activerecord.backend.expression.objects import Table
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