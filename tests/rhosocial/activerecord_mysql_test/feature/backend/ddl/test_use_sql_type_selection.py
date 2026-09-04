# tests/rhosocial/activerecord_mysql_test/feature/backend/ddl/test_use_sql_type_selection.py
"""Multi-type ``UseSqlType`` selection on MySQL, incl. 5.6/5.7 version gating.

``JsonType`` is only renderable on MySQL 5.7+; on 5.6 the selection must fall
through to a non-JSON declared type (or the version-aware suggestion). A
never-adapted dialect (version=None) is treated optimistically.
"""

from typing import Annotated

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.types import JsonType
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLLongTextType
from rhosocial.activerecord.base import ModelSchemaGenerator
from rhosocial.activerecord.base.fields import UseSqlType
from rhosocial.activerecord.model import ActiveRecord


class _JsonDoc(ActiveRecord):
    payload: Annotated[dict, UseSqlType(JsonType(), MySQLLongTextType())]


def _type_of(version):
    dialect = MySQLDialect(version=version)
    expr = ModelSchemaGenerator.generate_create_table(_JsonDoc, dialect)
    return type(expr.columns[0].data_type).__name__


def test_supports_json_type_version_gated():
    assert MySQLDialect().supports_data_type(JsonType()) is True          # unknown → optimistic
    assert MySQLDialect(version=(5, 6, 50)).supports_data_type(JsonType()) is False
    assert MySQLDialect(version=(5, 7, 30)).supports_data_type(JsonType()) is True


def test_render_json_type_version_gated():
    assert MySQLDialect(version=(5, 7, 30)).format_data_type(JsonType()) == ("JSON", ())
    with pytest.raises(UnsupportedFeatureError, match="JSON column type"):
        MySQLDialect(version=(5, 6, 50)).format_data_type(JsonType())


def test_selection_mysql57_prefers_json():
    assert _type_of((5, 7, 30)) == "JsonType"


def test_selection_mysql56_falls_through_to_longtext():
    assert _type_of((5, 6, 50)) == "MySQLLongTextType"


def test_selection_unknown_version_optimistic():
    assert _type_of(None) == "JsonType"


def test_declaration_order_overrides_version_preference():
    """LONGTEXT declared first wins on every MySQL version."""
    class _LongFirst(ActiveRecord):
        payload: Annotated[dict, UseSqlType(MySQLLongTextType(), JsonType())]

    for version in ((5, 6, 50), (5, 7, 30)):
        dialect = MySQLDialect(version=version)
        expr = ModelSchemaGenerator.generate_create_table(_LongFirst, dialect)
        assert type(expr.columns[0].data_type).__name__ == "MySQLLongTextType"