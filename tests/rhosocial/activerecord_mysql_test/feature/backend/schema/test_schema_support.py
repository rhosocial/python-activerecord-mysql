# tests/rhosocial/activerecord_mysql_test/feature/backend/schema/test_schema_support.py
"""Tests for the SchemaSupport capability declared on the MySQL dialect.

Under strict semantics MySQL has no schema namespace layer inside a database:
``SCHEMA`` is only an alias for ``DATABASE``. The umbrella flag therefore must
be False, while the granular DDL flags stay True because servers do accept
CREATE/DROP SCHEMA as synonyms of their DATABASE counterparts.
"""
from rhosocial.activerecord.backend.dialect.protocols import SchemaSupport
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


class TestSchemaCapability:
    """Umbrella flag and granular schema DDL capability bits."""

    def _dialect(self) -> MySQLDialect:
        return MySQLDialect()

    def test_supports_schema_is_false(self):
        assert self._dialect().supports_schema() is False

    def test_implements_schema_support_protocol(self):
        assert isinstance(self._dialect(), SchemaSupport)

    def test_create_drop_schema_are_database_aliases(self):
        """Servers accept the SCHEMA spelling, but it creates a database."""
        d = self._dialect()
        assert d.supports_create_schema() is True
        assert d.supports_drop_schema() is True
        assert d.supports_schema_if_not_exists() is True
        assert d.supports_schema_if_exists() is True
