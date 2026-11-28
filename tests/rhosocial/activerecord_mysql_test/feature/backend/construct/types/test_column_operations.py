# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/types/test_column_operations.py
"""The operations on MySQL's own geometry column class.

The ``ST_*`` façades are thin wrappers over functions/spatial.py, gated on
supports_geometry_type(). These are render and gate assertions; the live
round-trip is run against the configured MySQL scenario.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.mysql.expression.column_types.column_types import MySQLGeometryColumn
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


@pytest.fixture
def dialect():
    return MySQLDialect(version=(8, 0, 46))


@pytest.fixture
def geometry(dialect):
    return MySQLGeometryColumn(dialect, "g")


@pytest.mark.parametrize(
    "method, name",
    [
        ("st_distance", "ST_DISTANCE"),
        ("st_contains", "ST_CONTAINS"),
        ("st_within", "ST_WITHIN"),
        ("st_intersects", "ST_INTERSECTS"),
    ],
)
def test_spatial_functions(geometry, dialect, method, name):
    other = MySQLGeometryColumn(dialect, "h")
    assert getattr(geometry, method)(other).to_sql() == (f"{name}(`g`, `h`)", ())


@pytest.mark.parametrize("method", ["st_distance", "st_contains", "st_within", "st_intersects"])
def test_spatial_functions_fail_without_the_capability(geometry, monkeypatch, method):
    monkeypatch.setattr(geometry._dialect, "supports_geometry_type", lambda: False)
    with pytest.raises(UnsupportedFeatureError, match="supports_geometry_type"):
        getattr(geometry, method)(geometry)


def test_a_geometry_field_resolves_to_the_mysql_class(dialect):
    from rhosocial.activerecord.backend.adapters import Geometry

    assert dialect.suggest_column_types().table[Geometry] is MySQLGeometryColumn
