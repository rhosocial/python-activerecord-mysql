# tests/rhosocial/activerecord_mysql_test/feature/backend/conftest.py
import pytest
import pytest_asyncio
import yaml
import os
from typing import Dict, Any, Tuple, Type

from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, AsyncMySQLBackend, MySQLConnectionConfig

# --- Scenario Loading Logic ---

SCENARIO_MAP: Dict[str, Dict[str, Any]] = {}

def register_scenario(name: str, config: Dict[str, Any]):
    SCENARIO_MAP[name] = config

def _load_scenarios_from_config():
    """
    Load scenarios from a configuration file with the following priority:
    1. Environment variable specified path (highest priority)
    2. Default path tests/config/mysql_scenarios.yaml (lowest priority)
    If no valid configuration file is found, terminate with an error.
    """
    config_path = None
    env_config_path = os.getenv("MYSQL_SCENARIOS_CONFIG_PATH")

    if env_config_path and os.path.exists(env_config_path):
        print(f"Loading MySQL scenarios from environment-specified path: {env_config_path}")
        config_path = env_config_path
    else:
        default_path = os.path.join(os.path.dirname(__file__), "../../../../config", "mysql_scenarios.yaml")
        if os.path.exists(default_path):
            config_path = default_path
        elif env_config_path:
            # Path from env var was given but not found
            print(f"Warning: Scenario file specified in MYSQL_SCENARIOS_CONFIG_PATH not found: {env_config_path}")
            return

    if not config_path:
        raise FileNotFoundError(
            "No MySQL scenarios configuration file found. "
            "Either set MYSQL_SCENARIOS_CONFIG_PATH to a valid YAML file "
            "or place mysql_scenarios.yaml in the tests/config directory."
        )

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        if 'scenarios' not in config_data:
            raise ValueError(f"Configuration file {config_path} does not contain 'scenarios' key")

        for scenario_name, config in config_data['scenarios'].items():
            register_scenario(scenario_name, config)

    except ImportError:
        raise ImportError("PyYAML is required to load MySQL scenario configuration files")


_load_scenarios_from_config()

def get_scenario(name: str) -> Tuple[Type[MySQLBackend], MySQLConnectionConfig]:
    if name not in SCENARIO_MAP:
        if SCENARIO_MAP:
            name = next(iter(SCENARIO_MAP))
        else:
            raise ValueError("No scenarios registered")
    scenario_config = SCENARIO_MAP[name].copy()
    # Extract ssl_disabled if present, otherwise it will be None
    ssl_disabled = scenario_config.pop('ssl_disabled', None)
    config = MySQLConnectionConfig(**scenario_config)
    # Re-add ssl_disabled to config if it was present
    if ssl_disabled is not None:
        config.ssl_disabled = ssl_disabled
    return MySQLBackend, config

def get_enabled_scenarios() -> Dict[str, Any]:
    return SCENARIO_MAP

# --- Provider Logic ---

class BackendFeatureProvider:
    def __init__(self):
        self._backend = None
        self._async_backend = None

    def setup_backend(self, scenario_name: str):
        if self._backend:
            return self._backend
        backend_class, config = get_scenario(scenario_name)
        self._backend = backend_class(connection_config=config)
        self._backend.connect()
        self._backend.introspect_and_adapt()
        return self._backend

    async def setup_async_backend(self, scenario_name: str):
        if self._async_backend:
            return self._async_backend
        _, config = get_scenario(scenario_name)
        self._async_backend = AsyncMySQLBackend(connection_config=config)
        await self._async_backend.connect()
        await self._async_backend.introspect_and_adapt()
        return self._async_backend

    def cleanup(self):
        if self._backend:
            self._backend.disconnect()
            self._backend = None

    async def async_cleanup(self):
        if self._async_backend:
            await self._async_backend.disconnect()
            self._async_backend = None

# --- Fixtures ---

def get_scenario_names():
    return list(get_enabled_scenarios().keys())

@pytest.fixture(scope="function", params=get_scenario_names())
def mysql_backend(request):
    scenario_name = request.param
    provider = BackendFeatureProvider()
    backend = provider.setup_backend(scenario_name)
    yield backend
    provider.cleanup()


@pytest.fixture(scope="function")
def mysql_backend_single():
    """Non-parameterized fixture using the first available scenario."""
    scenario_names = get_scenario_names()
    if not scenario_names:
        pytest.skip("No MySQL scenarios configured")
    scenario_name = scenario_names[0]
    provider = BackendFeatureProvider()
    backend = provider.setup_backend(scenario_name)
    yield backend
    provider.cleanup()

