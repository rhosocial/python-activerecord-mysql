"""
This file provides the concrete implementation of the `IBasicProvider` interface
that is defined in the `rhosocial-activerecord-testsuite` package.

Its main responsibilities are:
1.  Reporting which test scenarios (database configurations) are available.
2.  Setting up the database environment for a given test. This includes:
    - Getting the correct database configuration for the scenario.
    - Configuring the ActiveRecord model with a database connection.
    - Dropping any old tables and creating the necessary table schema.
3.  Cleaning up any resources after a test runs.
"""
import os
import logging
from typing import Type, List, Tuple, Optional

logger = logging.getLogger(__name__)

from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter
from rhosocial.activerecord.model import ActiveRecord
# The models are defined generically in the testsuite...
from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (
    User, TypeCase, ValidatedFieldUser, TypeTestModel, ValidatedUser, TypeAdapterTest, YesOrNoBooleanAdapter,
    MappedUser, MappedPost, MappedComment, ColumnMappingModel, MixedAnnotationModel
)
# Import async models
from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (
    AsyncUser, AsyncTypeCase, AsyncValidatedUser, AsyncValidatedFieldUser, AsyncTypeTestModel,
    AsyncTypeAdapterTest, AsyncMappedUser, AsyncMappedPost, AsyncMappedComment,
    AsyncColumnMappingModel, AsyncMixedAnnotationModel
)
from rhosocial.activerecord.testsuite.feature.basic.interfaces import IBasicProvider
# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class BasicProvider(IBasicProvider):
    """
    This is the MySQL backend's implementation for the basic features test group.
    It connects the generic tests in the testsuite with the actual MySQL database.
    """

    def __init__(self):
        self._active_backends = []
        self._active_async_backends = []

    def get_test_scenarios(self) -> List[str]:
        """Returns a list of names for all enabled scenarios for this backend."""
        return list(get_enabled_scenarios().keys())

    def _track_backend(self, backend_instance, collection: List) -> None:
        if backend_instance not in collection:
            collection.append(backend_instance)

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given model."""
        backend_class, config = get_scenario(scenario_name)
        model_class.configure(config, backend_class)

        backend_instance = model_class.__backend__
        self._track_backend(backend_instance, self._active_backends)

        self._reset_table_sync(model_class, table_name)
        return model_class

    async def _setup_async_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given async model."""
        from rhosocial.activerecord.backend.impl.mysql import AsyncMySQLBackend

        _, config = get_scenario(scenario_name)
        await model_class.configure(config, AsyncMySQLBackend)

        backend_instance = model_class.__backend__
        self._track_backend(backend_instance, self._active_async_backends)

        await self._reset_table_async(model_class, table_name)
        return model_class

    def _reset_table_sync(self, model_class: Type[ActiveRecord], table_name: str) -> None:
        try:
            model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 0")
            model_class.__backend__.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        finally:
            model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 1")

        schema_sql = self._load_mysql_schema(f"{table_name}.sql")
        model_class.__backend__.execute(schema_sql)

    async def _reset_table_async(self, model_class: Type[ActiveRecord], table_name: str) -> None:
        try:
            await model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 0")
            await model_class.__backend__.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        finally:
            await model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 1")

        schema_sql = self._load_mysql_schema(f"{table_name}.sql")
        await model_class.__backend__.execute(schema_sql)

    async def _initialize_async_model_schema(self, model_class: Type[ActiveRecord], table_name: str):
        """Initialize schema for a model that shares backend with another model."""
        await self._reset_table_async(model_class, table_name)

    def _initialize_model_schema(self, model_class: Type[ActiveRecord], table_name: str) -> None:
        """Initialize schema for a model that shares backend with another model."""
        self._reset_table_sync(model_class, table_name)

    def _setup_multiple_models(self, model_classes: List[Tuple[Type[ActiveRecord], str]], scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Helper to set up multiple related models for a test, sharing a single backend."""
        if not model_classes:
            return tuple()

        first_model_class, first_table_name = model_classes[0]
        first_model = self._setup_model(first_model_class, scenario_name, first_table_name)
        shared_backend = first_model.__backend__

        result = [first_model]

        for model_class, table_name in model_classes[1:]:
            model_class.__connection_config__ = first_model.__connection_config__
            model_class.__backend_class__ = first_model.__backend_class__
            model_class.__backend__ = shared_backend
            self._track_backend(shared_backend, self._active_backends)
            self._initialize_model_schema(model_class, table_name)
            result.append(model_class)

        return tuple(result)

    # --- Implementation of the IBasicProvider interface ---

    def setup_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for user model tests."""
        return self._setup_model(User, scenario_name, "users")

    async def setup_async_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async user model tests."""
        return await self._setup_async_model(AsyncUser, scenario_name, "users")

    def setup_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for type case model tests."""
        return self._setup_model(TypeCase, scenario_name, "type_cases")

    async def setup_async_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async type case model tests."""
        return await self._setup_async_model(AsyncTypeCase, scenario_name, "type_cases")

    def setup_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for type test model tests."""
        import pytest
        # Check JSON support BEFORE setting up schema to avoid SQL error
        backend_class, config = get_scenario(scenario_name)
        # Create backend instance and introspect to get actual version
        temp_backend = backend_class(connection_config=config)
        temp_backend.connect()
        actual_version = temp_backend.get_server_version()
        temp_backend.disconnect()
        # Check if JSON is supported
        from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
        temp_dialect = MySQLDialect(actual_version)
        if not temp_dialect.supports_json_type():
            pytest.skip(f"JSON type not supported by MySQL version {actual_version}")
        # JSON is supported, proceed with normal setup
        model = self._setup_model(TypeTestModel, scenario_name, "type_tests")
        return model

    async def setup_async_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async type test model tests."""
        import pytest
        # Check JSON support BEFORE setting up schema to avoid SQL error
        from rhosocial.activerecord.backend.impl.mysql import AsyncMySQLBackend
        _, config = get_scenario(scenario_name)
        # Create backend instance and introspect to get actual version
        temp_backend = AsyncMySQLBackend(connection_config=config)
        await temp_backend.connect()
        actual_version = await temp_backend.get_server_version()
        await temp_backend.disconnect()
        # Check if JSON is supported
        from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
        temp_dialect = MySQLDialect(actual_version)
        if not temp_dialect.supports_json_type():
            pytest.skip(f"JSON type not supported by MySQL version {actual_version}")
        # JSON is supported, proceed with normal setup
        model = await self._setup_async_model(AsyncTypeTestModel, scenario_name, "type_tests")
        return model

    def setup_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for validated field user model tests."""
        return self._setup_model(ValidatedFieldUser, scenario_name, "validated_field_users")

    async def setup_async_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async validated field user model tests."""
        return await self._setup_async_model(AsyncValidatedFieldUser, scenario_name, "validated_field_users")

    def setup_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for validated user model tests."""
        return self._setup_model(ValidatedUser, scenario_name, "validated_users")

    async def setup_async_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async validated user model tests."""
        return await self._setup_async_model(AsyncValidatedUser, scenario_name, "validated_users")

    def setup_mapped_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for MappedUser, MappedPost, and MappedComment models."""
        return self._setup_multiple_models([
            (MappedUser, "users"),
            (MappedPost, "posts"),
            (MappedComment, "comments")
        ], scenario_name)

    async def setup_async_mapped_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for AsyncMappedUser, AsyncMappedPost, and AsyncMappedComment models."""
        user = await self._setup_async_model(AsyncMappedUser, scenario_name, "users")
        shared_backend = user.__backend__

        post_model_class = AsyncMappedPost
        post_model_class.__connection_config__ = user.__connection_config__
        post_model_class.__backend_class__ = user.__backend_class__
        post_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(post_model_class, "posts")

        comment_model_class = AsyncMappedComment
        comment_model_class.__connection_config__ = user.__connection_config__
        comment_model_class.__backend_class__ = user.__backend_class__
        comment_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(comment_model_class, "comments")

        return user, post_model_class, comment_model_class

    def setup_mixed_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for ColumnMappingModel and MixedAnnotationModel."""
        return self._setup_multiple_models([
            (ColumnMappingModel, "column_mapping_items"),
            (MixedAnnotationModel, "mixed_annotation_items")
        ], scenario_name)

    async def setup_async_mixed_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for AsyncColumnMappingModel and AsyncMixedAnnotationModel."""
        column_mapping_model = await self._setup_async_model(AsyncColumnMappingModel, scenario_name, "column_mapping_items")
        shared_backend = column_mapping_model.__backend__

        mixed_annotation_model_class = AsyncMixedAnnotationModel
        mixed_annotation_model_class.__connection_config__ = column_mapping_model.__connection_config__
        mixed_annotation_model_class.__backend_class__ = column_mapping_model.__backend_class__
        mixed_annotation_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(mixed_annotation_model_class, "mixed_annotation_items")

        return column_mapping_model, mixed_annotation_model_class

    def setup_type_adapter_model_and_schema(self, scenario_name: Optional[str] = None) -> Type[ActiveRecord]:
        """Sets up the database for the `TypeAdapterTest` model tests."""
        if scenario_name is None:
            scenario_name = self.get_test_scenarios()[0] if self.get_test_scenarios() else "default"
        return self._setup_model(TypeAdapterTest, scenario_name, "type_adapter_tests")

    async def setup_async_type_adapter_model_and_schema(self, scenario_name: Optional[str] = None) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncTypeAdapterTest` model tests."""
        if scenario_name is None:
            scenario_name = self.get_test_scenarios()[0] if self.get_test_scenarios() else "default"
        return await self._setup_async_model(AsyncTypeAdapterTest, scenario_name, "type_adapter_tests")

    def get_yes_no_adapter(self) -> 'BaseSQLTypeAdapter':
        """Returns an instance of the YesOrNoBooleanAdapter."""
        return YesOrNoBooleanAdapter()

    def _load_mysql_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_mysql_test", "feature", "basic", "schema")
        schema_path = os.path.join(schema_dir, filename)

        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()

    def cleanup_after_test(self, scenario_name: str):
        """
        Performs cleanup after a test, dropping all tables and disconnecting backends.
        """
        tables_to_drop = [
            'users', 'type_cases', 'type_tests', 'validated_field_users',
            'validated_users', 'type_adapter_tests', 'posts', 'comments',
            'column_mapping_items', 'mixed_annotation_items'
        ]
        for backend_instance in self._active_backends:
            try:
                backend_instance.execute("SET FOREIGN_KEY_CHECKS = 0")
                for table_name in tables_to_drop:
                    try:
                        backend_instance.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                    except Exception:
                        pass
                backend_instance.execute("SET FOREIGN_KEY_CHECKS = 1")
            finally:
                try:
                    backend_instance.disconnect()
                except Exception:
                    pass

        self._active_backends.clear()

    async def cleanup_after_test_async(self, scenario_name: str):
        """
        Performs async cleanup after a test, dropping all tables and disconnecting backends.
        
        Fix for mysql-connector-python bug: "RuntimeError: Set changed size during iteration"
        The issue is that conn.close() iterates over _cursors WeakSet while cursor.close()
        modifies it. We fix this by manually closing cursors BEFORE calling disconnect().
        """
        tables_to_drop = [
            'users', 'type_cases', 'type_tests', 'validated_field_users',
            'validated_users', 'type_adapter_tests', 'posts', 'comments',
            'column_mapping_items', 'mixed_annotation_items'
        ]
        for backend_instance in self._active_async_backends:
            try:
                try:
                    await backend_instance.execute("SET FOREIGN_KEY_CHECKS = 0")
                    for table_name in tables_to_drop:
                        try:
                            await backend_instance.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                        except Exception:
                            pass
                    await backend_instance.execute("SET FOREIGN_KEY_CHECKS = 1")
                except Exception:
                    pass
            finally:
                try:
                    await self._safe_async_disconnect(backend_instance)
                except Exception:
                    pass

        self._active_async_backends.clear()

    async def _safe_async_disconnect(self, backend_instance):
        """
        Safely disconnect an async MySQL backend, avoiding the "Set changed size during iteration" bug.
        
        The bug occurs because:
        1. backend._connection is a mysql.connector.aio connection
        2. connection._cursors is a WeakSet
        3. connection.close() iterates over _cursors while cursor.close() modifies it
        4. Result: RuntimeError
        
        Fix: Close all cursors manually BEFORE calling connection.close()
        """
        connection = backend_instance._connection
        if connection is None:
            return
        
        # Step 1: Close all cursors manually (while event loop is still alive!)
        cursors = list(connection._cursors)
        for cursor in cursors:
            try:
                await cursor.close()
            except Exception as e:
                logger.warning(f"Error closing cursor during cleanup: {type(e).__name__}: {e}")
        # Now _cursors should be empty
        
        # Step 2: Now safe to close connection
        # The iteration in connection.close() will find an empty set
        try:
            await connection.close()
        except Exception as e:
            logger.warning(f"Error closing connection during cleanup: {type(e).__name__}: {e}")
        
        backend_instance._connection = None
