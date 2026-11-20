# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/cli/test_cli_live.py
"""Live CLI integration tests for the data commands.

The mock-based CLI tests under ``feature/backend/construct/cli`` prove that
each handler dispatches to the right backend call. They cannot prove the other
half: that a real server answers the generated statement and that the JSON the
caller parses is the shape the CLI promises. These tests close that half by
driving ``main([...])`` with the connection parameters of a live scenario and
reading stdout back as JSON.

Only the CLI's own output is captured -- the backend is never faked. The
``mysql_backend_single`` fixture owns the connection (and the decision not to
run when no scenario is configured), so these tests run on the first configured
scenario, once, rather than once per scenario.

The catalogues the introspection commands read need something to find, so a
local fixture creates one small table on that scenario's dedicated database
and drops it again afterwards.
"""

import json

import pytest

from rhosocial.activerecord.backend.impl.mysql.__main__ import main

PROBE_TABLE = "cli_live_probe"


def _cli_args(backend, *rest) -> list:
    """Build CLI arguments that reach the same server as *backend*."""
    config = backend.config
    args = [
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


def _run(capsys, args):
    """Run the CLI and return its stdout, which JSON output keeps clean."""
    main(args)
    return capsys.readouterr().out


@pytest.fixture
def probed_backend(mysql_backend_single):
    """The live scenario with one table the introspection commands can find."""
    backend = mysql_backend_single
    backend.executescript(
        f"DROP TABLE IF EXISTS {PROBE_TABLE}; "
        f"CREATE TABLE {PROBE_TABLE} ("
        "id INT AUTO_INCREMENT PRIMARY KEY, "
        "name VARCHAR(64) NOT NULL"
        ");"
    )
    backend.introspector.clear_cache()
    yield backend
    try:
        backend.introspector.clear_cache()
        backend.executescript(f"DROP TABLE IF EXISTS {PROBE_TABLE};")
    except Exception:
        pass


class TestInfoLiveCli:
    """``info`` reports the server it actually connected to."""

    def test_info_reports_a_live_connection(self, mysql_backend_single, capsys):
        payload = json.loads(_run(capsys, _cli_args(mysql_backend_single, "info")))

        assert isinstance(payload, dict)
        assert {"database", "features", "protocols"} <= set(payload)
        # ``info`` falls back to a default dialect when the connection fails.
        # Requiring ``connected`` is what makes this a live test rather than a
        # check of that fallback.
        assert payload["database"]["connected"] is True
        assert payload["database"]["type"] == "mysql"
        assert len(payload["database"]["version_tuple"]) >= 2
        assert payload["protocols"]


class TestQueryLiveCli:
    """``query`` returns the server's answer as a JSON record list."""

    def test_select_literal_returns_its_row(self, mysql_backend_single, capsys):
        payload = json.loads(
            _run(capsys, _cli_args(mysql_backend_single, "query", "SELECT 1 AS n"))
        )

        assert isinstance(payload, list)
        assert len(payload) == 1
        assert int(payload[0]["n"]) == 1


class TestIntrospectLiveCli:
    """``introspect`` answers from the server's own catalogue."""

    def test_tables_lists_the_probe_table(self, probed_backend, capsys):
        payload = json.loads(_run(capsys, _cli_args(probed_backend, "introspect", "tables")))

        assert isinstance(payload, list)
        assert payload
        names = [row["name"] for row in payload]
        assert PROBE_TABLE in names

    def test_columns_of_the_probe_table(self, probed_backend, capsys):
        payload = json.loads(
            _run(capsys, _cli_args(probed_backend, "introspect", "columns", PROBE_TABLE))
        )

        assert isinstance(payload, list)
        assert payload
        names = [row["name"] for row in payload]
        assert "id" in names
        assert "name" in names

    def test_database_reports_the_connected_database(self, probed_backend, capsys):
        payload = json.loads(_run(capsys, _cli_args(probed_backend, "introspect", "database")))

        assert isinstance(payload, list)
        assert payload
        assert payload[0]["name"] == probed_backend.config.database
        assert payload[0]["version"]


class TestStatusLiveCli:
    """``status`` reads live server variables and status counters."""

    def test_all_returns_the_server_overview(self, mysql_backend_single, capsys):
        payload = json.loads(_run(capsys, _cli_args(mysql_backend_single, "status", "all")))

        assert isinstance(payload, dict)
        assert payload["server_version"]
        assert isinstance(payload["configuration"], list)

    def test_config_returns_configuration_items(self, mysql_backend_single, capsys):
        payload = json.loads(_run(capsys, _cli_args(mysql_backend_single, "status", "config")))

        assert isinstance(payload, list)
        assert payload
        assert {"name", "value"} <= set(payload[0])
