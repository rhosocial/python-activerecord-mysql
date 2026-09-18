# tests/rhosocial/activerecord_mysql_test/feature/backend/test_identifier_quoting.py
"""
MySQLDialect identifier quoting tests.

Verifies backtick quoting, escaped internal backticks, reserved word
detection, and the IdentifierQuotingWarning emitted for unquoted
reserved words.
"""

import warnings

import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.warnings import IdentifierQuotingWarning


class TestMySQLIdentifierQuoting:
    """Test MySQLDialect format_identifier and reserved words."""

    def test_format_identifier_default_backtick_quotes(self):
        d = MySQLDialect()
        assert d.format_identifier("users") == "`users`"

    def test_format_identifier_need_quote_false(self):
        d = MySQLDialect()
        assert d.format_identifier("users", need_quote=False) == "users"

    def test_format_identifier_escapes_internal_backticks(self):
        d = MySQLDialect()
        assert d.format_identifier("my`table") == "`my``table`"

    def test_format_identifier_need_quote_false_no_escaping(self):
        d = MySQLDialect()
        assert d.format_identifier("my`table", need_quote=False) == "my`table"

    def test_reserved_words_is_frozenset(self):
        d = MySQLDialect()
        assert isinstance(d.reserved_words, frozenset)

    def test_reserved_words_count(self):
        d = MySQLDialect()
        assert len(d.reserved_words) > 100  # MySQL has many reserved words

    def test_is_reserved_word_case_insensitive(self):
        d = MySQLDialect()
        assert d.is_reserved_word("SELECT") is True
        assert d.is_reserved_word("select") is True

    def test_is_reserved_word_non_reserved(self):
        d = MySQLDialect()
        assert d.is_reserved_word("users") is False

    def test_reserved_word_warning_emitted(self):
        d = MySQLDialect()
        with pytest.warns(IdentifierQuotingWarning, match="select"):
            d.format_identifier("select", need_quote=False)

    def test_no_warning_for_non_reserved_word(self):
        d = MySQLDialect()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            d.format_identifier("users", need_quote=False)

    def test_balanced_quotes_security(self):
        """Security: verify balanced backtick count."""
        d = MySQLDialect()
        for ident in ["users", "my`table", "a``b"]:
            result = d.format_identifier(ident)
            assert result.count("`") % 2 == 0, f"Unbalanced backticks: {result}"
