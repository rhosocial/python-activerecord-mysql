# src/rhosocial/activerecord/backend/impl/mysql/mixins/function.py
from typing import Dict

# MySQL function version support: function_name -> (min_version, max_version)
# min_version: minimum supported version (inclusive), None = all versions
# max_version: maximum supported version (inclusive), None = no upper limit
MYSQL_FUNCTION_VERSIONS = {
    "json_extract": ((5, 7, 8), None),
    "json_extract_text": ((5, 7, 13), None),
    "json_build_object": (None, (0, 0, 0)),
    "json_array_elements": (None, (0, 0, 0)),
    "json_objectagg": ((5, 7, 22), None),
    "json_arrayagg": ((5, 7, 22), None),
    "json_unquote": ((5, 7, 8), None),
    "json_object": ((5, 7, 8), None),
    "json_array": ((5, 7, 8), None),
    "json_contains": ((5, 7, 8), None),
    "json_set": ((5, 7, 8), None),
    "json_remove": ((5, 7, 8), None),
    "json_type": ((5, 7, 8), None),
    "json_valid": ((5, 7, 8), None),
    "json_search": ((5, 7, 8), None),
    "st_geom_from_text": ((5, 7, 0), None),
    "st_geom_from_wkb": ((5, 7, 0), None),
    "st_as_text": ((5, 7, 0), None),
    "st_as_geojson": ((5, 7, 5), None),
    "st_distance": ((5, 7, 0), None),
    "st_within": ((5, 7, 0), None),
    "st_contains": ((5, 7, 0), None),
    "st_intersects": ((5, 7, 0), None),
    "match_against": (None, None),
    "find_in_set": (None, None),
    "elt": (None, None),
    "field": (None, None),
    "round_": (None, None),
    "pow": (None, None),
    "power": (None, None),
    "sqrt": (None, None),
    "mod": (None, None),
    "ceil": (None, None),
    "floor": (None, None),
    "trunc": (None, None),
    "max_": (None, None),
    "min_": (None, None),
    "avg": (None, None),
    "bit_and": (None, None),
    "bit_or": (None, None),
    "bit_xor": (None, None),
    "bit_count": (None, None),
    "bit_get_bit": ((8, 0, 0), None),
    "bit_shift_left": ((8, 0, 0), None),
    "bit_shift_right": ((8, 0, 0), None),
}


class MySQLFunctionMixin:
    """MySQL SQL function version support."""

    _MYSQL_FUNCTION_VERSIONS = MYSQL_FUNCTION_VERSIONS

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping."""
        from rhosocial.activerecord.backend.expression.functions import (
            __all__ as core_functions,
        )
        from rhosocial.activerecord.backend.impl.mysql import functions as mysql_functions

        expression_constructors = {
            "xmlagg",
            "xmlattributes",
            "xmlcomment",
            "xmlconcat",
            "xmlelement",
            "xmlexists",
            "xmlforest",
            "xmlparse",
            "xmlpi",
            "xmlquery",
            "xmlroot",
            "xmlserialize",
            "xmltable",
        }
        result = {}
        for func_name in core_functions:
            if func_name not in expression_constructors:
                result[func_name] = self._is_mysql_function_supported(func_name)

        mysql_funcs = getattr(mysql_functions, "__all__", [])
        for func_name in mysql_funcs:
            if func_name not in result:
                result[func_name] = self._is_mysql_function_supported(func_name)

        return result

    def _is_mysql_function_supported(self, func_name: str) -> bool:
        """Check if a MySQL-specific function is supported based on version."""
        version_range = self._MYSQL_FUNCTION_VERSIONS.get(func_name)
        if version_range is None:
            return True

        min_version, max_version = version_range

        if min_version is not None and self.version < min_version:
            return False

        if max_version is not None and self.version > max_version:
            return False

        return True
