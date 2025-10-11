"""
This file provides the concrete implementation of the `IMixinsProvider` interface
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
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.testsuite.feature.mixins.interfaces import IMixinsProvider
# The models are defined generically in the testsuite...

# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class MixinsProvider(IMixinsProvider):
    """
    This is the MySQL backend's implementation for the mixins features test group.
    It connects the generic tests in the testsuite with the actual MySQL database.
    """
    
    def __init__(self):
        # 可能需要跟踪某些资源进行清理
        self._scenario_resources = {}

    def get_test_scenarios(self) -> List[str]:
        """Returns a list of names for all enabled scenarios for this backend."""
        return list(get_enabled_scenarios().keys())

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given model."""
        # 1. Get the backend class (MySQLBackend) and connection config for the requested scenario.
        backend_class, config = get_scenario(scenario_name)

        # 2. Configure the generic model class with our specific backend and config.
        model_class.configure(config, backend_class)

        # 3. Prepare the database schema. To ensure tests are isolated, we drop
        #    the table if it exists and recreate it from the schema file.
        try:
            model_class.__backend__.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        except Exception:
            # Ignore errors if the table doesn't exist, which is expected on the first run.
            pass
            
        schema_sql = self._load_mysql_schema(f"{table_name}.sql")
        model_class.__backend__.execute(schema_sql)
        
        return model_class

    # --- Implementation of the IMixinsProvider interface ---

    def setup_timestamped_article_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for timestamped article model tests."""
        from rhosocial.activerecord.testsuite.feature.mixins.fixtures.models import TimestampedArticle
        models_and_tables = [
            (TimestampedArticle, "timestamped_articles"),
        ]
        
        result = []
        for model_class, table_name in models_and_tables:
            configured_model = self._setup_model(model_class, scenario_name, table_name)
            result.append(configured_model)
        
        return tuple(result)

    def setup_soft_deletable_article_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for soft deletable article model tests."""
        from rhosocial.activerecord.testsuite.feature.mixins.fixtures.models import SoftDeletableArticle
        models_and_tables = [
            (SoftDeletableArticle, "soft_deletable_articles"),
        ]
        
        result = []
        for model_class, table_name in models_and_tables:
            configured_model = self._setup_model(model_class, scenario_name, table_name)
            result.append(configured_model)
        
        return tuple(result)

    def setup_locked_article_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for locked article model tests."""
        from rhosocial.activerecord.testsuite.feature.mixins.fixtures.models import LockedArticle
        models_and_tables = [
            (LockedArticle, "locked_articles"),
        ]
        
        result = []
        for model_class, table_name in models_and_tables:
            configured_model = self._setup_model(model_class, scenario_name, table_name)
            result.append(configured_model)
        
        return tuple(result)

    def setup_combined_article_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for combined article model tests."""
        from rhosocial.activerecord.testsuite.feature.mixins.fixtures.models import CombinedArticle
        models_and_tables = [
            (CombinedArticle, "combined_articles"),
        ]
        
        result = []
        for model_class, table_name in models_and_tables:
            configured_model = self._setup_model(model_class, scenario_name, table_name)
            result.append(configured_model)
        
        return tuple(result)

    def _load_mysql_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        # Schemas are stored in the centralized location for mixins feature.
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_mysql_test", "feature", "mixins", "schema")
        schema_path = os.path.join(schema_dir, filename)
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()

    def cleanup_after_test(self, scenario_name: str):
        """
        Performs cleanup after a test. For MySQL, we ensure tables are dropped
        to maintain test isolation.
        """
        pass