# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/cli/test_introspect_routines_constraints_cli.py
"""The ``routines`` and ``constraints`` families, as the CLI asks for them.

No server is needed. The stub introspector records each call, so a branch that
reaches the wrong method or drops an argument fails here rather than looking
like a plausible listing; the live tests carry whether the answer itself is
right. The capability tests hold the constraint floor at 8.0.16, where
``CHECK_CONSTRAINTS`` arrived.
"""

import argparse
import json

import pytest

from rhosocial.activerecord.backend.impl.mysql.cli import introspect as introspect_cli
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.introspection.types import (
    MySQLConstraintInfo,
    MySQLRoutineInfo,
    MySQLRoutineParameter,
)

MYSQL_80_15 = (8, 0, 15)
MYSQL_80_16 = (8, 0, 16)
MYSQL_97 = (26, 7, 0)


class _RecordingIntrospector:
    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self.results.get(name)

        return call


class _AsyncRecordingIntrospector(_RecordingIntrospector):
    def __getattr__(self, name):
        async def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self.results.get(name)

        return call


def _args(type_, name=None, version=MYSQL_97, **overrides):
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


def _run_sync(monkeypatch, introspector, args, version=MYSQL_97):
    class _Backend:
        dialect = MySQLDialect(version=version)
        _connection = None

        def __init__(self, **_kwargs):
            self.introspector = introspector

        def connect(self):
            pass

        def introspect_and_adapt(self):
            self.dialect = MySQLDialect(version=version)

        def disconnect(self):
            pass

    monkeypatch.setattr(introspect_cli, "MySQLBackend", _Backend)
    monkeypatch.setattr(
        introspect_cli, "resolve_connection_config_from_args", lambda _args: None
    )
    introspect_cli.handle(args)


def _run_async(monkeypatch, introspector, args, version=MYSQL_97):
    class _Backend:
        dialect = MySQLDialect(version=version)
        _connection = None

        def __init__(self, **_kwargs):
            self.introspector = introspector

        async def connect(self):
            pass

        async def introspect_and_adapt(self):
            self.dialect = MySQLDialect(version=version)

        async def disconnect(self):
            pass

    monkeypatch.setattr(introspect_cli, "AsyncMySQLBackend", _Backend)
    monkeypatch.setattr(
        introspect_cli, "resolve_connection_config_from_args", lambda _args: None
    )
    args.is_async = True
    introspect_cli.handle(args)


def _routine() -> MySQLRoutineInfo:
    return MySQLRoutineInfo(
        schema="mydb",
        name="f",
        kind="FUNCTION",
        parameters=(MySQLRoutineParameter(1, mode="IN", name="a", data_type="int"),),
        return_type="int",
        is_deterministic=False,
        comment="comment",
    )


def _constraint() -> MySQLConstraintInfo:
    return MySQLConstraintInfo(
        schema="mydb",
        table_name="orders",
        name="ck_orders_total",
        constraint_type="CHECK",
        expression="(`total` > 0)",
        enforced=True,
    )


class TestTheRoutinesBranch:
    def test_a_name_is_asked_for_by_name(self, monkeypatch):
        introspector = _RecordingIntrospector({"get_routine_info": _routine()})

        _run_sync(monkeypatch, introspector, _args("routines", "f"))

        assert introspector.calls == [
            ("get_routine_info", ("f",), {"schema": None})
        ]

    def test_an_unnamed_run_lists_the_database(self, monkeypatch):
        introspector = _RecordingIntrospector({"list_routines": [_routine()]})

        _run_sync(monkeypatch, introspector, _args("routines"))

        assert introspector.calls == [("list_routines", (), {"schema": None})]

    def test_arguments_and_return_type_reach_json(self, monkeypatch, capsys):
        introspector = _RecordingIntrospector({"get_routine_info": _routine()})

        _run_sync(monkeypatch, introspector, _args("routines", "f"))

        payload = json.loads(capsys.readouterr().out)
        assert payload[0]["kind"] == "FUNCTION"
        assert payload[0]["return_type"] == "int"
        assert payload[0]["parameters"][0]["name"] == "a"

    def test_an_unknown_name_is_an_error(self, monkeypatch, capsys):
        introspector = _RecordingIntrospector({"get_routine_info": None})

        with pytest.raises(SystemExit) as excinfo:
            _run_sync(monkeypatch, introspector, _args("routines", "missing"))

        assert excinfo.value.code == 1
        assert "not found" in capsys.readouterr().err


