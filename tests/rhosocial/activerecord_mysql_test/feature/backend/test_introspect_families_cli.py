# tests/rhosocial/activerecord_mysql_test/feature/backend/test_introspect_families_cli.py
"""The nine families the dialect answers, as the CLI asks for them.

No server is needed here. What is checked is the wiring the CLI owns: that
each type reaches its introspector method, that NAME and the type-specific
flags arrive as arguments rather than being parsed and dropped, and that a
family the connected server refuses is refused. Whether the answer is right is
the introspector's question, and the live tests carry it.

The stub introspector records one call per run, so a branch that calls two
methods, or calls the right one with a dropped argument, fails here rather
than showing up as a plausible-looking listing.
"""

import argparse
import json
from typing import Optional

import pytest

from rhosocial.activerecord.backend.impl.mysql.cli import introspect as introspect_cli
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.introspection.types import (
    ColumnDataProfile,
    ColumnValueFrequency,
    DDLStatement,
    JoinCoverage,
)

#: The nine families this change wires, and the switch that gates each. The
#: dialect declares them, so a run against a real server passes the gate; the
#: refusal test below turns the switch off to prove the gate is still read.
NEW_FAMILIES = {
    "unused-indexes": "supports_unused_indexes_detection",
    "table-stats": "supports_table_stats",
    "runtime": "supports_runtime_stats",
    "index-stats": "supports_index_stats",
    "dependencies": "supports_object_dependencies",
    "ddl": "supports_ddl_extraction",
    "column-profiles": "supports_column_data_profile",
    "value-samples": "supports_column_value_sample",
    "join-coverage": "supports_join_coverage",
}

#: The four families that answer for the whole database and take no NAME.
WHOLE_DATABASE_FAMILIES = (
    "unused-indexes",
    "table-stats",
    "runtime",
    "index-stats",
)


class _RecordingIntrospector:
    """Records each introspection call, and returns what the test declared.

    ``__getattr__`` is the whole implementation: a test names the method once,
    in the assertion, and a branch that reaches a different one fails on the
    recorded name rather than on an attribute error that would hide the typo.
    """

    def __init__(self, results: Optional[dict] = None) -> None:
        self.results = results or {}
        self.calls = []

    def __getattr__(self, name: str):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self.results.get(name)

        return call


class _AsyncRecordingIntrospector(_RecordingIntrospector):
    """The async shape of the same recorder: methods are awaited, calls are not."""

    def __getattr__(self, name: str):
        async def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self.results.get(name)

        return call


