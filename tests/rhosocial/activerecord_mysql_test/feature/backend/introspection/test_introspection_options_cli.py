# tests/rhosocial/activerecord_mysql_test/feature/backend/introspection/test_introspection_options_cli.py
"""Tests for the ``table-options`` and ``partitions`` CLI subcommands.

The subcommands are exercised through ``main([...])`` rather than through
the handler directly, so argument parsing, backend construction, dispatch
to ``backend.introspector`` and rendering by the output provider are all
covered. JSON output is used because it is machine-checkable.
"""

import json

import pytest

from rhosocial.activerecord.backend.impl.mysql.__main__ import main
from rhosocial.activerecord.backend.impl.mysql.cli.introspect import INTROSPECT_TYPES

from mysql_live_server import mysql_server_available

pytestmark = pytest.mark.skipif(
    not mysql_server_available(),
    reason="No MySQL server reachable from the configured scenarios",
)

PARTITIONED_TABLE = "partitioned_events"


def _cli_args(backend, *rest) -> list:
    """Build CLI arguments that reach the same server as *backend*."""
    config = backend.config
    args = [
        "introspect",
        *rest,
        "--host",
        config.host,
        "--port",
        str(config.port),
        "--database",
        config.database,
        "--user",
        config.username,
        "--password",
        config.password or "",
        "--charset",
        config.charset or "utf8mb4",
    ]
    if getattr(config, "ssl_disabled", None):
        args.extend(["--ssl", "disabled"])
    return args + ["-o", "json"]


def _run(capsys, args) -> str:
    main(args)
    captured = capsys.readouterr()
    return captured.out


class TestIntrospectTypes:
    """The new families are offered by the parser."""

    def test_new_families_are_registered(self):
        assert "table-options" in INTROSPECT_TYPES
        assert "partitions" in INTROSPECT_TYPES


class TestTableOptionsCommand:
    """Tests for ``introspect table-options``."""

    def test_lists_all_tables(self, backend_with_tables, capsys):
        out = _run(capsys, _cli_args(backend_with_tables, "table-options"))

        payload = json.loads(out)
        assert payload
        names = {row["table_name"] for row in payload}
        assert "users" in names
        users = next(row for row in payload if row["table_name"] == "users")
        assert users["engine"] == "InnoDB"
        assert "data_length" in users

    def test_reports_one_table(self, backend_with_tables, capsys):
        out = _run(capsys, _cli_args(backend_with_tables, "table-options", "users"))

        payload = json.loads(out)
        assert len(payload) == 1
        assert payload[0]["table_name"] == "users"
        assert payload[0]["engine"] == "InnoDB"

    def test_unknown_table_exits_non_zero(self, backend_with_tables, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main(
                _cli_args(
                    backend_with_tables, "table-options", "table_options_does_not_exist"
                )
            )

        assert excinfo.value.code == 1
        assert "not found" in capsys.readouterr().err


class TestPartitionsCommand:
    """Tests for ``introspect partitions``."""

    def test_emits_partitions(self, backend_with_partitioned_table, capsys):
        out = _run(
            capsys,
            _cli_args(backend_with_partitioned_table, "partitions", PARTITIONED_TABLE),
        )

        payload = json.loads(out)
        assert len(payload) == 3
        assert [row["partition_name"] for row in payload] == ["p2020", "p2021", "p_max"]

    def test_requires_a_table_name(self, backend_with_tables, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main(_cli_args(backend_with_tables, "partitions"))

        assert excinfo.value.code == 2
        assert "required" in capsys.readouterr().err
