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

    def format_spatial_literal(self, wkt: str, srid: Optional[int] = None) -> Tuple[str, tuple]:
        return self._format_spatial_literal_parts(wkt, srid)

    def _format_spatial_literal_parts(self, wkt: str, srid: Optional[int] = None) -> Tuple[str, tuple]:
        if srid is not None:
            return "ST_GeomFromText(%s, %s)", (wkt, srid)
        return "ST_GeomFromText(%s)", (wkt,)

    def format_st_geom_from_text(self, expr) -> Tuple[str, tuple]:
        sql, params = self._format_spatial_literal_parts(expr.wkt, None)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def format_st_geom_from_wkb(self, wkb: bytes, srid: Optional[int] = None) -> Tuple[str, tuple]:
        if srid is not None:
            return "ST_GeomFromWKB(%s, %s)", (wkb, srid)
        return "ST_GeomFromWKB(%s)", (wkb,)

    def format_st_as_text(self, geom: str) -> Tuple[str, tuple]:
        return f"ST_AsText({geom})", ()

    def format_st_as_geojson(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsGeoJSON function (MySQL 5.7.5+)."""
        if not self.supports_geojson():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(self.name, "GeoJSON functions (requires MySQL 5.7.5+)")
        return f"ST_AsGeoJSON({geom})", ()

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
