# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/cli/test_introspect_offline.py
"""Offline unit tests for ``impl.mysql.cli.introspect``.

No server and no network: every backend, introspector and output provider is a
mock. The tests that already exist for this module pin the type surface and the
new families; this file fills the remaining blind spots -- parser shape, the
pure serialisation/formatting helpers, the still-uncovered dispatch branches,
the sync/async error paths and the ``handle()`` dispatch itself.
"""

import argparse
from dataclasses import dataclass
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rhosocial.activerecord.backend.errors import ConnectionError, QueryError
from rhosocial.activerecord.backend.impl.mysql.cli import introspect as mod
from rhosocial.activerecord.backend.impl.mysql.cli.output import OUTPUT_CHOICES


def _args(type_, name=None, **overrides):
    """A parsed-invocation namespace with every attribute the module reads."""
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


def _backend(introspector, connected=True, is_async=False):
    """A stub backend: no dialect (so the capability gate is a no-op)."""
    backend = MagicMock()
    backend.introspector = introspector
    backend.dialect = None
    backend._connection = object() if connected else None
    if is_async:
        backend.connect = AsyncMock()
        backend.introspect_and_adapt = AsyncMock()
        backend.disconnect = AsyncMock()
    return backend


# ---------------------------------------------------------------------------
# create_parser
# ---------------------------------------------------------------------------


class TestCreateParser:
    def _parser(self):
        subs = argparse.ArgumentParser(prog="mysql").add_subparsers(dest="command")
        return mod.create_parser(subs)

    def test_defaults(self):
        args = self._parser().parse_args(["tables"])
        assert args.type == "tables"
        assert args.output == "table"
        assert args.name is None
        assert args.rich_ascii is False
        assert args.include_system is False
        assert args.column is None
        assert args.limit is None
        assert args.is_async is False

    @pytest.mark.parametrize("type_", mod.INTROSPECT_TYPES)
    def test_every_introspect_type_is_accepted(self, type_):
        assert self._parser().parse_args([type_]).type == type_

    def test_unknown_type_is_rejected(self):
        with pytest.raises(SystemExit) as exc:
            self._parser().parse_args(["not-a-type"])
        assert exc.value.code == 2

    def test_name_is_an_optional_positional(self):
        assert self._parser().parse_args(["columns", "users"]).name == "users"

    def test_output_choices(self):
        parser = self._parser()
        for choice in OUTPUT_CHOICES:
            assert parser.parse_args(["tables", "-o", choice]).output == choice
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["tables", "-o", "xml"])
        assert exc.value.code == 2

    def test_flags_and_typed_options(self):
        args = self._parser().parse_args(
            [
                "value-samples",
                "orders",
                "--column",
                "status",
                "--limit",
                "20",
                "-o",
                "json",
                "--rich-ascii",
                "--include-system",
                "--async",
            ]
        )
        assert args.column == "status"
        assert args.limit == 20
        assert isinstance(args.limit, int)
        assert args.output == "json"
        assert args.rich_ascii is True
        assert args.include_system is True
        assert args.is_async is True

    def test_join_coverage_flags(self):
        args = self._parser().parse_args(
            [
                "join-coverage",
                "--left-table",
                "orders",
                "--left-column",
                "customer_id",
                "--right-table",
                "customers",
                "--right-column",
                "id",
            ]
        )
        assert args.left_table == "orders"
        assert args.left_column == "customer_id"
        assert args.right_table == "customers"
        assert args.right_column == "id"

    def test_limit_must_be_an_integer(self):
        with pytest.raises(SystemExit) as exc:
            self._parser().parse_args(
                ["value-samples", "orders", "--column", "x", "--limit", "abc"]
            )
        assert exc.value.code == 2


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


