# tests/rhosocial/activerecord_mysql_test/feature/backend/test_cli.py
"""
Tests for MySQL backend CLI (__main__.py).

Tests argument parsing, help output, and basic CLI functionality.
"""

import pytest
import sys
from unittest.mock import patch


class TestCLIParseArgs:
    """Tests for CLI argument parsing."""

    def test_parse_args_default_values(self):
        """Test default argument values for info subcommand."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'info']):
            args = parse_args()

            assert args.command == 'info'
            assert args.host == 'localhost'
            assert args.port == 3306
            assert args.user == 'root'
            assert args.password == ''
            assert args.charset == 'utf8mb4'
            assert args.output == 'table'
            assert args.log_level == 'INFO'
            assert args.use_async is False
            assert args.verbose == 0

    def test_parse_args_custom_values(self):
        """Test custom argument values for query subcommand."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', [
            'mysql', 'query',
            '--host', 'db.example.com',
            '--port', '3307',
            '--user', 'admin',
            '--password', 'secret',
            '--database', 'testdb',
            '--charset', 'latin1',
            '--output', 'json',
            '--log-level', 'DEBUG',
            'SELECT 1',
        ]):
            args = parse_args()

            assert args.command == 'query'
            assert args.host == 'db.example.com'
            assert args.port == 3307
            assert args.user == 'admin'
            assert args.password == 'secret'
            assert args.database == 'testdb'
            assert args.charset == 'latin1'
            assert args.output == 'json'
            assert args.log_level == 'DEBUG'

    def test_parse_args_query_subcommand(self):
        """Test query subcommand parsing."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'query', 'SELECT 1']):
            args = parse_args()

            assert args.command == 'query'
            assert args.sql == 'SELECT 1'

    def test_parse_args_query_with_file(self):
        """Test query subcommand with file option."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'query', '-f', 'test.sql']):
            args = parse_args()

            assert args.command == 'query'
            assert args.file == 'test.sql'
            assert args.sql is None

    def test_parse_args_introspect_subcommand(self):
        """Test introspect subcommand parsing."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'introspect', 'tables']):
            args = parse_args()

            assert args.command == 'introspect'
            assert args.type == 'tables'

    def test_parse_args_introspect_with_name(self):
        """Test introspect subcommand with table name."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'introspect', 'table', 'users']):
            args = parse_args()

            assert args.command == 'introspect'
            assert args.type == 'table'
            assert args.name == 'users'

    def test_parse_args_introspect_valid_types(self):
        """Test all valid introspect types."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args, INTROSPECT_TYPES

        for introspect_type in INTROSPECT_TYPES:
            with patch.object(sys, 'argv', ['mysql', 'introspect', introspect_type]):
                args = parse_args()
                assert args.type == introspect_type

    def test_parse_args_use_async(self):
        """Test --use-async flag in query subcommand."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'query', '--use-async', 'SELECT 1']):
            args = parse_args()

            assert args.command == 'query'
            assert args.use_async is True

    def test_parse_args_verbose(self):
        """Test verbose flags with subcommand."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', '-v', 'info']):
            args = parse_args()
            assert args.verbose == 1

        with patch.object(sys, 'argv', ['mysql', '-vv', 'info']):
            args = parse_args()
            assert args.verbose == 2

    def test_parse_args_info_command(self):
        """Test info subcommand."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'info']):
            args = parse_args()

            assert args.command == 'info'

    def test_parse_args_version(self):
        """Test --version option in info subcommand."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'info', '--version', '5.7.0']):
            args = parse_args()

            assert args.command == 'info'
            assert args.version == '5.7.0'


class TestCLISerialization:
    """Tests for CLI output serialization."""

    def test_serialize_none(self):
        """Test serializing None."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import _serialize_for_output

        assert _serialize_for_output(None) is None

    def test_serialize_string(self):
        """Test serializing string."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import _serialize_for_output

        assert _serialize_for_output("test") == "test"

    def test_serialize_int(self):
        """Test serializing integer."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import _serialize_for_output

        assert _serialize_for_output(42) == 42

    def test_serialize_float(self):
        """Test serializing float."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import _serialize_for_output

        assert _serialize_for_output(3.14) == 3.14

    def test_serialize_bool(self):
        """Test serializing boolean."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import _serialize_for_output

        assert _serialize_for_output(True) is True
        assert _serialize_for_output(False) is False

    def test_serialize_list(self):
        """Test serializing list."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import _serialize_for_output

        result = _serialize_for_output([1, "two", None])
        assert result == [1, "two", None]

    def test_serialize_dict(self):
        """Test serializing dict."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import _serialize_for_output

        result = _serialize_for_output({"key": "value", "num": 42})
        assert result == {"key": "value", "num": 42}

    def test_serialize_nested(self):
        """Test serializing nested structures."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import _serialize_for_output

        result = _serialize_for_output({
            "list": [1, 2, 3],
            "nested": {"a": "b"}
        })
        assert result == {"list": [1, 2, 3], "nested": {"a": "b"}}

    def test_serialize_enum(self):
        """Test serializing Enum."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import _serialize_for_output
        from enum import Enum

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        assert _serialize_for_output(Color.RED) == "red"
        assert _serialize_for_output(Color.BLUE) == "blue"

    def test_serialize_fallback(self):
        """Test fallback serialization for unknown types."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import _serialize_for_output

        class CustomObject:
            def __str__(self):
                return "custom"

        result = _serialize_for_output(CustomObject())
        assert result == "custom"


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_main_help(self, capsys):
        """Test main help output doesn't crash."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', '--help']):
            with pytest.raises(SystemExit):
                parse_args()

        captured = capsys.readouterr()
        assert 'Execute SQL queries' in captured.out or 'usage:' in captured.out.lower()

    def test_query_help(self, capsys):
        """Test query subcommand help."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'query', '--help']):
            with pytest.raises(SystemExit):
                parse_args()

        captured = capsys.readouterr()
        assert 'query' in captured.out.lower() or 'sql' in captured.out.lower()

    def test_introspect_help(self, capsys):
        """Test introspect subcommand help."""
        from rhosocial.activerecord.backend.impl.mysql.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'introspect', '--help']):
            with pytest.raises(SystemExit):
                parse_args()

        captured = capsys.readouterr()
        assert 'introspect' in captured.out.lower() or 'type' in captured.out.lower()
