# tests/rhosocial/activerecord_mysql_test/feature/cli_contracts/conftest.py
"""Bridge the shared ``feature/cli`` contracts with a dedicated database.

The testsuite ``feature/cli`` conftest hardcodes the database name ``test_cli``.
A distinct directory must not reuse that name or it collides with the backend's
own ``feature/cli`` subsets under xdist; override it with a unique name here.
"""
from rhosocial.activerecord.testsuite.feature.cli.conftest import *  # noqa: F401,F403
import pytest


@pytest.fixture(scope="session")
def database_config(backend_scenario):
    name = "test_cli_contracts"
    return backend_scenario, backend_scenario.make_config(name), name
