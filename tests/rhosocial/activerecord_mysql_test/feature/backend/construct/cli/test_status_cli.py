# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/cli/test_status_cli.py
"""Backend-owned tests for ``impl.mysql.cli.status``.

The shared testsuite covers data-operation compatibility, not the CLI surface.
These tests pin this backend's status subcommand: parser shape, pure helpers,
JSON/rich rendering, and the sync/async dispatch and error paths (all mocked,
so no live server is needed).
"""
from dataclasses import dataclass
from enum import Enum
from unittest.mock import MagicMock, patch

import pytest

from rhosocial.activerecord.backend.impl.mysql.cli import status as mod
from rhosocial.activerecord.backend.introspection.status import (
    ConnectionInfo,
    DatabaseBriefInfo,
    ServerOverview,
    SessionInfo,
    StatusCategory,
    StatusItem,
    StorageInfo,
    UserInfo,
)


# ---------------------------------------------------------------------------
# create_parser
# ---------------------------------------------------------------------------


class TestCreateParser:
    def test_parser_defaults_and_choices(self):
        import argparse

        subs = argparse.ArgumentParser(prog="mysql").add_subparsers(dest="command")
        parser = mod.create_parser(subs)
        args = parser.parse_args([])
        assert args.type == "all"
        assert args.output == "table"
        assert args.verbose == 0
        assert args.rich_ascii is False

    @pytest.mark.parametrize("t", mod.STATUS_TYPES)
    def test_all_status_types_accepted(self, t):
        import argparse

        subs = argparse.ArgumentParser(prog="mysql").add_subparsers(dest="command")
        parser = mod.create_parser(subs)
        assert parser.parse_args([t]).type == t

    def test_verbose_is_counted(self):
        import argparse

        subs = argparse.ArgumentParser(prog="mysql").add_subparsers(dest="command")
        parser = mod.create_parser(subs)
        assert parser.parse_args(["-vvv"]).verbose == 3


# ---------------------------------------------------------------------------
# _serialize_for_output
# ---------------------------------------------------------------------------


class _Colour(Enum):
    RED = "red"


@dataclass
class _Point:
    x: int
    y: int


class _WithModelDump:
    def model_dump(self, mode="python"):
        return {"a": 1, "mode": mode}


class _Fallback:
    def __str__(self):
        return "fallback"


class TestSerializeForOutput:
    def test_none_and_scalars(self):
        assert mod._serialize_for_output(None) is None
        assert mod._serialize_for_output("x") == "x"
        assert mod._serialize_for_output(3) == 3
        assert mod._serialize_for_output(1.5) == 1.5
        assert mod._serialize_for_output(True) is True

    def test_enum(self):
        assert mod._serialize_for_output(_Colour.RED) == "red"

    def test_dataclass(self):
        assert mod._serialize_for_output(_Point(1, 2)) == {"x": 1, "y": 2}

    def test_dict_and_list_recursive(self):
        obj = {"p": _Point(1, 2), "c": _Colour.RED, "items": [_Colour.RED, 2]}
        assert mod._serialize_for_output(obj) == {
            "p": {"x": 1, "y": 2},
            "c": "red",
            "items": ["red", 2],
        }

    def test_tuple_becomes_list(self):
        assert mod._serialize_for_output((1, 2)) == [1, 2]

    def test_model_dump_json_mode(self):
        assert mod._serialize_for_output(_WithModelDump()) == {"a": 1, "mode": "json"}

    def test_model_dump_typeerror_falls_back(self):
        # model_dump(mode="json") raises TypeError here, so the source retries
        # model_dump() with no args; its result is then serialized.
        class BadNoMode:
            def model_dump(self):
                return {"ok": True}

        assert mod._serialize_for_output(BadNoMode()) == {"ok": True}

    def test_unknown_falls_back_to_str(self):
        assert mod._serialize_for_output(_Fallback()) == "fallback"


# ---------------------------------------------------------------------------
# _format_size
# ---------------------------------------------------------------------------


