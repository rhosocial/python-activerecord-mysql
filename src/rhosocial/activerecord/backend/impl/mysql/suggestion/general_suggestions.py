# src/rhosocial/activerecord/backend/impl/mysql/suggestion/general_suggestions.py
"""MySQL's general suggestion answers (JSON access operator, CREATE TABLE layout)."""
from rhosocial.activerecord.backend.suggestion.definitions import (
    ConcatenationFunctionSuggestion,
    CreateTableLayoutSuggestion,
    JSONAccessOperatorSuggestion,
)


class MySQLCreateTableLayoutSuggestionMixin:
    """MySQL inlines both indexes and table comments in ``CREATE TABLE``."""

    def suggest_create_table_layout(self) -> CreateTableLayoutSuggestion:
        inline_index = self.supports_inline_index()
        inline_comment = self.supports_table_comment()
        return CreateTableLayoutSuggestion(
            strategy="single" if inline_index and inline_comment else "split",
            inline_index=inline_index,
            inline_comment=inline_comment,
            state="actions",
        )


class MySQLJSONSuggestionMixin:
    """The JSON access operator MySQL renders for ``->`` / ``->>``."""

    def suggest_json_access_operator(self) -> JSONAccessOperatorSuggestion:
        return JSONAccessOperatorSuggestion(operator="->")


class MySQLStringConcatenationSuggestionMixin:
    """MySQL spells string concatenation with the ``CONCAT`` function."""

    def suggest_concatenation_function(self) -> ConcatenationFunctionSuggestion:
        return ConcatenationFunctionSuggestion(function="CONCAT")


__all__ = [
    "MySQLCreateTableLayoutSuggestionMixin",
    "MySQLJSONSuggestionMixin",
    "MySQLStringConcatenationSuggestionMixin",
]