class TestTheConstraintsBranch:
    def test_an_unnamed_run_lists_the_database(self, monkeypatch):
        introspector = _RecordingIntrospector({"list_constraints": [_constraint()]})

        _run_sync(monkeypatch, introspector, _args("constraints"))

        assert introspector.calls == [
            ("list_constraints", (None,), {"schema": None})
        ]

    def test_a_table_name_narrows_the_listing(self, monkeypatch):
        introspector = _RecordingIntrospector({"list_constraints": [_constraint()]})

        _run_sync(monkeypatch, introspector, _args("constraints", "orders"))

        assert introspector.calls == [
            ("list_constraints", ("orders",), {"schema": None})
        ]

    def test_type_expression_and_enforced_reach_json(self, monkeypatch, capsys):
        introspector = _RecordingIntrospector({"list_constraints": [_constraint()]})

        _run_sync(monkeypatch, introspector, _args("constraints", "orders"))

        payload = json.loads(capsys.readouterr().out)
        assert payload[0]["constraint_type"] == "CHECK"
        assert payload[0]["expression"] == "(`total` > 0)"
        assert payload[0]["enforced"] is True


class TestTheAsyncPath:
    def test_routines_ask_the_same_question(self, monkeypatch):
        introspector = _AsyncRecordingIntrospector({"get_routine_info": _routine()})

        _run_async(monkeypatch, introspector, _args("routines", "f"))

        assert introspector.calls == [
            ("get_routine_info", ("f",), {"schema": None})
        ]

    def test_constraints_ask_the_same_question(self, monkeypatch):
        introspector = _AsyncRecordingIntrospector(
            {"list_constraints": [_constraint()]}
        )

        _run_async(monkeypatch, introspector, _args("constraints", "orders"))

        assert introspector.calls == [
            ("list_constraints", ("orders",), {"schema": None})
        ]


class TestTheCapabilityGate:
    def test_routines_are_offered(self):
        assert introspect_cli._TYPE_CAPABILITIES["routines"] == (
            "supports_routine_introspection"
        )
        assert MySQLDialect(version=MYSQL_80_15).supports_routine_introspection() is True

    def test_constraints_are_refused_below_the_check_catalogue(self, capsys):
        class _Backend:
            dialect = MySQLDialect(version=MYSQL_80_15)

        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._require_capability(_args("constraints"), _Backend())

        assert excinfo.value.code == 2
        assert "not supported by this server" in capsys.readouterr().err

    def test_constraints_are_offered_from_the_floor(self):
        class _Backend:
            dialect = MySQLDialect(version=MYSQL_80_16)

        introspect_cli._require_capability(_args("constraints"), _Backend())

    @pytest.mark.parametrize("version", [MYSQL_80_15, (5, 7, 44)])
    def test_the_constraint_probe_refuses_older_servers(self, version):
        assert MySQLDialect(version=version).supports_constraint_introspection() is False

    def test_the_constraint_probe_follows_the_check_capability(self):
        dialect = MySQLDialect(version=MYSQL_80_16)
        assert dialect.supports_constraint_introspection() is (
            dialect.supports_check_constraint()
        )


class TestTheNameRules:
    def test_both_families_take_an_optional_name(self):
        assert introspect_cli._NAME_RULE["routines"] == "optional"
        assert introspect_cli._NAME_RULE["constraints"] == "optional"
        introspect_cli._validate_name(_args("routines"))
        introspect_cli._validate_name(_args("routines", "f"))
        introspect_cli._validate_name(_args("constraints"))
        introspect_cli._validate_name(_args("constraints", "orders"))
