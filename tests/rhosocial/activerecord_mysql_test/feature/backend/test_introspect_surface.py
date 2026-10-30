# tests/rhosocial/activerecord_mysql_test/feature/backend/test_introspect_surface.py
"""The introspect type surface: what the command offers, and what NAME means.

No server is needed here. These tests cover the layer that drifted before: a
family can be offered by the parser while no branch answers it, and a NAME can
be accepted by the parser while no code uses it. Both are invisible to a
test that only talks to a live server, because the failure looks like an empty
answer rather than an error.
"""

import argparse
import inspect
from typing import Optional

import pytest

from rhosocial.activerecord.backend.impl.mysql.cli import introspect as introspect_cli
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


class _Args:
    """The two attributes the rules look at, and nothing else."""

    def __init__(self, type_: str, name: Optional[str] = None) -> None:
        self.type = type_
        self.name = name


class TestTheTypeSurface:
    def test_the_type_list_is_the_capability_table(self):
        assert list(introspect_cli._TYPE_CAPABILITIES) == introspect_cli.INTROSPECT_TYPES

    def test_no_removed_aggregate_is_offered(self):
        assert "table" not in introspect_cli.INTROSPECT_TYPES

    def test_every_switch_exists_on_the_dialect(self):
        for name, switch in introspect_cli._TYPE_CAPABILITIES.items():
            assert hasattr(MySQLDialect, switch), f"{name} names a switch that does not exist"

    def test_every_name_rule_covers_a_declared_type(self):
        assert set(introspect_cli._NAME_RULE) == set(introspect_cli.INTROSPECT_TYPES)

    def test_help_lists_every_type(self, capsys):
        parser = introspect_cli.create_parser(argparse.ArgumentParser().add_subparsers())
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])
        out = capsys.readouterr().out
        for name in introspect_cli.INTROSPECT_TYPES:
            assert name in out

    def test_every_type_has_a_branch_in_both_paths(self):
        """A type with no branch prints nothing and exits 0 -- the worst shape."""
        sync_source = inspect.getsource(introspect_cli._handle_introspect_sync)
        async_source = inspect.getsource(introspect_cli._handle_introspect_async)
        for name in introspect_cli.INTROSPECT_TYPES:
            assert f'args.type == "{name}"' in sync_source, name
            assert f'args.type == "{name}"' in async_source, name


class TestTheNameRule:
    @pytest.mark.parametrize("type_", ["tables", "database"])
    def test_a_name_the_type_answers_whole_is_refused(self, type_, capsys):
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_name(_Args(type_, "users"))

        assert excinfo.value.code == 2
        assert "takes no name" in capsys.readouterr().err

    @pytest.mark.parametrize("type_", ["columns", "indexes", "foreign-keys", "partitions"])
    def test_a_required_name_must_be_given(self, type_, capsys):
        """A missing required NAME is an incomplete invocation, not a refusal.

        It exits 1 like a missing ``--database``; 2 is reserved for a request
        this command declines to serve.
        """
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_name(_Args(type_))

        assert excinfo.value.code == 1
        assert "required" in capsys.readouterr().err

    @pytest.mark.parametrize("type_", ["views", "triggers", "table-options"])
    def test_an_optional_name_may_be_given_or_not(self, type_):
        introspect_cli._validate_name(_Args(type_))
        introspect_cli._validate_name(_Args(type_, "x"))


class TestTheCapabilityGate:
    def test_a_refused_family_exits_two(self, capsys):
        class _Dialect:
            @staticmethod
            def supports_trigger_introspection() -> bool:
                return False

        class _Backend:
            dialect = _Dialect()

        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._require_capability(_Args("triggers"), _Backend())

        assert excinfo.value.code == 2
        assert "not supported by this server" in capsys.readouterr().err

    def test_a_stub_without_a_dialect_is_not_refused(self):
        """The offline tests stand a stub in for the backend; it has no dialect."""
        introspect_cli._require_capability(_Args("triggers"), object())


class TestTheViewsBranch:
    """``views NAME`` answers for one view, and says so when there is no such view."""

    def _args(self, name: Optional[str]) -> argparse.Namespace:
        return argparse.Namespace(
            output="json",
            rich_ascii=False,
            type="views",
            name=name,
            database="mydb",
            is_async=False,
            named_connection=None,
            include_system=False,
        )

    def test_a_named_view_is_asked_for_by_name(self, monkeypatch):
        seen = {}

        class _View:
            name = "users_v"
            schema = "mydb"
            definition = "CREATE VIEW users_v AS SELECT 1"

        class _Introspector:
            @staticmethod
            def get_view_info(view_name, schema=None):
                seen["name"] = view_name
                return _View()

            @staticmethod
            def list_views(schema=None):  # pragma: no cover - must not be called
                raise AssertionError("the whole family was listed despite a name")

        class _Backend:
            dialect = MySQLDialect()
            _connection = None

            def __init__(self, **_kwargs):
                self.introspector = _Introspector()

            def connect(self):
                pass

            def introspect_and_adapt(self):
                pass

            def disconnect(self):
                pass

        monkeypatch.setattr(introspect_cli, "MySQLBackend", _Backend)
        monkeypatch.setattr(
            introspect_cli, "resolve_connection_config_from_args", lambda _args: None
        )

        introspect_cli.handle(self._args("users_v"))

        assert seen["name"] == "users_v"

    def test_an_unknown_view_exits_one(self, monkeypatch, capsys):
        class _Introspector:
            @staticmethod
            def get_view_info(view_name, schema=None):
                return None

        class _Backend:
            dialect = MySQLDialect()
            _connection = None

            def __init__(self, **_kwargs):
                self.introspector = _Introspector()

            def connect(self):
                pass

            def introspect_and_adapt(self):
                pass

            def disconnect(self):
                pass

        monkeypatch.setattr(introspect_cli, "MySQLBackend", _Backend)
        monkeypatch.setattr(
            introspect_cli, "resolve_connection_config_from_args", lambda _args: None
        )

        with pytest.raises(SystemExit) as excinfo:
            introspect_cli.handle(self._args("nope"))

        assert excinfo.value.code == 1
        assert "not found" in capsys.readouterr().err
