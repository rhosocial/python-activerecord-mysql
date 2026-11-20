# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/show_admin/conftest.py
"""No directory-specific fixtures: these tests use the backend-owned fixtures."""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration


DECLARATION = Declaration(
    uses_database=True,
    parallel=True,
    purpose="Live MySQL tests under execute/show_admin; this dir owns one DB per scenario.",
    passes_means="The backend behaves correctly under execute/show_admin on the active scenario.",
    fails_means="A live-server defect breaks MySQL execute/show_admin behaviour here.",
)
