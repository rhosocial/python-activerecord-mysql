# tests/rhosocial/activerecord_mysql_test/feature/backend/named_connection/test_resolver.py
"""
Tests for MySQL named connection resolver.

This test module covers:
- NamedConnectionResolver with MySQL backend
- MySQL-specific connection configurations
- Integration tests using example_connections module
"""
import types
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.named_connection.resolver import (
    NamedConnectionResolver,
    resolve_named_connection,
    list_named_connections_in_module,
)
from rhosocial.activerecord.backend.named_connection.exceptions import (
    NamedConnectionNotFoundError,
    NamedConnectionModuleNotFoundError,
    NamedConnectionInvalidReturnTypeError,
    NamedConnectionNotCallableError,
    NamedConnectionMissingParameterError,
    NamedConnectionInvalidParameterError,
)
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig


class TestMysqlNamedConnectionResolverUnit:
    """Unit tests for NamedConnectionResolver with MySQL backend."""

    def test_resolve_mysql_config(self):
        """Test resolving a MySQL connection config."""
        module = types.ModuleType("test_mysql_connections")

        def dev_db(database: str = "test_db"):
            return MySQLConnectionConfig(
                host="localhost",
                port=3306,
                database=database,
                username="root",
                password="password",
            )

        module.dev_db = dev_db
        with patch("importlib.import_module", return_value=module):
            config = NamedConnectionResolver("test_mysql_connections.dev_db").load().resolve({})
            assert isinstance(config, MySQLConnectionConfig)
            assert config.host == "localhost"
            assert config.database == "test_db"

    def test_resolve_mysql_with_custom_database(self):
        """Test resolving MySQL config with custom database parameter."""
        module = types.ModuleType("test_mysql_connections")

        def dev_db(database: str = "test_db"):
            return MySQLConnectionConfig(
                host="localhost",
                port=3306,
                database=database,
                username="root",
                password="password",
            )

        module.dev_db = dev_db
        with patch("importlib.import_module", return_value=module):
            config = NamedConnectionResolver("test_mysql_connections.dev_db").load().resolve(
                {"database": "my_app_db"}
            )
            assert isinstance(config, MySQLConnectionConfig)
            assert config.database == "my_app_db"

    def test_resolve_mysql_missing_required_param(self):
        """Test resolve fails when required MySQL parameter is missing."""
        module = types.ModuleType("test_mysql_connections")

        def strict_db(host: str):
            return MySQLConnectionConfig(host=host)

        module.strict_db = strict_db
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_mysql_connections.strict_db").load()
            with pytest.raises(NamedConnectionMissingParameterError):
                resolver.resolve({})

    def test_resolve_mysql_invalid_return_type(self):
        """Test resolve fails when callable returns non-BaseConfig."""
        module = types.ModuleType("test_mysql_connections")

        def bad_connection():
            return {"host": "localhost"}

        module.bad_connection = bad_connection
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_mysql_connections.bad_connection").load()
            with pytest.raises(NamedConnectionInvalidReturnTypeError):
                resolver.resolve({})

    def test_list_mysql_connections(self):
        """Test listing MySQL connections in a module."""
        module = types.ModuleType("test_mysql_connections")

        def dev_db(database: str = "test_db"):
            return MySQLConnectionConfig(host="localhost", database=database)

        def prod_db():
            return MySQLConnectionConfig(host="prod.example.com", database="prod")

        module.dev_db = dev_db
        module.prod_db = prod_db

        with patch("importlib.import_module", return_value=module):
            connections = list_named_connections_in_module("test_mysql_connections")
            names = [c["name"] for c in connections]
            assert "dev_db" in names
            assert "prod_db" in names


class TestMysqlNamedConnectionsIntegration:
    """Integration tests using actual example_connections module."""

    def test_mysql_96_connection(self):
        """Test resolving the mysql_96 named connection."""
        config = resolve_named_connection(
            "rhosocial.activerecord_mysql_test.feature.backend.named_connection.example_connections.mysql_96",
            {},
        )
        assert isinstance(config, MySQLConnectionConfig)
        assert config.host == "db-dev-1-n.rho.im"
        assert config.port == 13694
        assert config.database == "test_db"
        assert config.charset == "utf8mb4"

    def test_mysql_96_with_custom_database(self):
        """Test resolving mysql_96 with custom database parameter."""
        config = resolve_named_connection(
            "rhosocial.activerecord_mysql_test.feature.backend.named_connection.example_connections.mysql_96",
            {"database": "my_app"},
        )
        assert isinstance(config, MySQLConnectionConfig)
        assert config.database == "my_app"

    def test_mysql_96_with_pool(self):
        """Test resolving mysql_96_with_pool named connection."""
        config = resolve_named_connection(
            "rhosocial.activerecord_mysql_test.feature.backend.named_connection.example_connections.mysql_96_with_pool",
            {},
        )
        assert isinstance(config, MySQLConnectionConfig)
        assert config.pool_size == 5

    def test_mysql_96_with_custom_pool_size(self):
        """Test resolving mysql_96_with_pool with custom pool_size."""
        config = resolve_named_connection(
            "rhosocial.activerecord_mysql_test.feature.backend.named_connection.example_connections.mysql_96_with_pool",
            {"pool_size": "10"},
        )
        assert isinstance(config, MySQLConnectionConfig)
        assert config.pool_size == 10

    def test_mysql_96_readonly(self):
        """Test resolving mysql_96_readonly named connection."""
        config = resolve_named_connection(
            "rhosocial.activerecord_mysql_test.feature.backend.named_connection.example_connections.mysql_96_readonly",
            {},
        )
        assert isinstance(config, MySQLConnectionConfig)
        assert config.pool_timeout == 10

    def test_list_example_connections(self):
        """Test listing connections in example_connections module."""
        connections = list_named_connections_in_module(
            "rhosocial.activerecord_mysql_test.feature.backend.named_connection.example_connections"
        )
        names = [c["name"] for c in connections]
        assert "mysql_96" in names
        assert "mysql_96_with_pool" in names
        assert "mysql_96_readonly" in names

    def test_describe_mysql_96(self):
        """Test describing the mysql_96 connection."""
        resolver = NamedConnectionResolver(
            "rhosocial.activerecord_mysql_test.feature.backend.named_connection.example_connections.mysql_96"
        ).load()
        info = resolver.describe()
        assert info["is_class"] is False
        assert "database" in info["parameters"]
        if info.get("config_preview"):
            assert "password" not in info["config_preview"]
