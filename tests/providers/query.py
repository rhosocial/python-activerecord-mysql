"""
This file provides the concrete implementation of the `IQueryProvider` interface
that is defined in the `rhosocial-activerecord-testsuite` package.

Its main responsibilities are:
1.  Reporting which test scenarios (database configurations) are available.
2.  Setting up the database environment for a given test. This includes:
    - Getting the correct database configuration for the scenario.
    - Configuring the ActiveRecord model with a database connection.
    - Dropping any old tables and creating the necessary table schema.
3.  Cleaning up any resources (like temporary database files) after a test runs.
"""
import os
from typing import Type, List, Tuple
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.testsuite.feature.query.interfaces import IQueryProvider
# The models are defined generically in the testsuite...
from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Order, OrderItem, Post, Comment, MappedUser, MappedPost, MappedComment
from rhosocial.activerecord.testsuite.feature.query.fixtures.cte_models import Node
from rhosocial.activerecord.testsuite.feature.query.fixtures.extended_models import ExtendedOrder, ExtendedOrderItem
# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class QueryProvider(IQueryProvider):
    """
    This is the MySQL backend's implementation for the query features test group.
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
        
        schema_sql = self._load_mysql_schema(f"{table_name}.sql")
        model_class.__backend__.execute(schema_sql)
        
        return model_class

    def _setup_multiple_models(self, model_classes: List[Tuple[Type[ActiveRecord], str]], scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Helper to set up multiple related models for a test."""
        result = []
        for model_class, table_name in model_classes:
            configured_model = self._setup_model(model_class, scenario_name, table_name)
            result.append(configured_model)
        return tuple(result)

    # --- Implementation of the IQueryProvider interface ---

    def setup_order_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for the order-related models (User, Order, OrderItem) tests."""
        return self._setup_multiple_models([
            (User, "users"),
            (Order, "orders"),
            (OrderItem, "order_items")
        ], scenario_name)

    def setup_blog_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for the blog-related models (User, Post, Comment) tests."""
        return self._setup_multiple_models([
            (User, "users"),
            (Post, "posts"),
            (Comment, "comments")
        ], scenario_name)

    def setup_json_user_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for the JSON user model tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import JsonUser
        json_user_model = self._setup_model(JsonUser, scenario_name, "json_users")
        return (json_user_model,)

    def setup_tree_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for the tree model (Node) tests."""
        node_model = self._setup_model(Node, scenario_name, "nodes")
        return (node_model,)

    def setup_extended_order_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for the extended order-related models (User, ExtendedOrder, ExtendedOrderItem) tests."""
        return self._setup_multiple_models([
            (User, "users"),
            (ExtendedOrder, "extended_orders"),
            (ExtendedOrderItem, "extended_order_items")
        ], scenario_name)

    def setup_combined_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for the combined models (User, Order, OrderItem, Post, Comment) tests."""
        return self._setup_multiple_models([
            (User, "users"),
            (Order, "orders"),
            (OrderItem, "order_items"),
            (Post, "posts"),
            (Comment, "comments")
        ], scenario_name)

    def setup_annotated_query_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for the SearchableItem model tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.annotated_adapter_models import SearchableItem
        return self._setup_multiple_models([
            (SearchableItem, "searchable_items"),
        ], scenario_name)

    def setup_mapped_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for MappedUser, MappedPost, and MappedComment models."""
        return self._setup_multiple_models([
            (MappedUser, "users"),
            (MappedPost, "posts"),
            (MappedComment, "comments")
        ], scenario_name)

    def _load_mysql_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        # Schemas are stored in the centralized location for query feature.
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_mysql_test", "feature", "query", "schema")
        schema_path = os.path.join(schema_dir, filename)
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()

    def cleanup_after_test(self, scenario_name: str):
        """
        Performs cleanup after a test. This now iterates through the backends
        that were created during setup, drops tables, and explicitly disconnects them.
        """
        for backend_instance in self._active_backends:
            try:
                # Drop all tables that might have been created for query tests
                # Disable foreign key checks to avoid constraint issues during cleanup
                backend_instance.execute("SET FOREIGN_KEY_CHECKS = 0")
                for table_name in ['users', 'orders', 'order_items', 'posts', 'comments', 'json_users', 'nodes', 'extended_orders', 'extended_order_items', 'searchable_items']:
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