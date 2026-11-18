# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/cli/conftest.py
"""No directory-specific fixtures: these tests use the backend-owned fixtures."""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration


DECLARATION = Declaration(
    parallel=True,
    purpose="Live MySQL tests under execute/cli; this dir owns one DB per scenario.",
    passes_means="The backend behaves correctly under execute/cli on the active scenario.",
    fails_means="A live-server defect breaks MySQL execute/cli behaviour here.",
)
