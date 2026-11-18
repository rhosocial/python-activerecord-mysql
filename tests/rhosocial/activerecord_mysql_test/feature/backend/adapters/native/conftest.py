# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/native/conftest.py
"""L2 backend fixtures for the MySQL native-type tests.

- ``database``: one database per directory (session scope, emptied at start);
- ``schema``: only the tables this module declares in ``TABLES``, dropped and
  recreated for every test (function scope), so each test starts from empty
  tables;
- one fixture per model, each configured against this directory's database.

A module declares what it needs and nothing else: MySQL 5.6 has no ``JSON``
column, so a directory-wide "create every family" would abort a ``BIT`` test's
setup with a syntax error from a table it never touches.
"""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

from pathlib import Path

import pytest

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

from native_capabilities import supports_uuid_functions, uuid_functions_skip_reason
from native_models import (
    NativeBit,
    NativeBitDefinition,
    NativeGeometry,
    NativeGeometryDefinition,
    NativeJSON,
    NativeJsonDefinition,
    NativeSetEnum,
    NativeSetEnumDefinition,
    NativeUUID,
    NativeUuidDefinition,
    NativeVector,
    NativeVectorDefinition,
)

DECLARATION = Declaration(
    parallel=True,
    purpose="Live MySQL tests under adapters/native; this dir owns one DB per scenario.",
    passes_means="The backend behaves correctly under adapters/native on the active scenario.",
    fails_means="A live-server defect breaks MySQL adapters/native behaviour here.",
)

DDL = ExecutionOptions(stmt_type=StatementType.DDL)

#: Table name -> (definition, capability gate).  A gate of ``None`` means the
#: columns exist on every supported server; a gate that answers ``no`` skips
#: the module and names the probe in the reason.
FAMILIES = {
    "native_bit": (NativeBitDefinition, None),
    "native_set_enum": (NativeSetEnumDefinition, None),
    "native_json": (NativeJsonDefinition, "supports_json_type"),
    "native_uuid": (NativeUuidDefinition, None),
    "native_geometry": (NativeGeometryDefinition, None),
    "native_vector": (NativeVectorDefinition, "supports_vector_type"),
}


def _database_name() -> str:
    """Database name from this directory's namespace (below ``feature``)."""
    parts = Path(__file__).parent.parts
    start = parts.index("feature") + 1
    return "test_" + "_".join(parts[start:])


def _declared(request) -> tuple:
    """The families the module declares in ``TABLES``."""
    names = tuple(getattr(request.module, "TABLES", ()))
    unknown = [name for name in names if name not in FAMILIES]
    if unknown:
        raise LookupError(
            f"{request.module.__name__} declares unknown native families: {unknown}"
        )
    return names


@pytest.fixture(scope="session")
def database_config(backend_scenario):
    """The scenario, its connection configuration, and the directory database name."""
    name = _database_name()
    return backend_scenario, backend_scenario.make_config(name), name


@pytest.fixture(scope="session")
def database(database_config):
    """The directory's database, prepared once and left for later files."""
    scenario, config, name = database_config
    scenario.reset_database(name)
    backend = scenario.backend_class(connection_config=config)
    backend.connect()
    backend.introspect_and_adapt()
    yield backend
    backend.disconnect()


@pytest.fixture(scope="function", autouse=True)
def schema(database, request):
    """Drop and recreate only the tables this module declares, before every test."""
    fixtures = []
    for name in _declared(request):
        definition, probe = FAMILIES[name]
        if probe is not None and not getattr(database.dialect, probe)():
            pytest.skip(f"this server cannot hold a {name} column set ({probe} is False)")
        fixtures.append(definition(database.dialect))
    for fixture in fixtures:
        database.execute(*fixture.create_table.to_sql(), options=DDL)
    yield
    for fixture in reversed(fixtures):
        database.execute(*fixture.drop_table.to_sql(), options=DDL)


@pytest.fixture(name="native_bit")
def native_bit(database_config):
    """``NativeBit`` configured against this directory's database."""
    scenario, config, _name = database_config
    NativeBit.configure(config, scenario.backend_class)
    yield NativeBit
    NativeBit.backend().disconnect()


@pytest.fixture(name="native_set_enum")
def native_set_enum(database_config):
    """``NativeSetEnum`` configured against this directory's database."""
    scenario, config, _name = database_config
    NativeSetEnum.configure(config, scenario.backend_class)
    yield NativeSetEnum
    NativeSetEnum.backend().disconnect()


@pytest.fixture(name="native_json")
def native_json(database_config):
    """``NativeJSON`` configured against this directory's database."""
    scenario, config, _name = database_config
    NativeJSON.configure(config, scenario.backend_class)
    yield NativeJSON
    NativeJSON.backend().disconnect()


@pytest.fixture(name="native_uuid")
def native_uuid(database_config, database):
    """``NativeUUID``, skipped when the server has no ``BIN_TO_UUID``."""
    if not supports_uuid_functions(database):
        pytest.skip(uuid_functions_skip_reason(database))
    scenario, config, _name = database_config
    NativeUUID.configure(config, scenario.backend_class)
    yield NativeUUID
    NativeUUID.backend().disconnect()


@pytest.fixture(name="native_geometry")
def native_geometry(database_config):
    """``NativeGeometry`` configured against this directory's database."""
    scenario, config, _name = database_config
    NativeGeometry.configure(config, scenario.backend_class)
    yield NativeGeometry
    NativeGeometry.backend().disconnect()


@pytest.fixture(name="native_vector")
def native_vector(database_config, database):
    """``NativeVector``, skipped when the server has no ``VECTOR`` type."""
    if not database.dialect.supports_vector_type():
        pytest.skip(
            "this server cannot hold a native VECTOR column "
            "(supports_vector_type() -> False)"
        )
    scenario, config, _name = database_config
    NativeVector.configure(config, scenario.backend_class)
    yield NativeVector
    NativeVector.backend().disconnect()
