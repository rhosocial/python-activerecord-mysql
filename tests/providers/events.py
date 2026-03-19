"""
This file provides the concrete implementation of the `IEventsProvider` interface
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
import sys
import logging
from typing import Type, List

from rhosocial.activerecord.model import ActiveRecord

# Setup logging for fixture selection debugging
logger = logging.getLogger(__name__)

# Import the fixture selector utility
from rhosocial.activerecord.testsuite.utils import select_fixture

# Import base version models (Python 3.8+)
from rhosocial.activerecord.testsuite.feature.events.fixtures.models import (
    EventTestModel as EventTestModelBase,
    EventTrackingModel as EventTrackingModelBase
)

# Conditionally import Python 3.10+ models
EventTestModel310 = EventTrackingModel310 = None

if sys.version_info >= (3, 10):
    try:
        from rhosocial.activerecord.testsuite.feature.events.fixtures.models_py310 import (
            EventTestModel as EventTestModel310,
            EventTrackingModel as EventTrackingModel310
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.10+ fixtures: {e}")

# Conditionally import Python 3.11+ models
EventTestModel311 = EventTrackingModel311 = None

if sys.version_info >= (3, 11):
    try:
        from rhosocial.activerecord.testsuite.feature.events.fixtures.models_py311 import (
            EventTestModel as EventTestModel311,
            EventTrackingModel as EventTrackingModel311
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.11+ fixtures: {e}")

# Conditionally import Python 3.12+ models
EventTestModel312 = EventTrackingModel312 = None

if sys.version_info >= (3, 12):
    try:
        from rhosocial.activerecord.testsuite.feature.events.fixtures.models_py312 import (
            EventTestModel as EventTestModel312,
            EventTrackingModel as EventTrackingModel312
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.12+ fixtures: {e}")


# Select appropriate fixture classes based on Python version
def _select_model_class(base_cls, py312_cls, py311_cls, py310_cls, model_name: str) -> Type:
    """Select the most appropriate model class for the current Python version."""
    candidates = [c for c in [py312_cls, py311_cls, py310_cls, base_cls] if c is not None]
    selected = select_fixture(*candidates)
    logger.info(f"Selected {model_name}: {selected.__name__} from {selected.__module__}")
    return selected


# Select models
EventTestModel = _select_model_class(EventTestModelBase, EventTestModel312, EventTestModel311, EventTestModel310, "EventTestModel")
EventTrackingModel = _select_model_class(EventTrackingModelBase, EventTrackingModel312, EventTrackingModel311, EventTrackingModel310, "EventTrackingModel")

from rhosocial.activerecord.testsuite.feature.events.interfaces import IEventsProvider
# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class EventsProvider(IEventsProvider):
    """
    This is the MySQL backend's implementation for the events features test group.
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
            except Exception:
                pass  # Ignore any errors when re-enabling foreign key checks
            # Continue anyway since the table might not exist
        
        schema_sql = self._load_mysql_schema(f"{table_name}.sql")
        model_class.__backend__.execute(schema_sql)
        
        return model_class

    # --- Implementation of the IEventsProvider interface ---

    def setup_event_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the event model tests."""
        return self._setup_model(EventTestModel, scenario_name, "event_tests")

    def setup_event_tracking_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the event tracking model tests."""
        return self._setup_model(EventTrackingModel, scenario_name, "event_tracking_models")

    def _load_mysql_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        # Schemas are stored in the centralized location for events feature.
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_mysql_test", "feature", "events", "schema")
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
                # Drop all tables that might have been created for events tests
                # Disable foreign key checks to avoid constraint issues during cleanup
                backend_instance.execute("SET FOREIGN_KEY_CHECKS = 0")
                for table_name in ['event_tests', 'event_tracking_models']:
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
                except Exception:
                    pass  # Ignore any errors when re-enabling foreign key checks
            finally:
                # Always disconnect the backend instance that was used in the test
                try:
                    backend_instance.disconnect()
                except Exception:
                    # Ignore errors during disconnect
                    pass
        
        # Clear the list of active backends for the next test
        self._active_backends.clear()