def _args(type_: str, name: Optional[str] = None, **overrides) -> argparse.Namespace:
    """The attributes a parsed invocation carries, with sane defaults."""
    values = dict(
        output="json",
        rich_ascii=False,
        type=type_,
        name=name,
        database="mydb",
        is_async=False,
        named_connection=None,
        include_system=False,
        column=None,
        limit=None,
        left_table=None,
        left_column=None,
        right_table=None,
        right_column=None,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


def _run_sync(monkeypatch, introspector, args) -> None:
    class _Backend:
        dialect = MySQLDialect()
        _connection = None

        def __init__(self, **_kwargs) -> None:
            self.introspector = introspector

        def connect(self) -> None:
            pass

        def introspect_and_adapt(self) -> None:
            pass

        def disconnect(self) -> None:
            pass

    monkeypatch.setattr(introspect_cli, "MySQLBackend", _Backend)
    monkeypatch.setattr(
        introspect_cli, "resolve_connection_config_from_args", lambda _args: None
    )
    introspect_cli.handle(args)


def _run_async(monkeypatch, introspector, args) -> None:
    class _Backend:
        dialect = MySQLDialect()
        _connection = None

        def __init__(self, **_kwargs) -> None:
            self.introspector = introspector

        async def connect(self) -> None:
            pass

        async def introspect_and_adapt(self) -> None:
            pass

        async def disconnect(self) -> None:
            pass

    monkeypatch.setattr(introspect_cli, "AsyncMySQLBackend", _Backend)
    monkeypatch.setattr(
        introspect_cli, "resolve_connection_config_from_args", lambda _args: None
    )
    args.is_async = True
    introspect_cli.handle(args)


class TestTheSchemaWideFamilies:
    """The counters and listings describe the database, so NAME is refused."""

    @pytest.mark.parametrize(
        "type_, method",
        [
            ("unused-indexes", "list_unused_indexes"),
            ("table-stats", "list_table_usage_stats"),
            ("runtime", "list_runtime_metrics"),
            ("index-stats", "list_index_usage_stats"),
        ],
    )
    def test_the_family_asks_its_method_for_the_whole_schema(
        self, type_, method, monkeypatch
    ):
        introspector = _RecordingIntrospector({method: []})

        _run_sync(monkeypatch, introspector, _args(type_))

        assert introspector.calls == [(method, (), {"schema": None})]

    @pytest.mark.parametrize("type_", WHOLE_DATABASE_FAMILIES)
    def test_a_name_is_refused(self, type_, capsys):
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_name(_args(type_, "orders"))

        assert excinfo.value.code == 2
        assert "takes no name" in capsys.readouterr().err


class TestTheDependenciesBranch:
    """One optional NAME narrows the graph; omitting it asks for all of it."""

    def test_a_named_object_is_asked_for_by_name(self, monkeypatch):
        introspector = _RecordingIntrospector({"list_object_dependencies": []})

        _run_sync(monkeypatch, introspector, _args("dependencies", "posts"))

        assert introspector.calls == [
            ("list_object_dependencies", (), {"object_name": "posts", "schema": None})
        ]

    def test_an_unnamed_run_asks_for_the_whole_graph(self, monkeypatch):
        introspector = _RecordingIntrospector({"list_object_dependencies": []})

        _run_sync(monkeypatch, introspector, _args("dependencies"))

        assert introspector.calls == [
            ("list_object_dependencies", (), {"object_name": None, "schema": None})
        ]


class TestTheDdlBranch:
    """The schema object, not a name, is what a caller parses."""

    def _statement(self) -> DDLStatement:
        return DDLStatement(
            schema="mydb",
            object_type="TABLE",
            object_name="orders",
            ddl="CREATE TABLE `orders` (`id` int)",
            native=True,
        )

    def test_the_table_is_asked_for_by_name(self, monkeypatch):
        introspector = _RecordingIntrospector({"get_ddl_statement": self._statement()})

        _run_sync(monkeypatch, introspector, _args("ddl", "orders"))

        assert introspector.calls == [
            ("get_ddl_statement", ("orders",), {"schema": None})
        ]

    def test_the_engine_text_reaches_json_with_its_native_flag(
        self, monkeypatch, capsys
    ):
        introspector = _RecordingIntrospector({"get_ddl_statement": self._statement()})

        _run_sync(monkeypatch, introspector, _args("ddl", "orders"))

        payload = json.loads(capsys.readouterr().out)
        assert payload[0]["object_name"] == "orders"
        assert payload[0]["ddl"] == "CREATE TABLE `orders` (`id` int)"
        assert payload[0]["native"] is True

    def test_no_ddl_is_an_error_not_an_empty_listing(self, monkeypatch, capsys):
        introspector = _RecordingIntrospector({"get_ddl_statement": None})

        with pytest.raises(SystemExit) as excinfo:
            _run_sync(monkeypatch, introspector, _args("ddl", "orders"))

        assert excinfo.value.code == 1
        assert "not available" in capsys.readouterr().err


class TestTheColumnProfilesBranch:
    """The aggregate label must reach the reader; the numbers are not a catalogue."""

    def _profile(self) -> ColumnDataProfile:
        return ColumnDataProfile(
            schema="mydb",
            table_name="orders",
            column_name="status",
            null_fraction=0.0,
            distinct_count=3,
            row_count=120,
            source="aggregate",
        )

    def test_the_table_is_asked_for_by_name(self, monkeypatch, capsys):
        introspector = _RecordingIntrospector(
            {"list_column_data_profiles": [self._profile()]}
        )

        _run_sync(monkeypatch, introspector, _args("column-profiles", "orders"))

        assert introspector.calls == [
            ("list_column_data_profiles", ("orders",), {"schema": None})
        ]

    def test_the_run_says_the_numbers_are_aggregated(self, monkeypatch, capsys):
        """Exact and expensive, on stderr so the JSON on stdout stays parseable."""
        introspector = _RecordingIntrospector(
            {"list_column_data_profiles": [self._profile()]}
        )

        _run_sync(monkeypatch, introspector, _args("column-profiles", "orders"))

        captured = capsys.readouterr()
        assert "aggregate" in captured.err
        assert "full scan" in captured.err
        payload = json.loads(captured.out)
        assert payload[0]["source"] == "aggregate"

    def test_the_note_is_not_mistaken_for_a_result_row(self, monkeypatch, capsys):
        """The note belongs on stderr; a line on stdout would break every parser."""
        introspector = _RecordingIntrospector(
            {"list_column_data_profiles": [self._profile()]}
        )

        _run_sync(monkeypatch, introspector, _args("column-profiles", "orders"))

        out = capsys.readouterr().out
        assert out.lstrip().startswith("[")


class TestTheValueSamplesBranch:
    """A table and a column, and a limit that the introspector receives."""

    def test_the_table_column_and_limit_reach_the_introspector(self, monkeypatch):
        introspector = _RecordingIntrospector(
            {"sample_column_values": [ColumnValueFrequency(value="paid", count=7)]}
        )

        _run_sync(
            monkeypatch,
            introspector,
            _args("value-samples", "orders", column="status", limit=20),
        )

        assert introspector.calls == [
            (
                "sample_column_values",
                ("orders", "status"),
                {"limit": 20, "schema": None},
            )
        ]

    def test_the_limit_is_the_introspector_default_when_omitted(self, monkeypatch):
        introspector = _RecordingIntrospector({"sample_column_values": []})

        _run_sync(
            monkeypatch, introspector, _args("value-samples", "orders", column="status")
        )

        asserted_limit = introspector.calls[0][2]["limit"]
        assert asserted_limit == introspect_cli.DEFAULT_VALUE_SAMPLE_LIMIT

    def test_a_missing_column_is_an_incomplete_invocation(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_options(_args("value-samples", "orders"))

        assert excinfo.value.code == 1
        assert "--column" in capsys.readouterr().err


class TestTheJoinCoverageBranch:
    """Four names, both sides of the measurement, in the order they are asked."""

    def _coverage(self) -> JoinCoverage:
        return JoinCoverage(
            left_schema="mydb",
            left_table="orders",
            left_column="customer_id",
            right_schema="mydb",
            right_table="customers",
            right_column="id",
            left_coverage=1.0,
            right_coverage=0.75,
        )

    def test_the_four_names_reach_the_introspector(self, monkeypatch):
        introspector = _RecordingIntrospector(
            {"estimate_join_coverage": self._coverage()}
        )

        _run_sync(
            monkeypatch,
            introspector,
            _args(
                "join-coverage",
                left_table="orders",
                left_column="customer_id",
                right_table="customers",
                right_column="id",
            ),
        )

        assert introspector.calls == [
            (
                "estimate_join_coverage",
                ("orders", "customer_id", "customers", "id"),
                {"schema": None},
            )
        ]

    def test_both_fractions_are_reported(self, monkeypatch, capsys):
        introspector = _RecordingIntrospector(
            {"estimate_join_coverage": self._coverage()}
        )

        _run_sync(
            monkeypatch,
            introspector,
            _args(
                "join-coverage",
                left_table="orders",
                left_column="customer_id",
                right_table="customers",
                right_column="id",
            ),
        )

        payload = json.loads(capsys.readouterr().out)
        assert payload[0]["left_coverage"] == 1.0
        assert payload[0]["right_coverage"] == 0.75

    def test_missing_names_are_listed_together(self, capsys):
        """One run should name every absent flag, not the first one it met."""
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_options(
                _args(
                    "join-coverage",
                    left_table="orders",
                    right_table="customers",
                )
            )

        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "--left-column" in err
        assert "--right-column" in err

    def test_an_unmeasurable_pair_is_an_error(self, monkeypatch, capsys):
        """``None`` is "not measured", which is not a zero-overlap answer."""
        introspector = _RecordingIntrospector({"estimate_join_coverage": None})

        with pytest.raises(SystemExit) as excinfo:
            _run_sync(
                monkeypatch,
                introspector,
                _args(
                    "join-coverage",
                    left_table="orders",
                    left_column="customer_id",
                    right_table="customers",
                    right_column="id",
                ),
            )

        assert excinfo.value.code == 1
        assert "could not measure" in capsys.readouterr().err


class TestTheArgumentRules:
    def test_a_flag_the_type_does_not_read_is_refused(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_options(_args("tables", column="status"))

        assert excinfo.value.code == 2
        assert "takes no --column" in capsys.readouterr().err

    def test_a_required_name_is_required_for_the_new_families(self, capsys):
        for type_ in ("ddl", "column-profiles", "value-samples"):
            with pytest.raises(SystemExit) as excinfo:
                introspect_cli._validate_name(_args(type_))
            assert excinfo.value.code == 1
        assert "required" in capsys.readouterr().err


class TestTheCapabilityGate:
    @pytest.mark.parametrize("type_, switch", list(NEW_FAMILIES.items()))
    def test_a_family_the_server_refuses_exits_two(self, type_, switch, capsys):
        class _Dialect:
            pass

        setattr(_Dialect, switch, staticmethod(lambda: False))

        class _Backend:
            dialect = _Dialect()

        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._require_capability(_args(type_), _Backend())

        assert excinfo.value.code == 2
        assert "not supported by this server" in capsys.readouterr().err


class TestTheAsyncPath:
    """The second dispatch chain must ask the same question the first one does."""

    @pytest.mark.parametrize(
        "type_, method, args_kwargs, expected",
        [
            ("unused-indexes", "list_unused_indexes", {}, ((), {"schema": None})),
            (
                "column-profiles",
                "list_column_data_profiles",
                {"name": "orders"},
                (("orders",), {"schema": None}),
            ),
            (
                "value-samples",
                "sample_column_values",
                {"name": "orders", "column": "status", "limit": 5},
                (("orders", "status"), {"limit": 5, "schema": None}),
            ),
            (
                "join-coverage",
                "estimate_join_coverage",
                {
                    "left_table": "orders",
                    "left_column": "customer_id",
                    "right_table": "customers",
                    "right_column": "id",
                },
                (
                    ("orders", "customer_id", "customers", "id"),
                    {"schema": None},
                ),
            ),
        ],
    )
    def test_the_async_branch_calls_the_same_method_with_the_same_arguments(
        self, type_, method, args_kwargs, expected, monkeypatch
    ):
        introspector = _AsyncRecordingIntrospector({method: []})

        _run_async(monkeypatch, introspector, _args(type_, **args_kwargs))

        assert introspector.calls == [(method, expected[0], expected[1])]


class TestTheTypeSurfaceExtension:
    def test_each_new_family_has_a_switch_the_dialect_declares(self):
        for type_, switch in NEW_FAMILIES.items():
            assert introspect_cli._TYPE_CAPABILITIES[type_] == switch
            assert hasattr(MySQLDialect, switch)

