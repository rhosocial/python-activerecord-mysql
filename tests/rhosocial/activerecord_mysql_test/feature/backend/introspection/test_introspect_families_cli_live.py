# tests/rhosocial/activerecord_mysql_test/feature/backend/test_introspect_families_cli_live.py
"""The nine new CLI types, answered by a real server.

The offline tests prove the branches call the right introspector method with
the right arguments. What only a server can say is whether the method itself
answers: a statement the engine rejects, or a parser reading a column the
catalogue never projected, would pass every offline test and still make the
type useless. Each test therefore asks for a small, arranged fact -- one
inserted row, one foreign key, one indexed lookup -- and reads it back through
the CLI's own JSON.

The two performance-schema families skip on a server where that collector is
off, because the capability is real but the data source is an install-time
option; an empty answer there is not a defect.

The unused-indexes family splits on whether the server has a ``sys`` schema
(5.7+): where it does, the answer is asserted; where it does not, the run is
asserted to refuse rather than to fail mid-query.

The tables come from ``backend_with_tables`` (users, posts, tags, post_tags,
with the posts -> users foreign key), so every test also exercises MySQL's
usual catalogue shapes rather than a table built only for this file.
"""

import json

import pytest

from rhosocial.activerecord.backend.impl.mysql.__main__ import main

from mysql_live_server import mysql_server_available

pytestmark = pytest.mark.skipif(
    not mysql_server_available(),
    reason="No MySQL server reachable from the configured scenarios",
)

#: The ``sys`` schema -- and with it ``sys.schema_unused_indexes`` -- arrived
#: with MySQL 5.7. A probe answering ``True`` below that floor would be a
#: promise a 5.6 server cannot keep, so the scenario is split there rather
#: than demanded of every server.
UNUSED_INDEXES_FLOOR = (5, 7, 0)


def _server_has_sys_schema(backend) -> bool:
    """Whether this server carries the schema the family reads.

    Asked of the server rather than of the version number, because that is
    what the family actually depends on and the two could in principle
    disagree on a server somebody hand-built. The column is aliased to a
    name that is not a keyword, because ``SCHEMAS`` is one.
    """
    row = backend.execute(
        "SELECT COUNT(*) AS sys_present FROM information_schema.schemata "
        "WHERE schema_name = 'sys'"
    ).data[0]
    return int(row["sys_present"]) != 0


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


def _run_with_stderr(capsys, args):
    main(args)
    return capsys.readouterr()


def _performance_schema_enabled(backend) -> bool:
    row = backend.execute("SELECT @@performance_schema AS enabled").data[0]
    return int(row["enabled"]) != 0


def _require_performance_schema(backend) -> None:
    if not _performance_schema_enabled(backend):
        pytest.skip("performance_schema is disabled on this server")


def _insert_users(backend, names) -> list:
    """Insert *names* with unique emails, returning their ids."""
    ids = []
    for index, name in enumerate(names):
        backend.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            (name, f"cli_families_{name}_{index}@example.com"),
        )
        ids.append(backend.execute("SELECT LAST_INSERT_ID() AS id").data[0]["id"])
    return ids


class TestUnusedIndexesCommand:
    """``sys.schema_unused_indexes`` reached through the CLI.

    The family is only answerable where the ``sys`` schema exists, which is a
    5.7+ fact: before that the view is absent and the probe is honest about
    it. So the scenario is split at the schema rather than demanded of every
    server -- one half proves the answer arrives, the other half proves the
    run refuses cleanly instead of failing mid-execution. That second half is
    the regression: the CLI was the first caller to reach the family against
    5.6, and what it found there was a ``1146`` from the engine.
    """

    def test_an_index_a_full_scan_never_touched_is_reported(
        self, backend_with_tables, capsys
    ):
        """``SELECT *`` uses no secondary index, so the two remain unused.

        A miss here is also legal (the view covers what the collector
        instruments), but a row the view *does* report must arrive with its
        address intact -- that is what the CLI adds to the introspector.
        """
        if not _server_has_sys_schema(backend_with_tables):
            pytest.skip(
                f"this server has no sys schema (unused-indexes is a "
                f"{'.'.join(str(p) for p in UNUSED_INDEXES_FLOOR)}+ family)"
            )

        backend_with_tables.execute("SELECT * FROM users")

        payload = json.loads(_run(capsys, _cli_args(backend_with_tables, "unused-indexes")))

        assert isinstance(payload, list)
        for row in payload:
            assert {"table_name", "index_name"} <= set(row)
        reported = {row["index_name"] for row in payload if row["table_name"] == "users"}
        assert reported <= {"idx_users_email", "idx_users_name_age"}

    def test_a_server_without_the_sys_schema_is_refused_not_errored_on(
        self, backend_with_tables, capsys
    ):
        """The refusal is the probe saying "cannot answer", not a 1146.

        Below 5.7 the view does not exist, so rendering the query and running
        it would hand back an ``ProgrammingError`` the CLI reports as a generic
        "Error during introspection". What the caller needs is the capability
        answer, which is what exit 2 with "not supported by this server" says.
        """
        if _server_has_sys_schema(backend_with_tables):
            pytest.skip("this server answers the family; nothing to refuse")

        with pytest.raises(SystemExit) as excinfo:
            _run(capsys, _cli_args(backend_with_tables, "unused-indexes"))

        assert excinfo.value.code == 2
        assert "not supported by this server" in capsys.readouterr().err


