# tests/providers/fixtures/_common.py
"""Shared helpers for the MySQL DDL expression fixtures.

The MySQL backend's :meth:`format_storage_options_expression` quotes string option
values (``ENGINE='InnoDB'``), while the authoritative ``.sql`` schema files
under ``tests/rhosocial/activerecord_mysql_test/feature/<feature>/schema/``
use the unquoted storage form. :func:`to_mysql_ddl_sql` post-processes the
SQL produced by ``CreateTableStatement.to_sql()`` so the generated DDL
matches the reference files for that bit.

The former second post-processing step -- re-injecting ``ON DELETE`` /
``ON UPDATE`` referential actions that ``format_table_constraint`` used to
drop for plain table constraints -- is gone: the two-level constraint nodes
render every ``TableForeignKeyConstraint`` through the shared
``ReferencesClause`` machinery, so the actions the fixtures declare are on
the wire the dialect produced.

Providers call :func:`create_table_sql` instead of ``expr.to_sql()`` directly
to obtain the canonical ``(sql, params)`` tuple.
"""

from __future__ import annotations

import re
from typing import Tuple

from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    DropTableStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table


_STORAGE_OPTION_RE = re.compile(r"([A-Z_ ]+=)'([^']*)'")


def _strip_storage_option_quotes(sql: str) -> str:
    """Drop single quotes around storage option values (``ENGINE='InnoDB'`` -> ``ENGINE=InnoDB``)."""
    return _STORAGE_OPTION_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}", sql)


def to_mysql_ddl_sql(expr: CreateTableStatement) -> Tuple[str, tuple]:
    """Generate canonical MySQL DDL for a :class:`CreateTableStatement`.

    Post-processes the dialect output to drop quotes around storage option
    values. Referential actions need no help any more: the table-level
    foreign-key branch renders them through the shared ``ReferencesClause``
    path, so what the fixtures declare is what the dialect emits.

    Returns:
        The ``(sql, params)`` tuple suitable for ``backend.execute``.
    """
    sql, params = expr.to_sql()
    sql = _strip_storage_option_quotes(sql)
    return sql, params


def create_table_sql(expr: CreateTableStatement) -> Tuple[str, tuple]:
    """Public alias for :func:`to_mysql_ddl_sql`."""
    return to_mysql_ddl_sql(expr)


def drop_table(dialect, table_name: str) -> DropTableStatement:
    """Build a canonical ``DROP TABLE IF EXISTS`` expression."""
    return DropTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
        if_exists=True,
    )
