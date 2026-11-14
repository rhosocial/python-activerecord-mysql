# tests/rhosocial/activerecord_mysql_test/feature/backend/conftest.py
"""Fixtures for the backend-owned tests.

The backend runs these against a real server. The scenario supplies the
connection parameters; the database name is derived from the directory that
owns the test, so two directories never share tables.
"""
import os
from typing import Any, Dict, Tuple, Type

import pytest
import pytest_asyncio

import support.mysql

from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.backend.async_backend import AsyncMySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

# --- Scenario Loading Logic ---

SCENARIO_MAP: Dict[str, Dict[str, Any]] = dict(support.mysql.SCENARIO_MAP)


def _apply_scenario_filter():
    """Filter SCENARIO_MAP based on the active scenarios env var.

    Keeps the backend-feature scenarios consistent with the scenarios active
    for the rest of the test run.
    """
    filter_str = os.getenv("MYSQL_ACTIVE_SCENARIOS") or os.getenv("TESTSUITE_ACTIVE_SCENARIOS")
    if not filter_str:
        return
    allowed = set(s.strip() for s in filter_str.split(",") if s.strip())
    if not allowed:
        return
    for name in [n for n in SCENARIO_MAP if n not in allowed]:
        del SCENARIO_MAP[name]


_apply_scenario_filter()


def get_enabled_scenarios() -> Dict[str, Any]:
    return SCENARIO_MAP


def get_scenario_names():
    return list(get_enabled_scenarios().keys())


_PREPARED_DATABASES = set()


def _database_for(request) -> str:
    """Derive the logical database the directory owning the test runs in."""
    parts = list(request.node.path.parts)
    try:
        index = max(i for i, part in enumerate(parts) if part == "backend")
        names = [part for part in parts[index + 1 : -1] if part]
        return "test_backend" + "".join("_" + name for name in names)
    except ValueError:
        if "feature" in parts:
            index = max(i for i, part in enumerate(parts) if part == "feature")
            names = [part for part in parts[index + 1 : -1] if part]
            return "test_" + "_".join(names) if names else "test_misc"
        return "test_backend"


def _prepare_database(scenario_name: str, database: str) -> None:
    """Create the directory's database once per scenario."""
    key = (scenario_name, database)
    if key in _PREPARED_DATABASES:
        return
    support.mysql.scenario(scenario_name).reset_database(database)
    _PREPARED_DATABASES.add(key)


def get_scenario(name: str, database: str = "test_backend") -> Tuple[Type[MySQLBackend], MySQLConnectionConfig]:
    if name not in SCENARIO_MAP:
        if SCENARIO_MAP:
            name = next(iter(SCENARIO_MAP))
        else:
            raise ValueError("No scenarios registered")
    _prepare_database(name, database)
    return MySQLBackend, support.mysql.scenario(name).make_config(database)


def pytest_collection_modifyitems(config, items):
    """Pin a backend directory's tests to one worker.

    These directories create and drop tables in the directory's own database,
    so two workers must never run tests from the same directory at once.
    """
    for item in items:
        parts = item.path.parts
        if "backend" not in parts:
            continue
        item.add_marker(pytest.mark.xdist_group("mysql-backend::" + str(item.path.parent)))


# --- Provider Logic ---


class BackendFeatureProvider:
    def __init__(self):
        self._backend = None
        self._async_backend = None

    def setup_backend(self, scenario_name: str, database: str):
        if self._backend:
            return self._backend
        backend_class, config = get_scenario(scenario_name, database)
        self._backend = backend_class(connection_config=config)
        self._backend.connect()
        self._backend.introspect_and_adapt()
        return self._backend

    async def setup_async_backend(self, scenario_name: str, database: str):
        if self._async_backend:
            return self._async_backend
        _, config = get_scenario(scenario_name, database)
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


@pytest.fixture(scope="function", params=get_scenario_names())
def mysql_backend(request):
    scenario_name = request.param
    provider = BackendFeatureProvider()
    backend = provider.setup_backend(scenario_name, _database_for(request))
    yield backend
    provider.cleanup()


