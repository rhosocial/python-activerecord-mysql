# src/rhosocial/activerecord/backend/impl/mysql/expression/column_types.py
"""MySQL's own column classes.

Core's ``GeometryColumn`` promises only the surface every backend can execute.
MySQL has a set of ``ST_*`` functions for a geometry column, so this module
names a subclass that carries them; a field annotated with ``Geometry`` resolves
to it on this backend.

The operations are thin façades over the function factories in
``functions/spatial.py``. Each one is gated on ``supports_geometry_type()``: a
server without spatial types fails loudly by capability name instead of
rendering SQL the server would refuse.
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.column_types import GeometryColumn

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.bases import BaseExpression


#: The capability switches this module may ask a dialect for. A switch is a
#: declared name bound to the probe the dialect actually defines; a name that
#: is not here is not a capability this module owns.
_CAPABILITY_PROBES = {
    "supports_geometry_type": lambda dialect: dialect.supports_geometry_type,
}


def _require(dialect, switch: str) -> None:
    probe = _CAPABILITY_PROBES[switch](dialect)
    if not probe():
        raise UnsupportedFeatureError(
            type(dialect).__name__,
            switch,
            f"this operation needs the {switch}() capability",
        )


class MySQLGeometryColumn(GeometryColumn):
    """A geometry column with MySQL's ``ST_*`` functions."""

    def st_distance(self, other) -> "BaseExpression":
        """``ST_DISTANCE(col, other)``."""
        _require(self._dialect, "supports_geometry_type")
        from ..functions.spatial import st_distance

        return st_distance(self._dialect, self, other)

    def st_contains(self, other) -> "BaseExpression":
        """``ST_CONTAINS(col, other)``."""
        _require(self._dialect, "supports_geometry_type")
        from ..functions.spatial import st_contains

        return st_contains(self._dialect, self, other)

    def st_within(self, other) -> "BaseExpression":
        """``ST_WITHIN(col, other)``."""
        _require(self._dialect, "supports_geometry_type")
        from ..functions.spatial import st_within

        return st_within(self._dialect, self, other)

    def st_intersects(self, other) -> "BaseExpression":
        """``ST_INTERSECTS(col, other)``."""
        _require(self._dialect, "supports_geometry_type")
        from ..functions.spatial import st_intersects

        return st_intersects(self._dialect, self, other)


__all__ = ["MySQLGeometryColumn"]