class TestTableStatsCommand:
    def test_a_touched_table_arrives_with_its_counters(
        self, backend_with_tables, capsys
    ):
        _require_performance_schema(backend_with_tables)
        backend_with_tables.execute("SELECT COUNT(*) FROM users")

        payload = json.loads(_run(capsys, _cli_args(backend_with_tables, "table-stats")))

        rows = [row for row in payload if row["table_name"] == "users"]
        assert rows, "the table that was just read is missing from the counters"
        assert "count_read" in rows[0]["extra"]


class TestRuntimeCommand:
    def test_the_enabled_instruments_are_listed(self, backend_with_tables, capsys):
        _require_performance_schema(backend_with_tables)

        payload = json.loads(_run(capsys, _cli_args(backend_with_tables, "runtime")))

        assert payload
        assert {"name", "value"} <= set(payload[0])


class TestIndexStatsCommand:
    def test_the_secondary_index_used_by_the_lookup_is_listed(
        self, backend_with_tables, capsys
    ):
        _require_performance_schema(backend_with_tables)
        backend_with_tables.execute(
            "SELECT id FROM users WHERE email = %s", ("nobody@example.com",)
        )

        payload = json.loads(_run(capsys, _cli_args(backend_with_tables, "index-stats")))

        indexes = {
            row["index_name"] for row in payload if row["table_name"] == "users"
        }
        assert "idx_users_email" in indexes


class TestDependenciesCommand:
    def test_the_foreign_key_is_one_edge_of_the_graph(
        self, backend_with_tables, capsys
    ):
        payload = json.loads(
            _run(capsys, _cli_args(backend_with_tables, "dependencies", "posts"))
        )

        edges = [
            row
            for row in payload
            if row["dependent"] == "posts" and row["referenced"] == "users"
        ]
        assert edges
        assert edges[0]["action"].upper() == "CASCADE"


class TestDdlCommand:
    def test_the_engine_returns_its_own_create_statement(
        self, backend_with_tables, capsys
    ):
        payload = json.loads(_run(capsys, _cli_args(backend_with_tables, "ddl", "users")))

        assert len(payload) == 1
        assert payload[0]["native"] is True
        assert payload[0]["object_type"] == "TABLE"
        assert payload[0]["ddl"].lstrip().upper().startswith("CREATE TABLE")


class TestColumnProfilesCommand:
    def test_the_counts_are_aggregated_and_say_so(self, backend_with_tables, capsys):
        _insert_users(backend_with_tables, ["alice", "alice", "bob"])

        captured = _run_with_stderr(
            capsys, _cli_args(backend_with_tables, "column-profiles", "users")
        )

        payload = json.loads(captured.out)
        name = next(row for row in payload if row["column_name"] == "name")
        assert name["row_count"] == 3
        assert name["source"] == "aggregate"
        # The label is not only in the row: the run says it is exact and paid
        # for with a scan, on stderr so the JSON above stays parseable.
        assert "aggregate" in captured.err
        assert "full scan" in captured.err


class TestValueSamplesCommand:
    def test_the_repeated_value_is_listed_first(self, backend_with_tables, capsys):
        _insert_users(backend_with_tables, ["alice", "alice", "bob"])

        payload = json.loads(
            _run(
                capsys,
                _cli_args(
                    backend_with_tables, "value-samples", "users", "--column", "name"
                ),
            )
        )

        assert payload[0]["value"] == "alice"
        assert payload[0]["count"] == 2


class TestJoinCoverageCommand:
    def test_both_sides_of_the_measurement_are_reported(
        self, backend_with_tables, capsys
    ):
        """Two users, one post: every post value is a user, half are not used."""
        user_ids = _insert_users(backend_with_tables, ["alice", "bob"])
        backend_with_tables.execute(
            "INSERT INTO posts (title, user_id) VALUES (%s, %s)",
            ("first", user_ids[0]),
        )

        payload = json.loads(
            _run(
                capsys,
                _cli_args(
                    backend_with_tables,
                    "join-coverage",
                    "--left-table",
                    "posts",
                    "--left-column",
                    "user_id",
                    "--right-table",
                    "users",
                    "--right-column",
                    "id",
                ),
            )
        )

        assert payload[0]["left_coverage"] == pytest.approx(1.0)
        assert payload[0]["right_coverage"] == pytest.approx(0.5)