@pytest_asyncio.fixture(scope="function", params=get_scenario_names())
async def async_mysql_backend(request):
    scenario_name = request.param
    provider = BackendFeatureProvider()
    backend = await provider.setup_async_backend(scenario_name)
    yield backend
    await provider.async_cleanup()


@pytest_asyncio.fixture(scope="function")
async def async_mysql_backend_single():
    """Non-parameterized async fixture using the first available scenario."""
    scenario_names = get_scenario_names()
    if not scenario_names:
        pytest.skip("No MySQL scenarios configured")
    scenario_name = scenario_names[0]
    provider = BackendFeatureProvider()
    backend = await provider.setup_async_backend(scenario_name)
    yield backend
    await provider.async_cleanup()


# --- Control Backend for Session Modification Tests ---

@pytest.fixture(scope="function")
def mysql_control_backend():
    """
    Dedicated control backend for tests that modify MySQL session settings.

    This fixture provides an independent backend instance for operations that
    need to control or interfere with the main test backend, such as:
    - KILL CONNECTION statements
    - Setting global variables
    - Monitoring other connections

    The fixture is NOT parameterized to ensure consistent behavior across
    all MySQL scenarios.
    """
    scenario_names = get_scenario_names()
    if not scenario_names:
        pytest.skip("No MySQL scenarios configured")
    scenario_name = scenario_names[0]
    provider = BackendFeatureProvider()
    backend = provider.setup_backend(scenario_name)
    yield backend
    provider.cleanup()


@pytest_asyncio.fixture(scope="function")
async def async_mysql_control_backend():
    """
    Dedicated async control backend for tests that modify MySQL session settings.

    This fixture provides an independent async backend instance for operations that
    need to control or interfere with the main test backend, such as:
    - KILL CONNECTION statements
    - Setting global variables
    - Monitoring other connections

    The fixture is NOT parameterized to ensure consistent behavior across
    all MySQL scenarios.
    """
    scenario_names = get_scenario_names()
    if not scenario_names:
        pytest.skip("No MySQL scenarios configured")
    scenario_name = scenario_names[0]
    provider = BackendFeatureProvider()
    backend = await provider.setup_async_backend(scenario_name)
    yield backend
    await provider.async_cleanup()


# --- Type Adapters ---

@pytest.fixture(scope="module")
def json_column_adapter():
    """
    Module-scoped fixture providing MySQLJSONAdapter instance.

    This adapter can be used with column_adapters parameter to automatically
    parse JSON columns returned as strings by mysql-connector-python.

    Usage:
        result = mysql_backend.execute(
            "SELECT data FROM table",
            column_adapters={'data': (json_column_adapter, dict)}
        )
    """
    from rhosocial.activerecord.backend.impl.mysql.adapters import MySQLJSONAdapter
    return MySQLJSONAdapter()


# --- Protocol Requirement Checking ---

@pytest.fixture(scope="function", autouse=True)
def check_protocol_requirements(request):
    """
    Auto-used fixture that checks if the current backend supports required protocols.

    This fixture runs automatically for each test and checks if the test has
    a 'requires_protocol' marker. If so, it verifies that the current backend
    supports the required protocols, skipping the test if not.

    Note: This fixture accesses the backend through request.getfixturevalue()
    to avoid parameterization conflicts.
    """
    requires_protocol_marker = request.node.get_closest_marker("requires_protocol")
    if requires_protocol_marker:
        required_protocol_info = requires_protocol_marker.args[0]

        # Check if we're running an async test
        is_async = 'async_mysql_backend' in request.fixturenames
        fixture_name = 'async_mysql_backend' if is_async else 'mysql_backend'

        if fixture_name in request.fixturenames:
            try:
                # Get the backend fixture
                backend = request.getfixturevalue(fixture_name)

                if backend is not None:
                    protocol_class, method_name = required_protocol_info

                    # Check if backend implements the protocol
                    if not isinstance(backend.dialect, protocol_class):
                        pytest.skip(
                            f"Skipping test - backend dialect does not implement {protocol_class.__name__} protocol"
                        )

                    # If a specific method name is provided, check if it's supported
                    if method_name:
                        if hasattr(backend.dialect, method_name):
                            method = getattr(backend.dialect, method_name)
                            if callable(method):
                                # For support checking methods that return bool
                                if method_name.startswith('supports_'):
                                    if not method():
                                        feature_name = method_name.replace('supports_', '')
                                        pytest.skip(
                                            f"Skipping test - backend dialect does not support {feature_name}"
                                        )
            except Exception:
                pass
