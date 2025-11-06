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
from typing import Type, List

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.testsuite.feature.basic.interfaces import IBasicProvider
# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


# The models are defined generically in the testsuite...


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

        # --- Start of modification: Track the created backend instance ---
        backend_instance = model_class.__backend__
        if backend_instance not in self._active_backends:
            self._active_backends.append(backend_instance)
        # --- End of modification ---

        # 3. Prepare the database schema. To ensure tests are isolated, we disable foreign key checks,
        #    drop the table if it exists, and recreate it from the schema file.
        try:
            # Disable foreign key checks temporarily to avoid constraint issues
            model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 0")
            # Drop the table if it exists
            model_class.__backend__.execute(f"DROP TABLE IF EXISTS `{table_name}`")
            # Re-enable foreign key checks
            model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 1")
        except Exception:
            # If there's an error, ensure foreign key checks are re-enabled
            try:
                model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 1")
            except:
                pass  # Ignore any errors when re-enabling foreign key checks
            # Continue anyway since the table might not exist

        # Check if this is a table that requires JSON support and if the backend supports it
        requires_json = table_name in ['type_tests', 'type_cases']
        if requires_json and not self._backend_supports_json(model_class.__backend__):
            # If the table requires JSON but the backend doesn't support it, modify the schema
            schema_sql = self._load_mysql_schema(f"{table_name}.sql")
            # Replace JSON type with LONGTEXT for MySQL versions that don't support JSON
            adjusted_schema_sql = self._adjust_schema_for_json_support(schema_sql, model_class.__backend__)
            model_class.__backend__.execute(adjusted_schema_sql)
        else:
            # Execute the original schema
            schema_sql = self._load_mysql_schema(f"{table_name}.sql")
            model_class.__backend__.execute(schema_sql)

        return model_class

    # --- Implementation of the IBasicProvider interface ---

    def setup_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for user model tests."""
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import User
        return self._setup_model(User, scenario_name, "users")

    def setup_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for type case model tests."""
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import TypeCase
        return self._setup_model(TypeCase, scenario_name, "type_cases")

    def setup_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for type test model tests."""
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import TypeTestModel
        return self._setup_model(TypeTestModel, scenario_name, "type_tests")

    def setup_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for validated field user model tests."""
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import ValidatedFieldUser
        return self._setup_model(ValidatedFieldUser, scenario_name, "validated_field_users")

    def setup_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for validated user model tests."""
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import ValidatedUser
        return self._setup_model(ValidatedUser, scenario_name, "validated_users")

    def _load_mysql_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        # Schemas are stored in the centralized location for basic feature.
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_mysql_test", "feature", "basic", "schema")
        schema_path = os.path.join(schema_dir, filename)

        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _backend_supports_json(self, backend) -> bool:
        """Check if the backend supports JSON capability."""
        try:
            # Get the backend's capabilities
            capabilities = backend.capabilities
            # Check if JSON operations are supported
            return capabilities.is_supported('json_operations')
        except Exception:
            # If there's an error checking capabilities, fall back to version check
            try:
                version = backend.get_server_version()
                # JSON support was introduced in MySQL 5.7.8
                return version >= (5, 7, 8)
            except Exception:
                # Default to not supporting JSON if we can't determine
                return False

    def _adjust_schema_for_json_support(self, schema_sql: str, backend) -> str:
        """Adjust schema SQL to replace JSON fields with LONGTEXT if JSON is not supported."""
        if self._backend_supports_json(backend):
            # If JSON is supported, return the original schema
            return schema_sql

        # Replace JSON data type with LONGTEXT for compatibility with older MySQL versions
        import re
        adjusted_schema = re.sub(r'\bJSON\b', 'LONGTEXT', schema_sql, flags=re.IGNORECASE)
        return adjusted_schema

    def cleanup_after_test(self, scenario_name: str):
        """
        Performs cleanup after a test. This now iterates through the backends
        that were created during setup, drops tables, and explicitly disconnects them.
        """
        for backend_instance in self._active_backends:
            try:
                # Drop all tables that might have been created for basic tests
                # Disable foreign key checks to avoid constraint issues during cleanup
                backend_instance.execute("SET FOREIGN_KEY_CHECKS = 0")
                for table_name in ['users', 'type_cases', 'type_tests', 'validated_field_users', 'validated_users']:
                    try:
                        backend_instance.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                    except Exception:
                        # Continue with other tables if one fails
                        pass
                # Re-enable foreign key checks
                backend_instance.execute("SET FOREIGN_KEY_CHECKS = 1")
            except Exception:
                # If there's an error, ensure foreign key checks are re-enabled
                try:
                    backend_instance.execute("SET FOREIGN_KEY_CHECKS = 1")
                except:
                    pass  # Ignore any errors when re-enabling foreign key checks
            finally:
                # Always disconnect the backend instance that was used in the test
                try:
                    backend_instance.disconnect()
                except:
                    # Ignore errors during disconnect
                    pass
        
        # Clear the list of active backends for the next test
        self._active_backends.clear()