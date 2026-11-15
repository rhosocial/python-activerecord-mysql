# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/timestamps/test_implicit_first_timestamp.py
"""What an old server does to the table's first TIMESTAMP column, measured.

MySQL before 8.0.2 defaults ``explicit_defaults_for_timestamp`` to OFF. With
that setting the table's **first** TIMESTAMP column carries an implicit
``DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP``, so any UPDATE
rewrites it with the server's clock -- including an UPDATE that never mentions
it. This is a property of the server's configuration, not of the framework, and
the framework does not change it: the test states which setting is in force and
asserts the behaviour that follows, so a server behaving the other way is a
detected difference rather than a surprise.

``feature/basic/crud`` asserts the opposite ("a field an UPDATE never names
keeps its value"), which is why the repository's root conftest skips that
directory on the versions that behave this way.
"""

from datetime import datetime

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

DDL = ExecutionOptions(stmt_type=StatementType.DDL)
DML = ExecutionOptions(stmt_type=StatementType.DML)

SEED = datetime(2020, 1, 1, 0, 0, 1)

TABLE = "implicit_first_timestamp"


def _session_defaults_are_explicit(backend) -> bool:
    """Whether this session keeps TIMESTAMP columns to what was written."""
    row = backend.execute(
        "SELECT @@SESSION.explicit_defaults_for_timestamp AS v", ()
    ).data[0]
    return bool(int(row["v"]))


def _create(backend) -> None:
    backend.execute(f"DROP TABLE IF EXISTS {TABLE}", (), options=DDL)
    # ``first_ts`` is declared the way the suite declares its timestamps: bare,
    # with no NULL and no default. That is exactly the shape the old server
    # decorates implicitly; declaring NULL would suppress the automatic
    # DEFAULT / ON UPDATE and the measurement would prove nothing.
    backend.execute(
        f"CREATE TABLE {TABLE} ("
        " id INT NOT NULL PRIMARY KEY,"
        " first_ts TIMESTAMP,"
        " second_ts TIMESTAMP NULL)",
        (),
        options=DDL,
    )


def _drop(backend) -> None:
    backend.execute(f"DROP TABLE IF EXISTS {TABLE}", (), options=DDL)


def test_update_rewrites_the_first_timestamp_only_when_defaults_are_implicit(
    mysql_backend,
):
    explicit = mysql_backend.dialect.explicit_defaults_for_timestamp()
    assert explicit is _session_defaults_are_explicit(mysql_backend), (
        "the dialect must report the session's real value, not a guess from "
        "the version"
    )
    _create(mysql_backend)
    try:
        mysql_backend.execute(
            f"INSERT INTO {TABLE} (id, first_ts, second_ts) VALUES "
            f"(1, '2020-01-01 00:00:01', '2020-01-01 00:00:01')",
            (),
            options=DML,
        )
        # The statement touches the key and neither timestamp column.
        mysql_backend.execute(
            f"UPDATE {TABLE} SET id = 2 WHERE id = 1", (), options=DML
        )
        row = mysql_backend.execute(
            f"SELECT first_ts, second_ts FROM {TABLE} WHERE id = 2", ()
        ).data[0]
        assert row["second_ts"] == SEED, (
            "only the first TIMESTAMP column takes the implicit behaviour"
        )
        if explicit:
            assert row["first_ts"] == SEED, (
                "explicit_defaults_for_timestamp is ON: an UPDATE leaves a "
                "column it never names alone"
            )
        else:
            assert row["first_ts"] != SEED, (
                "explicit_defaults_for_timestamp is OFF: the first TIMESTAMP "
                "column is rewritten by the server on any UPDATE"
            )
    finally:
        _drop(mysql_backend)
