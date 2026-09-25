# tests/rhosocial/activerecord_mysql_test/feature/backend/ddl/test_derived_ddl_inline_index.py
"""MySQL inline-index support for ActiveRecord-derived DDL (positive path).

SQLite and other SQL-standard dialects cannot inline index definitions, so the
positive rendering path is exercised here on a dialect that supports it
(``supports_inline_index()`` is True).
"""

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

from rhosocial.activerecord.base import UseIndex
from rhosocial.activerecord.ddl import TableDDLDeriver
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.model import ActiveRecord


class Indexed(ActiveRecord):
    __table_name__ = "indexed"

    id: int
    email: Annotated[str, UseIndex("idx_indexed_email", unique=True)]


def mysql_dialect():
    return MySQLDialect((8, 0, 0))


def test_create_table_renders_inline_index():
    deriver = TableDDLDeriver(Indexed, mysql_dialect())
    expression = deriver.create_table()

    assert [index.name for index in expression.indexes] == ["idx_indexed_email"]
    sql, _ = expression.to_sql()
    assert "UNIQUE INDEX `idx_indexed_email` (`email`)" in sql


def test_create_indexes_is_empty_when_inline_capable():
    deriver = TableDDLDeriver(Indexed, mysql_dialect())
    assert deriver.create_indexes() == []
