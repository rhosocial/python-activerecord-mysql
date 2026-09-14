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

    def format_spatial_literal(self, expr: "MySQLSpatialLiteralExpression") -> Tuple[str, tuple]:
        """Format MySQLSpatialLiteralExpression."""
        if expr.srid is not None:
            sql = "ST_GeomFromText(%s, %s)"
            params = (expr.wkt, expr.srid)
        else:
            sql = "ST_GeomFromText(%s)"
            params = (expr.wkt,)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def format_st_geom_from_wkb(self, expr: "MySQLSTGeomFromWKBExpression") -> Tuple[str, tuple]:
        """Format MySQLSTGeomFromWKBExpression."""
        if expr.srid is not None:
            sql = "ST_GeomFromWKB(%s, %s)"
            params = (expr.wkb, expr.srid)
        else:
            sql = "ST_GeomFromWKB(%s)"
            params = (expr.wkb,)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def format_st_as_text(self, expr: "MySQLSTAsTextExpression") -> Tuple[str, tuple]:
        """Format MySQLSTAsTextExpression."""
        sql = f"ST_AsText({self.get_parameter_placeholder()})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, (expr.geom,)

    def format_st_as_geojson(self, expr: "MySQLSTAsGeoJSONExpression") -> Tuple[str, tuple]:
        """Format MySQLSTAsGeoJSONExpression."""
        if not self.supports_geojson():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(self.name, "GeoJSON functions (requires MySQL 5.7.5+)")
        sql = f"ST_AsGeoJSON({self.get_parameter_placeholder()})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, (expr.geom,)

    def format_create_spatial_index(self, expr: "MySQLCreateSpatialIndexExpression") -> Tuple[str, tuple]:
        """Format MySQLCreateSpatialIndexExpression."""
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

    def format_create_spatial_index(self, index_name: str, table_name: str, column: str) -> Tuple[str, tuple]:
        """Format CREATE SPATIAL INDEX statement."""
        if not self.supports_spatial_index():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(self.name, "SPATIAL indexes (requires MySQL 5.7+)")
        return (
            f"CREATE SPATIAL INDEX {self.format_identifier(index_name)} "
            f"ON {self.format_identifier(table_name)} "
            f"({self.format_identifier(column)})",
            (),
        )
