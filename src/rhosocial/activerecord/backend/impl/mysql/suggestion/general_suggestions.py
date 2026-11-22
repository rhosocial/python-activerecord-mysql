# src/rhosocial/activerecord/backend/impl/mysql/suggestion/general_suggestions.py
"""MySQL's general suggestion answers (JSON access operator)."""
from rhosocial.activerecord.backend.suggestion.definitions import (
    ConcatenationFunctionSuggestion,
    JSONAccessOperatorSuggestion,
)
from rhosocial.activerecord.backend.suggestion.protocols import (
    JSONSuggestionSupport,
    StringConcatenationSuggestionSupport,
)


class MySQLJSONSuggestionMixin(JSONSuggestionSupport):
    """The JSON access operator MySQL renders for ``->`` / ``->>``."""

    def suggest_json_access_operator(self) -> JSONAccessOperatorSuggestion:
        return JSONAccessOperatorSuggestion(operator="->")


class MySQLStringConcatenationSuggestionMixin(StringConcatenationSuggestionSupport):
    """MySQL spells string concatenation with the ``CONCAT`` function."""

    def suggest_concatenation_function(self) -> ConcatenationFunctionSuggestion:
        return ConcatenationFunctionSuggestion(function="CONCAT")


__all__ = ["MySQLJSONSuggestionMixin", "MySQLStringConcatenationSuggestionMixin"]
