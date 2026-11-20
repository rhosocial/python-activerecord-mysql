# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/mysql/set/conftest.py
"""No directory-specific fixtures: these tests use the backend-owned fixtures."""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration


DECLARATION = Declaration(
    uses_database=True,
    parallel=True,
    purpose="Live MySQL tests under execute/mysql/set; this dir owns one DB per scenario.",
    passes_means="The backend behaves correctly under execute/mysql/set on the active scenario.",
    fails_means="A live-server defect breaks MySQL execute/mysql/set behaviour here.",
)
