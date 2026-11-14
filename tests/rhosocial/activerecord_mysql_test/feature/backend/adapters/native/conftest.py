# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/native/conftest.py
"""L2 backend fixtures for the MySQL native-type tests.

- ``database``: one database per directory (session scope, emptied at start);
- ``schema``: the native family tables, plus the ``VECTOR`` table only when the
  scenario's server reports the type, dropped and recreated for every test
  (function scope), so each test starts from empty tables;
- one fixture per model, each configured against this directory's database.
"""

from pathlib import Path

import pytest

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

from native_capabilities import supports_vector, vector_skip_reason
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

DDL = ExecutionOptions(stmt_type=StatementType.DDL)

DEFINITIONS = (
    NativeBitDefinition,
    NativeSetEnumDefinition,
    NativeJsonDefinition,
    NativeUuidDefinition,
    NativeGeometryDefinition,
)


def _database_name() -> str:
    """Database name from this directory's namespace (below ``feature``)."""
    parts = Path(__file__).parent.parts
    start = parts.index("feature") + 1
    return "test_" + "_".join(parts[start:])


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
def schema(database):
    """Drop and recreate the native tables this directory uses, before every test."""
    fixtures = [definition(database.dialect) for definition in DEFINITIONS]
    if supports_vector(database):
        fixtures.append(NativeVectorDefinition(database.dialect))
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
def native_uuid(database_config):
    """``NativeUUID`` configured against this directory's database."""
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
    if not supports_vector(database):
        pytest.skip(vector_skip_reason(database))
    scenario, config, _name = database_config
    NativeVector.configure(config, scenario.backend_class)
    yield NativeVector
    NativeVector.backend().disconnect()
