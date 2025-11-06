# tests/rhosocial/activerecord_test/feature/basic/conftest.py
"""
This file defines the pytest fixtures for the "basic" feature test group.

Fixtures are a core concept in pytest. They are functions that provide a fixed
baseline state or data for tests. In this case, they provide fully configured
ActiveRecord model classes that are ready to be used in tests.

The key mechanism here is `pytest.fixture` parameterization. The fixtures are
parameterized by the list of "scenarios" provided by the backend's provider.
This causes pytest to run each test that uses one of these fixtures multiple times,
once for each database configuration (scenario) the backend supports.
"""
import pytest
from rhosocial.activerecord.testsuite.core.registry import get_provider_registry

def get_scenarios():
    """
    A helper function that runs during pytest's collection phase to discover
    all available test scenarios from the backend's registered provider.
    """
    # Dynamically get the registry and the provider for this test group.
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider("feature.basic.IBasicProvider")
    if not provider_class:
        return []
    # Instantiate the provider and get the list of scenario names.
    return provider_class().get_test_scenarios()

# Discover the scenarios at module import time.
scenarios = get_scenarios()

# If no scenarios are found, create a single dummy parameter that will cause
# the tests to be skipped with a helpful message.
SCENARIO_PARAMS = scenarios if scenarios else [pytest.param("default", marks=pytest.mark.skip(reason="No testsuite scenarios found"))]

@pytest.fixture(scope="function", params=SCENARIO_PARAMS)
def user_class(request):
    """
    A pytest fixture that provides a configured `User` model class for testing.
    It is parameterized to run for each available scenario.
    It also handles the setup and teardown for each test.
    """
    # `request.param` holds the current scenario name (e.g., "memory", "file").
    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider("feature.basic.IBasicProvider")
    provider = provider_class()

    # Ask the provider to set up the database and configure the User model for this scenario.
    Model = provider.setup_user_model(scenario)

    # `yield` passes the configured model class to the test function.
    yield Model

    # After the test function finishes, the code below this line runs as a teardown.
    provider.cleanup_after_test(scenario)

@pytest.fixture(scope="function", params=SCENARIO_PARAMS)
def type_case_class(request):
    """
    Provides a configured `TypeCase` model class for each scenario."""
    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider("feature.basic.IBasicProvider")
    provider = provider_class()

    Model = provider.setup_type_case_model(scenario)
    yield Model
    provider.cleanup_after_test(scenario)

@pytest.fixture(scope="function", params=SCENARIO_PARAMS)
def type_test_model(request):
    """
    Provides a configured `TypeTestModel` model class for each scenario."""
    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider("feature.basic.IBasicProvider")
    provider = provider_class()

    Model = provider.setup_type_test_model(scenario)
    yield Model
    provider.cleanup_after_test(scenario)

@pytest.fixture(scope="function", params=SCENARIO_PARAMS)
def validated_user_class(request):
    """
    Provides a configured `ValidatedFieldUser` model class for each scenario."""
    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider("feature.basic.IBasicProvider")
    provider = provider_class()

    Model = provider.setup_validated_field_user_model(scenario)
    yield Model
    provider.cleanup_after_test(scenario)

@pytest.fixture(scope="function", params=SCENARIO_PARAMS)
def validated_user(request):
    """
    Provides a configured `ValidatedUser` model class for each scenario."""
    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider("feature.basic.IBasicProvider")
    provider = provider_class()

    Model = provider.setup_validated_user_model(scenario)
    yield Model
    provider.cleanup_after_test(scenario)