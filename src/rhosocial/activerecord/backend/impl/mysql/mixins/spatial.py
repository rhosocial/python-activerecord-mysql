# src/rhosocial/activerecord/backend/impl/mysql/mixins/spatial.py
from typing import Optional, Tuple


class MySQLSpatialMixin:
    """MySQL spatial data type implementation."""

    def supports_spatial_type(self, type_name: str) -> bool:
        valid_types = {
            "GEOMETRY", "POINT", "LINESTRING", "POLYGON",
            "MULTIPOINT", "MULTILINESTRING", "MULTIPOLYGON", "GEOMETRYCOLLECTION",
        }
        if type_name.upper() not in valid_types:
            return False
        return self.version >= (5, 7, 0)

    def supports_spatial_index(self) -> bool:
        return self.version >= (5, 7, 0)

    def supports_geojson(self) -> bool:
        return self.version >= (5, 7, 5)

    def supports_geometry_type(self) -> bool:
        return self.version >= (5, 7, 0)

    def supports_point_type(self) -> bool:
        return self.version >= (5, 7, 0)

    def supports_curve_type(self) -> bool:
        return self.version >= (5, 7, 0)

    def supports_surface_type(self) -> bool:
        return self.version >= (5, 7, 0)

    def supports_geometry_collection_type(self) -> bool:
        return self.version >= (5, 7, 0)

    def format_spatial_literal(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLSpatialLiteralExpression` node."""
        from ..expression.spatial import MySQLSpatialLiteralExpression

        if not isinstance(expr, MySQLSpatialLiteralExpression):
            raise TypeError(
                f"format_spatial_literal expects MySQLSpatialLiteralExpression, got {type(expr).__name__}"
            )

        sql, params = self._format_spatial_literal_parts(expr.wkt, expr.srid)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _format_spatial_literal_parts(self, wkt: str, srid: Optional[int] = None) -> Tuple[str, tuple]:
        """Format ST_GeomFromText from raw WKT and optional SRID."""
        if srid is not None:
            return "ST_GeomFromText(%s, %s)", (wkt, srid)
        return "ST_GeomFromText(%s)", (wkt,)

    def format_st_geom_from_text(self, expr) -> Tuple[str, tuple]:
        """Format MySQLSTGeomFromTextExpression or a raw WKT string."""
        from ..expression.spatial import MySQLSTGeomFromTextExpression

        if isinstance(expr, MySQLSTGeomFromTextExpression):
            wkt = expr.wkt
            alias = expr.alias
        else:
            wkt = expr
            alias = None
        sql, params = self._format_spatial_literal_parts(wkt, None)
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, params

    def format_st_geom_from_wkb(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLSTGeomFromWKBExpression` node."""
        from ..expression.spatial import MySQLSTGeomFromWKBExpression

        if not isinstance(expr, MySQLSTGeomFromWKBExpression):
            raise TypeError(
                f"format_st_geom_from_wkb expects MySQLSTGeomFromWKBExpression, got {type(expr).__name__}"
            )

        if expr.srid is not None:
            sql = "ST_GeomFromWKB(%s, %s)"
            params: Tuple = (expr.wkb, expr.srid)
        else:
            sql = "ST_GeomFromWKB(%s)"
            params = (expr.wkb,)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def format_st_as_text(self, expr) -> Tuple[str, tuple]:
        """Format MySQLSTAsTextExpression or a raw geometry reference."""
        from ..expression.spatial import MySQLSTAsTextExpression

        if isinstance(expr, MySQLSTAsTextExpression):
            sql = f"ST_AsText({expr.geom})"
            params: Tuple = ()
            alias = expr.alias
        else:
            sql = f"ST_AsText({expr})"
            params = ()
            alias = None
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, params

    def format_st_as_geojson(self, expr) -> Tuple[str, tuple]:
        """Format MySQLSTAsGeoJSONExpression or a raw geometry reference."""
        from ..expression.spatial import MySQLSTAsGeoJSONExpression

        if not self.supports_geojson():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(self.name, "GeoJSON functions (requires MySQL 5.7.5+)")
        if isinstance(expr, MySQLSTAsGeoJSONExpression):
            sql = f"ST_AsGeoJSON({expr.geom})"
            params: Tuple = ()
            alias = expr.alias
        else:
            sql = f"ST_AsGeoJSON({expr})"
            params = ()
            alias = None
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, params

    def format_create_spatial_index(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLCreateSpatialIndexExpression` node."""
        from ..expression.spatial import MySQLCreateSpatialIndexExpression

        if not isinstance(expr, MySQLCreateSpatialIndexExpression):
            raise TypeError(
                f"format_create_spatial_index expects MySQLCreateSpatialIndexExpression, "
                f"got {type(expr).__name__}"
            )

        if not self.supports_spatial_index():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(self.name, "SPATIAL indexes (requires MySQL 5.7+)")
        return (
            f"CREATE SPATIAL INDEX {self.format_identifier(expr.index_name)} "
            f"ON {self.format_identifier(expr.table_name)} "
            f"({self.format_identifier(expr.column)})",
            (),
        )

    def format_st_distance(self, expr) -> Tuple[str, tuple]:
        sql = f"ST_Distance({expr.geom1}, {expr.geom2})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()

    def format_st_within(self, expr) -> Tuple[str, tuple]:
        sql = f"ST_Within({expr.geom1}, {expr.geom2})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()

    def format_st_contains(self, expr) -> Tuple[str, tuple]:
        sql = f"ST_Contains({expr.geom1}, {expr.geom2})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()