@pytest.fixture(scope="function")
def mysql_backend_single(request):
    """Non-parameterized fixture using the first available scenario.

    Use this for tests whose results do not vary across database versions
    (e.g. Protocol conformance, Explain output format). These tests run
    once instead of 7 times, and are pinned to the first scenario's worker
    in --scenario-parallel mode.
    """
    scenario_names = get_scenario_names()
    if not scenario_names:
        pytest.skip("No MySQL scenarios configured")
    scenario_name = scenario_names[0]
    provider = BackendFeatureProvider()
    backend = provider.setup_backend(scenario_name, _database_for(request))
    yield backend
    provider.cleanup()


@pytest_asyncio.fixture(scope="function", params=get_scenario_names())
async def async_mysql_backend(request):
    scenario_name = request.param
    provider = BackendFeatureProvider()
    backend = await provider.setup_async_backend(scenario_name, _database_for(request))
    yield backend
    await provider.async_cleanup()


@pytest_asyncio.fixture(scope="function")
async def async_mysql_backend_single(request):
    """Non-parameterized async fixture using the first available scenario.

    Use this for tests whose results do not vary across database versions.
    See mysql_backend_single for rationale.
    """
    scenario_names = get_scenario_names()
    if not scenario_names:
        pytest.skip("No MySQL scenarios configured")
    scenario_name = scenario_names[0]
    provider = BackendFeatureProvider()
    backend = await provider.setup_async_backend(scenario_name, _database_for(request))
    yield backend
    await provider.async_cleanup()


# --- Control Backend for Session Modification Tests ---


@pytest.fixture(scope="function")
def mysql_control_backend(mysql_backend):
    """
    Dedicated control backend sharing the same connection config as mysql_backend.

    This fixture provides an independent backend instance for operations that
    need to control or interfere with the main test backend, such as:
    - KILL CONNECTION statements
    - Setting global variables
    - Monitoring other connections

    Automatically follows the same scenario parametrization as mysql_backend.
    """
    backend = MySQLBackend(connection_config=mysql_backend.config)
    backend.connect()
    backend.introspect_and_adapt()
    yield backend
    backend.disconnect()


@pytest.fixture(scope="function")
def mysql_control_backend_single(mysql_backend_single):
    """
    Non-parameterized control backend following mysql_backend_single.

    Must be used together with mysql_backend_single (or async_mysql_backend_single
    counterpart) so that KILL CONNECTION / SET GLOBAL operations target the same
    scenario the main backend is pinned to. Mixing a parameterized control backend
    with the single (first-scenario) backend makes KILL target a different server
    under multi-scenario runs.
    """
    backend = MySQLBackend(connection_config=mysql_backend_single.config)
    backend.connect()
    backend.introspect_and_adapt()
    yield backend
    backend.disconnect()


@pytest_asyncio.fixture(scope="function")
async def async_mysql_control_backend(async_mysql_backend):
    """
    Dedicated async control backend that connects to the same scenario as async_mysql_backend.

    This fixture provides an independent async backend instance for operations that
    need to control or interfere with the main test backend, such as:
    - KILL CONNECTION statements
    - Setting global variables
    - Monitoring other connections

    Automatically follows the same scenario parametrization as async_mysql_backend.
    """
    backend = AsyncMySQLBackend(connection_config=async_mysql_backend.config)
    await backend.connect()
    await backend.introspect_and_adapt()
    yield backend
    await backend.disconnect()


@pytest_asyncio.fixture(scope="function")
async def async_mysql_control_backend_single(async_mysql_backend_single):
    """
    Non-parameterized async control backend following async_mysql_backend_single.

    See mysql_control_backend_single for the rationale: it must stay on the same
    scenario as the pinned single backend.
    """
    backend = AsyncMySQLBackend(connection_config=async_mysql_backend_single.config)
    await backend.connect()
    await backend.introspect_and_adapt()
    yield backend
    await backend.disconnect()


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
        is_async = "async_mysql_backend" in request.fixturenames
        fixture_name = "async_mysql_backend" if is_async else "mysql_backend"

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
                                if method_name.startswith("supports_"):
                                    if not method():
                                        feature_name = method_name.replace("supports_", "")
                                        pytest.skip(f"Skipping test - backend dialect does not support {feature_name}")
            except Exception:
                pass


@pytest.fixture(scope="function")
def mysql_dialect():
    """Fixture providing MySQLDialect instance for testing transaction expressions."""
    from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

    dialect = MySQLDialect()
    dialect.version = (8, 0, 0)
    return dialect
