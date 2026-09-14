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

    def format_spatial_literal(self, expr, srid: Optional[int] = None) -> Tuple[str, tuple]:
        """Format MySQLSpatialLiteralExpression or a raw WKT string."""
        from ..expression.spatial import MySQLSpatialLiteralExpression

        if isinstance(expr, MySQLSpatialLiteralExpression):
            wkt = expr.wkt
            srid = expr.srid
            alias = expr.alias
        else:
            wkt = expr
            alias = None
        sql, params = self._format_spatial_literal_parts(wkt, srid)
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
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

    def format_st_geom_from_wkb(self, expr, srid: Optional[int] = None) -> Tuple[str, tuple]:
        """Format MySQLSTGeomFromWKBExpression or raw WKB bytes."""
        from ..expression.spatial import MySQLSTGeomFromWKBExpression

        if isinstance(expr, MySQLSTGeomFromWKBExpression):
            wkb = expr.wkb
            srid = expr.srid
            alias = expr.alias
        else:
            wkb = expr
            alias = None
        if srid is not None:
            sql = "ST_GeomFromWKB(%s, %s)"
            params: Tuple = (wkb, srid)
        else:
            sql = "ST_GeomFromWKB(%s)"
            params = (wkb,)
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, params

    def format_st_as_text(self, expr) -> Tuple[str, tuple]:
        """Format MySQLSTAsTextExpression or a raw geometry reference."""
        from ..expression.spatial import MySQLSTAsTextExpression

        if isinstance(expr, MySQLSTAsTextExpression):
            sql = f"ST_AsText({self.get_parameter_placeholder()})"
            params: Tuple = (expr.geom,)
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
            sql = f"ST_AsGeoJSON({self.get_parameter_placeholder()})"
            params: Tuple = (expr.geom,)
            alias = expr.alias
        else:
            sql = f"ST_AsGeoJSON({expr})"
            params = ()
            alias = None
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, params

    def format_create_spatial_index(
        self, expr, table_name: Optional[str] = None, column: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format MySQLCreateSpatialIndexExpression or raw index arguments."""
        from ..expression.spatial import MySQLCreateSpatialIndexExpression

        if isinstance(expr, MySQLCreateSpatialIndexExpression):
            index_name = expr.index_name
            table_name = expr.table_name
            column = expr.column
        else:
            index_name = expr
        if not self.supports_spatial_index():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(self.name, "SPATIAL indexes (requires MySQL 5.7+)")
        return (
            f"CREATE SPATIAL INDEX {self.format_identifier(index_name)} "
            f"ON {self.format_identifier(table_name)} "
            f"({self.format_identifier(column)})",
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
