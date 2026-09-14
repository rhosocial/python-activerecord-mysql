# src/rhosocial/activerecord/backend/impl/mysql/mixins/vector.py
from typing import List, Tuple


class MySQLVectorMixin:
    """MySQL vector data type implementation."""

    MAX_VECTOR_DIMENSION = 16384

    def supports_vector_type(self) -> bool:
        return self.version >= (9, 0, 0)

    def supports_vector_index(self) -> bool:
        return self.version >= (9, 0, 1)

    def get_max_vector_dimension(self) -> int:
        return self.MAX_VECTOR_DIMENSION

    def format_vector_literal(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLVectorExpression` node (VECTOR literal)."""
        sql, params = self._format_vector_literal_parts(expr.vector)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _format_vector_literal_parts(self, values: List[float]) -> Tuple[str, tuple]:
        """Format VECTOR literal value."""
        if len(values) > self.MAX_VECTOR_DIMENSION:
            raise ValueError(
                f"Vector dimension {len(values)} exceeds maximum supported dimension {self.MAX_VECTOR_DIMENSION}"
            )
        vector_str = "[" + ",".join(str(v) for v in values) + "]"
        return f"STRING_TO_VECTOR({self.p()})", (vector_str,)

    def format_string_to_vector(self, expr) -> Tuple[str, tuple]:
        """Format MySQLStringToVectorExpression or a raw vector string."""
        from ..expression.vector import MySQLStringToVectorExpression

        if isinstance(expr, MySQLStringToVectorExpression):
            vector_str = expr.vector_str
            alias = expr.alias
        else:
            vector_str = expr
            alias = None
        sql = f"STRING_TO_VECTOR({self.get_parameter_placeholder()})"
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, (vector_str,)

    def format_vector_to_string(self, expr) -> Tuple[str, tuple]:
        """Format MySQLVectorToStringExpression or a raw vector reference."""
        from ..expression.vector import MySQLVectorToStringExpression

        if isinstance(expr, MySQLVectorToStringExpression):
            sql = f"VECTOR_TO_STRING({self.get_parameter_placeholder()})"
            params: Tuple = (expr.vector_col,)
            alias = expr.alias
        else:
            sql = f"VECTOR_TO_STRING({expr})"
            params = ()
            alias = None
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, params

    def format_vector_dim(self, expr) -> Tuple[str, tuple]:
        """Format MySQLVectorDimExpression or a raw vector reference."""
        from ..expression.vector import MySQLVectorDimExpression

        if isinstance(expr, MySQLVectorDimExpression):
            sql = f"VECTOR_DIM({self.get_parameter_placeholder()})"
            params: Tuple = (expr.vector_col,)
            alias = expr.alias
        else:
            sql = f"VECTOR_DIM({expr})"
            params = ()
            alias = None
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, params

    def format_distance_euclidean(self, expr) -> Tuple[str, tuple]:
        sql = f"DISTANCE_EUCLIDEAN({expr.vec1}, {expr.vec2})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()

    def format_distance_cosine(self, expr) -> Tuple[str, tuple]:
        sql = f"DISTANCE_COSINE({expr.vec1}, {expr.vec2})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()

    def format_distance_dot(self, expr) -> Tuple[str, tuple]:
        sql = f"DISTANCE_DOT({expr.vec1}, {expr.vec2})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()

    def format_create_vector_index(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLCreateVectorIndexExpression` node."""
        from ..expression.vector import MySQLCreateVectorIndexExpression

        if not isinstance(expr, MySQLCreateVectorIndexExpression):
            raise TypeError(
                f"format_create_vector_index expects MySQLCreateVectorIndexExpression, "
                f"got {type(expr).__name__}"
            )

        if not self.supports_vector_index():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(self.name, "VECTOR indexes (requires MySQL 9.0.1+)")
        return (
            f"CREATE VECTOR INDEX {self.format_identifier(expr.index_name)} "
            f"ON {self.format_identifier(expr.table_name)} "
            f"({self.format_identifier(expr.column)})",
            (),
        )
