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
from typing import Type, List, Tuple

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
        # This list will track the backend instances created during the setup phase.
        self._active_backends = []

    def get_test_scenarios(self) -> List[str]:
        """Returns a list of names for all enabled scenarios for this backend."""
        return list(get_enabled_scenarios().keys())

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given model."""
        # 1. Get the backend class (MySQLBackend) and connection config for the requested scenario.
        backend_class, config = get_scenario(scenario_name)

        # 2. Configure the generic model class with our specific backend and config.
        model_class.configure(config, backend_class)

        backend_instance = model_class.__backend__
        if backend_instance not in self._active_backends:
            self._active_backends.append(backend_instance)

        # 3. Prepare the database schema.
        try:
            model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 0")
            model_class.__backend__.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        finally:
            model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 1")

        schema_sql = self._load_mysql_schema(f"{table_name}.sql")
        
        # Adjust for JSON support if necessary
        requires_json = table_name in ['type_tests', 'type_cases']
        if requires_json and not self._backend_supports_json(backend_instance):
            schema_sql = self._adjust_schema_for_json_support(schema_sql, backend_instance)

        model_class.__backend__.execute(schema_sql)

        return model_class

    def _setup_multiple_models(self, model_classes: List[Tuple[Type[ActiveRecord], str]], scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Helper to set up multiple related models for a test."""
        result = []
        for model_class, table_name in model_classes:
            configured_model = self._setup_model(model_class, scenario_name, table_name)
            result.append(configured_model)
        return tuple(result)

    # --- Implementation of the IBasicProvider interface ---

    def setup_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for user model tests."""
        return self._setup_model(User, scenario_name, "users")

    def setup_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for type case model tests."""
        return self._setup_model(TypeCase, scenario_name, "type_cases")

    def setup_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for type test model tests."""
        return self._setup_model(TypeTestModel, scenario_name, "type_tests")

    def setup_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for validated field user model tests."""
        return self._setup_model(ValidatedFieldUser, scenario_name, "validated_field_users")

    def setup_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for validated user model tests."""
        return self._setup_model(ValidatedUser, scenario_name, "validated_users")

    def setup_mapped_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for MappedUser, MappedPost, and MappedComment models."""
        return self._setup_multiple_models([
            (MappedUser, "users"),
            (MappedPost, "posts"),
            (MappedComment, "comments")
        ], scenario_name)

    def setup_mixed_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for ColumnMappingModel and MixedAnnotationModel."""
        return self._setup_multiple_models([
            (ColumnMappingModel, "column_mapping_items"),
            (MixedAnnotationModel, "mixed_annotation_items")
        ], scenario_name)

    def setup_type_adapter_model_and_schema(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `TypeAdapterTest` model tests."""
        return self._setup_model(TypeAdapterTest, scenario_name, "type_adapter_tests")

    def get_yes_no_adapter(self) -> 'BaseSQLTypeAdapter':
        """Returns an instance of the YesOrNoBooleanAdapter."""
        return YesOrNoBooleanAdapter()

    # --- Async implementations ---

    async def setup_async_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async user model tests."""
        return self._setup_model(AsyncUser, scenario_name, "users")

    async def setup_async_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async type case model tests."""
        return self._setup_model(AsyncTypeCase, scenario_name, "type_cases")

    async def setup_async_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async type test model tests."""
        return self._setup_model(AsyncTypeTestModel, scenario_name, "type_tests")

    async def setup_async_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async validated field user model tests."""
        return self._setup_model(AsyncValidatedFieldUser, scenario_name, "validated_field_users")

    async def setup_async_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async validated user model tests."""
        return self._setup_model(AsyncValidatedUser, scenario_name, "validated_users")

    async def setup_async_mapped_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for AsyncMappedUser, AsyncMappedPost, and AsyncMappedComment models."""
        return self._setup_multiple_models([
            (AsyncMappedUser, "users"),
            (AsyncMappedPost, "posts"),
            (AsyncMappedComment, "comments")
        ], scenario_name)

    async def setup_async_mixed_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for AsyncColumnMappingModel and AsyncMixedAnnotationModel."""
        return self._setup_multiple_models([
            (AsyncColumnMappingModel, "column_mapping_items"),
            (AsyncMixedAnnotationModel, "mixed_annotation_items")
        ], scenario_name)

    async def setup_async_type_adapter_model_and_schema(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncTypeAdapterTest` model tests."""
        return self._setup_model(AsyncTypeAdapterTest, scenario_name, "type_adapter_tests")

    async def cleanup_after_test_async(self, scenario_name: str):
        """
        Performs async cleanup after a test, dropping all tables and disconnecting backends.
        """
        self.cleanup_after_test(scenario_name)

    def _load_mysql_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_mysql_test", "feature", "basic", "schema")
        schema_path = os.path.join(schema_dir, filename)

        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _backend_supports_json(self, backend) -> bool:
        """Check if the backend supports JSON capability."""
        try:
            return backend.capabilities.is_supported('json_operations')
        except Exception:
            try:
                version = backend.get_server_version()
                return version >= (5, 7, 8)
            except Exception:
                return False

    def _adjust_schema_for_json_support(self, schema_sql: str, backend) -> str:
        """Adjust schema SQL to replace JSON fields with LONGTEXT if JSON is not supported."""
        if self._backend_supports_json(backend):
            return schema_sql
        import re
        return re.sub(r'\bJSON\b', 'LONGTEXT', schema_sql, flags=re.IGNORECASE)

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
                except:
                    pass
        
        self._active_backends.clear()
