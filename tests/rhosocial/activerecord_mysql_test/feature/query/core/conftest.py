# tests/rhosocial/activerecord_mysql_test/feature/query/core/conftest.py
from rhosocial.activerecord_mysql_test.feature.query.conftest import *  # noqa: F401,F403


# --- directory contract: keep this directory on one worker per scenario ---
def ensure_database(environment):
    return


def prepare(environment):
    return


def teardown(environment):
    return
