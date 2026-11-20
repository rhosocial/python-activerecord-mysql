# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/errors/test_driver_error_mapping.py
"""MySQL driver exceptions map to semantic error categories."""

import pytest

mysql_errors = pytest.importorskip("mysql.connector.errors")

from rhosocial.activerecord.backend.errors import (  # noqa: E402
    DataError,
    DatabaseError,
    DeadlockError,
    IntegrityError,
    LockError,
    OperationalError,
    QueryError,
)

from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend  # noqa: E402


@pytest.fixture
def backend():
    return MySQLBackend(host="localhost", database="db", user="u", password="p")


def _translated(backend, error):
    with pytest.raises(DatabaseError) as info:
        backend._handle_error(error)
    return info.value


def test_duplicate_key_maps_to_integrity(backend):
    error = mysql_errors.IntegrityError(msg="Duplicate entry 'a' for key 'uniq'", errno=1062)
    translated = _translated(backend, error)
    assert isinstance(translated, IntegrityError)
    assert isinstance(translated, DataError)
    assert translated.driver_code == 1062
    assert translated.backend == "mysql"
    assert translated.retryable is False


def test_foreign_key_maps_to_integrity(backend):
    error = mysql_errors.IntegrityError(
        msg="Cannot add or update a child row: a foreign key constraint fails", errno=1452
    )
    translated = _translated(backend, error)
    assert isinstance(translated, IntegrityError)
    assert translated.driver_code == 1452


def test_deadlock_maps_to_deadlock_error(backend):
    error = mysql_errors.OperationalError(msg="Deadlock found when trying to get lock", errno=1213)
    translated = _translated(backend, error)
    assert isinstance(translated, DeadlockError)
    assert isinstance(translated, LockError)
    assert translated.retryable is True
    assert translated.transient is True


def test_lock_wait_timeout_maps_to_lock_error(backend):
    error = mysql_errors.OperationalError(msg="Lock wait timeout exceeded", errno=1205)
    translated = _translated(backend, error)
    assert isinstance(translated, LockError)
    assert not isinstance(translated, DeadlockError)
    assert translated.retryable is True


def test_lost_connection_is_transient(backend):
    error = mysql_errors.OperationalError(msg="Lost connection to MySQL server", errno=2013)
    translated = _translated(backend, error)
    assert isinstance(translated, OperationalError)
    assert translated.transient is True
    assert translated.retryable is True


def test_read_only_server_is_not_retryable(backend):
    error = mysql_errors.DatabaseError(
        msg="The MySQL server is running with the --read-only option", errno=1290
    )
    translated = _translated(backend, error)
    assert isinstance(translated, OperationalError)
    assert translated.sqlstate == "HY000"
    assert translated.transient is False
    assert translated.retryable is False


def test_syntax_error_maps_to_query_error(backend):
    error = mysql_errors.ProgrammingError(msg="You have an error in your SQL syntax", errno=1064)
    translated = _translated(backend, error)
    assert isinstance(translated, QueryError)
    assert translated.driver_code == 1064


def test_unknown_database_error_falls_back(backend):
    error = mysql_errors.DatabaseError(msg="No database selected", errno=1046)
    translated = _translated(backend, error)
    assert isinstance(translated, DatabaseError)
    assert not isinstance(translated, (IntegrityError, QueryError, LockError))
