# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/sequence_identity/conftest.py
"""No directory-specific fixtures: these tests use the backend-owned fixtures."""

from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    parallel=True,
    purpose="Live MySQL tests under execute/sequence_identity; this dir owns one DB per scenario.",
    passes_means="The backend behaves correctly under execute/sequence_identity on the active scenario.",
    fails_means="A live-server defect breaks MySQL execute/sequence_identity behaviour here.",
)
