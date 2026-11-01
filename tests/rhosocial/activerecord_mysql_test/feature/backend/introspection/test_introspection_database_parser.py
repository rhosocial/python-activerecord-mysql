# tests/rhosocial/activerecord_mysql_test/feature/backend/introspection/test_introspection_database_parser.py
"""Parser-level tests for MySQL database and table introspection.

``introspect database`` used to crash when the run had not adapted the
dialect: the parser joined the backend's private ``_version``, which is
``None`` until a server has been asked. These tests call the parsers with no
server at all -- the row the query would have returned is supplied directly
-- so they fail on the parser rather than on a missing database.
"""

from types import SimpleNamespace

from rhosocial.activerecord.backend.impl.mysql.introspection import (
    MySQLIntrospector,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.introspection.types import TableType


class _NoServerBackend:
    """The parts of a MySQL backend an introspector reads, and nothing else."""

    def __init__(self, version=None, cached_version=None):
        self.config = SimpleNamespace(database="shop")
        self.dialect = MySQLDialect(version)
        self._cached_version = cached_version

    def get_cached_server_version(self):
        return self._cached_version


class _UnusedExecutor:
    """An executor that fails loudly if a parser-level test asks for SQL."""

    def execute(self, sql, params=()):
        raise AssertionError("a parser-level test must not execute SQL")


def _introspector(**kwargs) -> MySQLIntrospector:
    return MySQLIntrospector(_NoServerBackend(**kwargs), _UnusedExecutor())


_SCHEMATA_ROW = {
    "DEFAULT_CHARACTER_SET_NAME": "utf8mb4",
    "DEFAULT_COLLATION_NAME": "utf8mb4_0900_ai_ci",
}


class TestParseDatabaseInfo:
    """The record is built from the row and the version, never a private."""

    def test_unadapted_version_is_reported_as_unknown(self):
        """Before adaptation there is no version: say "unknown", not 8.0.0."""
        info = _introspector().parse_database_info([_SCHEMATA_ROW])

        assert info.version == "unknown"
        assert info.version_tuple == (0, 0, 0)

    def test_row_values_fill_the_rest_of_the_record(self):
        info = _introspector().parse_database_info([_SCHEMATA_ROW])

        assert info.name == "shop"
        assert info.vendor == "MySQL"
        assert info.encoding == "utf8mb4"
        assert info.collation == "utf8mb4_0900_ai_ci"
        # Not selected by the statement, so not invented here.
        assert info.table_count is None
        assert info.size_bytes is None

    def test_adapted_version_is_reported(self):
        info = _introspector(version=(8, 0, 36)).parse_database_info([_SCHEMATA_ROW])

        assert info.version == "8.0.36"
        assert info.version_tuple == (8, 0, 36)

    def test_backend_cache_is_used_when_the_dialect_has_none(self):
        """A connected-but-unadapted backend still knows what it measured."""
        info = _introspector(cached_version=(5, 7, 44)).parse_database_info(
            [_SCHEMATA_ROW]
        )

        assert info.version == "5.7.44"
        assert info.version_tuple == (5, 7, 44)

    def test_no_rows_leaves_the_row_derived_fields_empty(self):
        info = _introspector(version=(8, 0, 36)).parse_database_info([])

        assert info.name == "shop"
        assert info.encoding is None
        assert info.collation is None


class TestParseTables:
    """The catalog's kind is carried through instead of being flattened."""

    def test_table_kinds_are_reported_as_named(self):
        rows = [
            {"TABLE_NAME": "users", "TABLE_TYPE": "BASE TABLE"},
            {"TABLE_NAME": "user_summary", "TABLE_TYPE": "VIEW"},
            {"TABLE_NAME": "INNODB_METRICS", "TABLE_TYPE": "SYSTEM VIEW"},
        ]

        tables = _introspector().parse_tables(rows, schema=None)

        assert [table.name for table in tables] == [
            "users",
            "user_summary",
            "INNODB_METRICS",
        ]
        assert [table.table_type for table in tables] == [
            TableType.BASE_TABLE,
            TableType.VIEW,
            TableType.SYSTEM_TABLE,
        ]

    def test_schema_defaults_to_the_connected_database(self):
        rows = [{"TABLE_NAME": "users", "TABLE_TYPE": "BASE TABLE"}]

        tables = _introspector().parse_tables(rows, schema=None)

        assert tables[0].schema == "shop"

    def test_an_explicit_schema_wins_over_the_default(self):
        rows = [{"TABLE_NAME": "users", "TABLE_TYPE": "BASE TABLE"}]

        tables = _introspector().parse_tables(rows, schema="archive")

        assert tables[0].schema == "archive"

    def test_storage_split_is_reported_and_summed(self):
        """The three storage slots answer three questions, so all are filled.

        ``DATA_LENGTH`` and ``INDEX_LENGTH`` are the server's own byte
        accounting, reported as it said them; ``size_bytes`` is their sum, so
        a table with no index is not reported as smaller than its rows.
        """
        rows = [
            {
                "TABLE_NAME": "users",
                "TABLE_TYPE": "BASE TABLE",
                "TABLE_ROWS": 3,
                "DATA_LENGTH": 16384,
                "INDEX_LENGTH": 0,
            }
        ]

        table = _introspector().parse_tables(rows, schema=None)[0]

        assert table.row_count == 3
        assert table.data_size_bytes == 16384
        assert table.index_size_bytes == 0
        assert table.size_bytes == 16384

    def test_a_table_with_no_bytes_reports_none_rather_than_zero(self):
        """No rows reported is not the same as zero bytes reported."""
        rows = [{"TABLE_NAME": "empty_view", "TABLE_TYPE": "VIEW"}]

        table = _introspector().parse_tables(rows, schema=None)[0]

        assert table.data_size_bytes is None
        assert table.index_size_bytes is None
        assert table.size_bytes is None