class _NoMode:
    """``model_dump`` without a ``mode`` parameter forces the TypeError path."""

    def model_dump(self):
        return {"ok": True}


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

    def test_tuple_becomes_a_list(self):
        assert mod._serialize_for_output((1, 2)) == [1, 2]

    def test_model_dump_json_mode(self):
        assert mod._serialize_for_output(_WithModelDump()) == {"a": 1, "mode": "json"}

    def test_model_dump_typeerror_falls_back(self):
        assert mod._serialize_for_output(_NoMode()) == {"ok": True}

    def test_dataclass_type_is_not_serialised_as_an_instance(self):
        assert mod._serialize_for_output(_Point) == str(_Point)

    def test_unknown_object_falls_back_to_str(self):
        class _Opaque:
            def __str__(self):
                return "opaque"

        assert mod._serialize_for_output(_Opaque()) == "opaque"


# ---------------------------------------------------------------------------
# _value_sample_arguments and _display_ddl
# ---------------------------------------------------------------------------


class TestValueSampleArguments:
    def test_no_limit_means_no_forwarded_option(self):
        assert mod._value_sample_arguments(_args("value-samples")) == {}

    def test_limit_is_forwarded(self):
        assert mod._value_sample_arguments(_args("value-samples", limit=20)) == {"limit": 20}


class TestDisplayDdl:
    def _statement(self):
        return {
            "object_type": "TABLE",
            "object_name": "orders",
            "ddl": "CREATE TABLE `orders` (`id` int)",
            "native": True,
        }

    def test_non_table_output_uses_the_provider(self):
        provider = MagicMock()
        mod._display_ddl(_args("ddl", "orders", output="json"), provider, self._statement())
        provider.display_results.assert_called_once()
        assert provider.display_results.call_args.kwargs["title"] == "DDL of orders"
        assert provider.display_results.call_args.args[0][0]["native"] is True

    def test_table_output_prints_the_engine_text(self, capsys):
        mod._display_ddl(_args("ddl", "orders", output="table"), MagicMock(), self._statement())
        out = capsys.readouterr().out
        assert "-- TABLE orders" in out
        assert "CREATE TABLE `orders` (`id` int)" in out

    def test_table_output_falls_back_to_object_and_args_name(self, capsys):
        statement = {"ddl": "CREATE VIEW v AS SELECT 1"}
        mod._display_ddl(_args("ddl", "v", output="table"), MagicMock(), statement)
        out = capsys.readouterr().out
        assert "-- OBJECT v" in out
        assert "CREATE VIEW v AS SELECT 1" in out


# ---------------------------------------------------------------------------
# dispatch branches not covered by the family-specific test files
# ---------------------------------------------------------------------------


