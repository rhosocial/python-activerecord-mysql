# src/rhosocial/activerecord/backend/impl/mysql/expression/json.py
"""
MySQL-specific JSON expression functions.

This module provides expression classes for MySQL JSON functions:
- MySQLJSONExtractExpression
- MySQLJSONObjectExpression
- MySQLJSONArrayExpression
- MySQLJSONContainsExpression
- JSONUnquoteExpression
- JSONSetExpression
- JSONRemoveExpression
- JSONTypeExpression
- JSONValidExpression
- JSONSearchExpression
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rhosocial.activerecord.backend.expression.bases import SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MySQLJSONExtractExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL JSON_EXTRACT expression.

    Extracts a value from a JSON document using a path.

    Example:
        >>> expr = MySQLJSONExtractExpression(dialect, 'data', '$.name')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_column: str,
        path: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.json_column = json_column
        self.path = path
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_extract"


class MySQLJSONObjectExpression(AliasableMixin, SQLValueExpression):
    """MySQL JSON_OBJECT expression.

    Creates a JSON object from key-value pairs.

    Example:
        >>> expr = MySQLJSONObjectExpression(dialect, {'name': 'Alice', 'age': 30})
        OR
        >>> expr = MySQLJSONObjectExpression(dialect, ('name', 'Alice'), ('age', 30))
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        data: Any = None,
        *,
        alias: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(dialect)
        self.data = data  # keep raw for get_params() introspection
        self.kwargs: Dict[str, Any] = dict(kwargs)
        if data is not None and kwargs:
            pairs = self._convert_to_pairs(data) + self._convert_to_pairs(kwargs)
        elif data is not None:
            pairs = self._convert_to_pairs(data)
        elif kwargs:
            pairs = self._convert_to_pairs(kwargs)
        else:
            pairs = []
        self.pairs = pairs
        self.alias = alias

    def _convert_to_pairs(self, data: Any) -> List[tuple]:
        """Convert dict or iterable to list of key-value tuples."""
        if isinstance(data, dict):
            return [(k, v) for k, v in data.items()]
        return list(data)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_object"


class MySQLJSONArrayExpression(AliasableMixin, SQLValueExpression):
    """MySQL JSON_ARRAY expression.

    Creates a JSON array from values.

    Example:
        >>> expr = MySQLJSONArrayExpression(dialect, [1, 2, 3])
        OR
        >>> expr = MySQLJSONArrayExpression(dialect, 1, 2, 3)
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        values: Any = None,
        *args: Any,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self._raw_values = values  # keep raw for get_params() introspection
        self.args = list(args)  # keep raw for get_params() introspection
        if values is not None and args:
            self.values = [values] + list(args)
        elif values is not None:
            self.values = values if isinstance(values, list) else [values]
        elif args:
            self.values = list(args)
        else:
            self.values = []
        self.alias = alias

    def get_params(self) -> Dict[str, Any]:
        """Return the raw constructor arguments.

        The ``values`` parameter is normalized into ``self.values`` during
        construction; returning the raw form keeps the round-trip
        (serialize -> deserialize) from double-applying the positional args.
        """
        return {"values": self._raw_values, "args": self.args, "alias": self.alias}

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_array"


class MySQLJSONContainsExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL JSON_CONTAINS expression.

    Checks if a JSON document contains a specific value.

    Example:
        >>> expr = MySQLJSONContainsExpression(dialect, 'data', 'urgent', '$.tags')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_column: str,
        value: str,
        path: Optional[str] = None,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.json_column = json_column
        self.value = value
        self.path = path
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_contains"


class JSONUnquoteExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL JSON_UNQUOTE expression.

    Removes quotes from a JSON-quoted string.

    Args:
        dialect: The SQL dialect.
        json_val: JSON value to unquote.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_val: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.json_val = json_val
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_unquote"


class JSONSetExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL JSON_SET expression.

    Inserts or updates values in a JSON document.

    Args:
        dialect: The SQL dialect.
        json_doc: JSON document column or expression.
        path: JSON path to set.
        value: Value to set at the path.
        path_value_pairs: Additional path-value pairs.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_doc: str,
        path: str,
        value: Any,
        path_value_pairs: Optional[List[tuple]] = None,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.json_doc = json_doc
        self.path = path
        self.value = value
        self.path_value_pairs = path_value_pairs
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_set"


class JSONRemoveExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL JSON_REMOVE expression.

    Removes data from a JSON document.

    Args:
        dialect: The SQL dialect.
        json_doc: JSON document column or expression.
        path: JSON path to remove.
        paths: Additional paths to remove.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.json_doc = json_doc
        self.path = path
        self.paths = paths
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_remove"


class JSONTypeExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL JSON_TYPE expression.

    Returns the type of a JSON value.

    Args:
        dialect: The SQL dialect.
        json_val: JSON value to check.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_val: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.json_val = json_val
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_type"


class JSONValidExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL JSON_VALID expression.

    Checks whether a value is valid JSON.

    Args:
        dialect: The SQL dialect.
        json_val: JSON value to validate.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_val: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.json_val = json_val
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_valid"


class JSONSearchExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL JSON_SEARCH expression.

    Searches a JSON document for a string and returns the path.

    Args:
        dialect: The SQL dialect.
        json_doc: JSON document column or expression.
        search_str: String to search for.
        path: Optional JSON path scope.
        all: If True, return all matches; if False, return first match.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_doc: str,
        search_str: str,
        path: Optional[str] = None,
        all: bool = False,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.json_doc = json_doc
        self.search_str = search_str
        self.path = path
        self.all = all
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_search"


__all__ = [
    "MySQLJSONExtractExpression",
    "MySQLJSONObjectExpression",
    "MySQLJSONArrayExpression",
    "MySQLJSONContainsExpression",
    "JSONUnquoteExpression",
    "JSONSetExpression",
    "JSONRemoveExpression",
    "JSONTypeExpression",
    "JSONValidExpression",
    "JSONSearchExpression",
]