class TestFormatSize:
    @pytest.mark.parametrize(
        "size,expected",
        [
            (0, "0.0 B"),
            (512, "512.0 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024**3, "1.0 GB"),
            (1024**4, "1.0 TB"),
            (1024**5, "1.0 PB"),
        ],
    )
    def test_units(self, size, expected):
        assert mod._format_size(size) == expected


# ---------------------------------------------------------------------------
# _display_status_rich
# ---------------------------------------------------------------------------


def _overview():
    return ServerOverview(
        server_version="8.0.35",
        server_vendor="MySQL",
        session=SessionInfo(
            user="root",
            database="app",
            host="localhost",
            ssl_enabled=True,
            ssl_version="TLSv1.3",
            ssl_cipher="AES",
            password_used=True,
        ),
        configuration=[
            StatusItem("max_connections", 151, StatusCategory.CONFIGURATION, "desc", is_readonly=True),
            StatusItem("datadir", "/var/lib", StatusCategory.CONFIGURATION),
            # The renderer splits sections from ``configuration`` by category.
            StatusItem("queries", 100, StatusCategory.PERFORMANCE, unit="q/s"),
        ],
        connections=ConnectionInfo(active_count=5, max_connections=151),
        storage=StorageInfo(total_size_bytes=1024**3, data_size_bytes=512, index_size_bytes=256),
        databases=[DatabaseBriefInfo("app", size_bytes=1024, table_count=3, view_count=1)],
        users=[UserInfo("root", is_superuser=True)],
    )


class _FakeTable:
    def __init__(self, *a, **k):
        self.columns = []
        self.rows = []

    def add_column(self, *a, **k):
        self.columns.append((a, k))

    def add_row(self, *a, **k):
        self.rows.append((a, k))


class _FakeConsole:
    printed = []

    def __init__(self, *a, **k):
        pass

    def print(self, *a, **k):
        for item in a:
            if isinstance(item, _FakeTable):
                for args, kwargs in item.columns:
                    _FakeConsole.printed.extend(str(x) for x in args)
                for args, kwargs in item.rows:
                    _FakeConsole.printed.extend(str(x) for x in args)
            else:
                _FakeConsole.printed.append(str(item))


@pytest.fixture
def fake_rich():
    """Inject minimal fake rich modules so _display_status_rich runs without rich installed."""
    import sys
    import types

    console_mod = types.ModuleType("rich.console")
    console_mod.Console = _FakeConsole
    table_mod = types.ModuleType("rich.table")
    table_mod.Table = _FakeTable
    rich_mod = types.ModuleType("rich")
    rich_mod.console = console_mod
    rich_mod.table = table_mod
    with patch.dict(
        sys.modules,
        {"rich": rich_mod, "rich.console": console_mod, "rich.table": table_mod},
    ):
        _FakeConsole.printed = []
        yield


class TestDisplayStatusRich:
    def test_verbose_zero(self, fake_rich):
        mod._display_status_rich(_overview(), verbose=0)
        out = " ".join(_FakeConsole.printed)
        assert "MySQL Server Status" in out
        assert "8.0.35" in out
        assert "Configuration" in out
        assert "Performance" in out
        assert "Storage" in out
        assert "Databases" in out
        assert "Users" in out

    def test_verbose_extra_columns(self, fake_rich):
        mod._display_status_rich(_overview(), verbose=1)
        out = " ".join(_FakeConsole.printed)
        assert "Readonly" in out
        assert "Unit" in out
        assert "Tables" in out
        assert "SSL" in out

    def test_minimal_status(self, fake_rich):
        bare = ServerOverview(server_version="8.0", server_vendor="MySQL")
        mod._display_status_rich(bare)
        assert any("8.0" in s for s in _FakeConsole.printed)

    def test_ssl_disabled_and_no_password(self, fake_rich):
        ov = _overview()
        ov.session.ssl_enabled = False
        ov.session.password_used = False
        mod._display_status_rich(ov, verbose=1)
        out = " ".join(_FakeConsole.printed)
        assert "Disabled" in out
        assert "Other" in out


# ---------------------------------------------------------------------------
# _handle_status_sync / _handle_status_async / handle
# ---------------------------------------------------------------------------


def _args(status_type="all", output="table", verbose=0, rich_ascii=False, is_async=False):
    a = MagicMock()
    a.type = status_type
    a.output = output
    a.verbose = verbose
    a.rich_ascii = rich_ascii
    a.is_async = is_async
    a.database = "app"
    a.named_connection = None
    return a


class TestHandleStatusSync:
    @pytest.mark.parametrize(
        "status_type", ["config", "performance", "connections", "storage", "databases", "users"]
    )
    def test_each_branch_displays(self, status_type):
        args = _args(status_type=status_type)
        backend = MagicMock()
        backend._connection = object()
        provider = MagicMock()
        introspector = backend.introspector.status
        with patch.object(mod, "_serialize_for_output", side_effect=lambda x: x):
            mod._handle_status_sync(args, backend, provider)
        provider.display_results.assert_called_once()
        backend.disconnect.assert_called_once()

    def test_all_json_output(self, capsys):
        args = _args(status_type="all", output="json")
        backend = MagicMock()
        backend._connection = None
        provider = MagicMock()
        with patch.object(mod, "_serialize_for_output", return_value={"ok": 1}):
            mod._handle_status_sync(args, backend, provider)
        assert '"ok": 1' in capsys.readouterr().out

    def test_all_csv_falls_back_to_json(self, capsys):
        args = _args(status_type="all", output="csv")
        backend = MagicMock()
        backend._connection = None
        provider = MagicMock()
        with patch.object(mod, "_serialize_for_output", return_value={"ok": 1}):
            mod._handle_status_sync(args, backend, provider)
        assert '"ok": 1' in capsys.readouterr().out

    def test_all_rich_when_available(self):
        args = _args(status_type="all", output="table")
        backend = MagicMock()
        backend._connection = None
        provider = MagicMock()
        with patch.object(mod, "RICH_AVAILABLE", True), patch.object(mod, "_display_status_rich") as d:
            mod._handle_status_sync(args, backend, provider)
        d.assert_called_once()

    def test_connection_error_exits(self):
        from rhosocial.activerecord.backend.errors import ConnectionError

        args = _args()
        backend = MagicMock()
        backend._connection = None
        provider = MagicMock()
        backend.connect.side_effect = ConnectionError("nope")
        with pytest.raises(SystemExit) as e:
            mod._handle_status_sync(args, backend, provider)
        assert e.value.code == 1
        provider.display_connection_error.assert_called_once()

    def test_query_error_exits(self):
        from rhosocial.activerecord.backend.errors import QueryError

        args = _args()
        backend = MagicMock()
        backend._connection = None
        provider = MagicMock()
        backend.introspector.status.get_overview.side_effect = QueryError("bad")
        with pytest.raises(SystemExit) as e:
            mod._handle_status_sync(args, backend, provider)
        assert e.value.code == 1
        provider.display_query_error.assert_called_once()

    def test_generic_error_exits(self, capsys):
        args = _args()
        backend = MagicMock()
        backend._connection = None
        backend.introspector.status.get_overview.side_effect = RuntimeError("boom")
        with pytest.raises(SystemExit) as e:
            mod._handle_status_sync(args, backend, MagicMock())
        assert e.value.code == 1
        assert "boom" in capsys.readouterr().err


class TestHandleStatusAsync:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "status_type", ["config", "performance", "connections", "storage", "databases", "users"]
    )
    async def test_each_branch_displays(self, status_type):
        args = _args(status_type=status_type, is_async=True)
        backend = MagicMock()
        backend._connection = object()

        async def _noop(*a, **k):
            return None

        backend.connect = _noop
        backend.introspect_and_adapt = _noop
        backend.disconnect = _noop
        introspector = backend.introspector.status
        for m in ("get_overview", "list_configuration", "get_connection_info", "get_storage_info",
                  "list_databases", "list_users"):
            setattr(introspector, m, _noop)
        provider = MagicMock()
        with patch.object(mod, "_serialize_for_output", side_effect=lambda x: x):
            await mod._handle_status_async(args, backend, provider)
        provider.display_results.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_error_exits(self):
        from rhosocial.activerecord.backend.errors import ConnectionError

        args = _args(is_async=True)
        backend = MagicMock()
        backend._connection = None

        async def _raise(*a, **k):
            raise ConnectionError("nope")

        backend.connect = _raise
        provider = MagicMock()
        with pytest.raises(SystemExit) as e:
            await mod._handle_status_async(args, backend, provider)
        assert e.value.code == 1
        provider.display_connection_error.assert_called_once()


class TestHandleDispatch:
    def test_requires_database(self, capsys):
        args = _args()
        args.database = None
        args.named_connection = None
        with pytest.raises(SystemExit) as e:
            mod.handle(args)
        assert e.value.code == 1
        assert "database is required" in capsys.readouterr().err

    def test_sync_dispatch(self):
        args = _args(is_async=False)
        with patch.object(mod, "resolve_connection_config_from_args", return_value=MagicMock()), \
             patch.object(mod, "MySQLBackend") as B, \
             patch.object(mod, "_handle_status_sync") as h:
            mod.handle(args)
        h.assert_called_once()
        B.return_value.connect.assert_not_called()

    def test_async_dispatch(self):
        args = _args(is_async=True)
        with patch.object(mod, "resolve_connection_config_from_args", return_value=MagicMock()), \
             patch.object(mod, "AsyncMySQLBackend") as B, \
             patch.object(mod, "asyncio"), \
             patch.object(mod, "_handle_status_async") as h:
            mod.handle(args)
        B.assert_called_once()