class TestSyncBranches:
    """The simple catalogue branches each reach exactly one introspector method."""

    @pytest.mark.parametrize(
        "type_, name, method, expected_args, expected_kwargs, title",
        [
            ("tables", None, "list_tables", (), {"schema": None, "include_system": True}, "Tables"),
            ("columns", "users", "list_columns", ("users",), {"schema": None}, "Columns of users"),
            ("indexes", "users", "list_indexes", ("users",), {"schema": None}, "Indexes of users"),
            (
                "foreign-keys",
                "users",
                "list_foreign_keys",
                ("users",),
                {"schema": None},
                "Foreign Keys of users",
            ),
            (
                "triggers",
                "users",
                "list_triggers",
                (),
                {"table_name": "users", "schema": None},
                "Triggers",
            ),
            (
                "table-options",
                None,
                "list_table_options",
                (),
                {"schema": None},
                "Table options",
            ),
            (
                "partitions",
                "orders",
                "list_partitions",
                ("orders",),
                {"schema": None},
                "Partitions of orders",
            ),
            ("database", None, "get_database_info", (), {}, "Database Info"),
        ],
    )
    def test_branch_calls_its_method_and_displays(
        self, type_, name, method, expected_args, expected_kwargs, title
    ):
        introspector = MagicMock()
        getattr(introspector, method).return_value = []
        backend = _backend(introspector)
        provider = MagicMock()
        args = _args(type_, name, include_system=True)

        mod._handle_introspect_sync(args, backend, provider)

        getattr(introspector, method).assert_called_once_with(*expected_args, **expected_kwargs)
        provider.display_results.assert_called_once()
        assert provider.display_results.call_args.kwargs["title"] == title
        backend.connect.assert_called_once()
        backend.introspect_and_adapt.assert_called_once()
        backend.disconnect.assert_called_once()

    def test_named_table_options_uses_get_table_options(self):
        introspector = MagicMock()
        introspector.get_table_options.return_value = {"engine": "InnoDB"}
        backend = _backend(introspector)
        provider = MagicMock()

        mod._handle_introspect_sync(_args("table-options", "users"), backend, provider)

        introspector.get_table_options.assert_called_once_with("users", schema=None)
        introspector.list_table_options.assert_not_called()

    def test_unknown_named_table_options_exits_one(self, capsys):
        introspector = MagicMock()
        introspector.get_table_options.return_value = None
        backend = _backend(introspector)

        with pytest.raises(SystemExit) as exc:
            mod._handle_introspect_sync(_args("table-options", "nope"), backend, MagicMock())
        assert exc.value.code == 1
        assert "not found" in capsys.readouterr().err

    def test_no_connection_skips_disconnect(self):
        introspector = MagicMock()
        introspector.list_tables.return_value = []
        backend = _backend(introspector, connected=False)
        mod._handle_introspect_sync(_args("tables"), backend, MagicMock())
        backend.disconnect.assert_not_called()


class TestAsyncBranches:
    @pytest.mark.parametrize(
        "type_, name, method, expected_args, expected_kwargs",
        [
            ("tables", None, "list_tables", (), {"schema": None, "include_system": False}),
            ("columns", "users", "list_columns", ("users",), {"schema": None}),
            ("indexes", "users", "list_indexes", ("users",), {"schema": None}),
            ("foreign-keys", "users", "list_foreign_keys", ("users",), {"schema": None}),
            ("triggers", "users", "list_triggers", (), {"table_name": "users", "schema": None}),
            ("table-options", None, "list_table_options", (), {"schema": None}),
            ("partitions", "orders", "list_partitions", ("orders",), {"schema": None}),
            ("database", None, "get_database_info", (), {}),
        ],
    )
    async def test_async_branch_calls_its_method(
        self, type_, name, method, expected_args, expected_kwargs
    ):
        introspector = MagicMock()
        setattr(introspector, method, AsyncMock(return_value=[]))
        backend = _backend(introspector, is_async=True)
        provider = MagicMock()

        await mod._handle_introspect_async(_args(type_, name), backend, provider)

        getattr(introspector, method).assert_awaited_once_with(*expected_args, **expected_kwargs)
        provider.display_results.assert_called_once()
        backend.disconnect.assert_awaited_once()

    async def test_async_no_connection_skips_disconnect(self):
        introspector = MagicMock()
        introspector.list_tables = AsyncMock(return_value=[])
        backend = _backend(introspector, connected=False, is_async=True)
        await mod._handle_introspect_async(_args("tables"), backend, MagicMock())
        backend.disconnect.assert_not_awaited()


# ---------------------------------------------------------------------------
# error paths
# ---------------------------------------------------------------------------


class TestSyncErrorPaths:
    def test_connection_error(self):
        backend = _backend(MagicMock(), connected=False)
        backend.connect.side_effect = ConnectionError("nope")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            mod._handle_introspect_sync(_args("tables"), backend, provider)
        assert exc.value.code == 1
        provider.display_connection_error.assert_called_once()

    def test_query_error(self):
        introspector = MagicMock()
        introspector.list_tables.side_effect = QueryError("bad sql")
        backend = _backend(introspector, connected=False)
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            mod._handle_introspect_sync(_args("tables"), backend, provider)
        assert exc.value.code == 1
        provider.display_query_error.assert_called_once()

    def test_generic_error(self, capsys):
        introspector = MagicMock()
        introspector.list_tables.side_effect = RuntimeError("boom")
        backend = _backend(introspector, connected=False)
        with pytest.raises(SystemExit) as exc:
            mod._handle_introspect_sync(_args("tables"), backend, MagicMock())
        assert exc.value.code == 1
        assert "Error during introspection: boom" in capsys.readouterr().err


class TestAsyncErrorPaths:
    async def test_connection_error(self):
        backend = _backend(MagicMock(), connected=False, is_async=True)
        backend.connect.side_effect = ConnectionError("nope")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            await mod._handle_introspect_async(_args("tables"), backend, provider)
        assert exc.value.code == 1
        provider.display_connection_error.assert_called_once()

    async def test_query_error(self):
        introspector = MagicMock()
        introspector.list_tables = AsyncMock(side_effect=QueryError("bad sql"))
        backend = _backend(introspector, connected=False, is_async=True)
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            await mod._handle_introspect_async(_args("tables"), backend, provider)
        assert exc.value.code == 1
        provider.display_query_error.assert_called_once()

    async def test_generic_error(self, capsys):
        introspector = MagicMock()
        introspector.list_tables = AsyncMock(side_effect=RuntimeError("boom"))
        backend = _backend(introspector, connected=False, is_async=True)
        with pytest.raises(SystemExit) as exc:
            await mod._handle_introspect_async(_args("tables"), backend, MagicMock())
        assert exc.value.code == 1
        assert "Error during introspection: boom" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# handle() dispatch
# ---------------------------------------------------------------------------


class TestHandleDispatch:
    def test_database_is_required(self, capsys):
        with pytest.raises(SystemExit) as exc:
            mod.handle(_args("tables", database=None))
        assert exc.value.code == 1
        assert "--database is required" in capsys.readouterr().err

    def test_named_connection_allows_no_database(self):
        args = _args("tables", database=None, named_connection="app.connections.prod")
        with patch.object(mod, "create_provider"), patch.object(
            mod, "resolve_connection_config_from_args", return_value=MagicMock()
        ), patch.object(mod, "MySQLBackend"), patch.object(
            mod, "_handle_introspect_sync"
        ) as handler:
            mod.handle(args)
        handler.assert_called_once()

    def test_name_validation_runs_before_any_connection(self, capsys):
        args = _args("columns", name=None)
        with pytest.raises(SystemExit) as exc:
            mod.handle(args)
        assert exc.value.code == 1
        assert "Table name is required" in capsys.readouterr().err

    def test_option_validation_runs_before_any_connection(self, capsys):
        args = _args("tables", column="status")
        with pytest.raises(SystemExit) as exc:
            mod.handle(args)
        assert exc.value.code == 2
        assert "takes no --column" in capsys.readouterr().err

    def test_sync_dispatch(self):
        args = _args("tables", output="table", rich_ascii=True)
        with patch.object(mod, "create_provider") as cp, patch.object(
            mod, "resolve_connection_config_from_args", return_value=MagicMock()
        ) as resolve, patch.object(mod, "MySQLBackend") as backend_cls, patch.object(
            mod, "_handle_introspect_sync"
        ) as handler:
            mod.handle(args)
        cp.assert_called_once_with("table", ascii_borders=True)
        resolve.assert_called_once_with(args)
        backend_cls.assert_called_once()
        handler.assert_called_once_with(args, backend_cls.return_value, cp.return_value)

    def test_async_dispatch(self):
        args = _args("tables", is_async=True)
        with patch.object(mod, "create_provider"), patch.object(
            mod, "resolve_connection_config_from_args", return_value=MagicMock()
        ), patch.object(mod, "AsyncMySQLBackend") as backend_cls, patch.object(
            mod, "_handle_introspect_async", new_callable=AsyncMock
        ) as handler:
            mod.handle(args)
        backend_cls.assert_called_once()
        handler.assert_awaited_once()
