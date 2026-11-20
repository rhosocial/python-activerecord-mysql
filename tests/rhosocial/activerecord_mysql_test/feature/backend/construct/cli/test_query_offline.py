# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/cli/test_query_offline.py
"""Offline unit tests for ``impl.mysql.cli.query``.

The database, the output provider, the logging configuration and the standard
streams are all mocked: these tests pin argument parsing, SQL-source selection,
``handle()`` dispatch and the sync/async execution/error paths without ever
opening a connection.
"""

import argparse
import sys
import types
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from rhosocial.activerecord.backend.errors import ConnectionError, QueryError
from rhosocial.activerecord.backend.impl.mysql.cli import query as mod
from rhosocial.activerecord.backend.impl.mysql.cli.output import OUTPUT_CHOICES


def _args(**overrides):
    values = dict(
        sql=None,
        file=None,
        output="json",
        log_level="INFO",
        rich_ascii=False,
        is_async=False,
        database="mydb",
        named_connection=None,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


def _result(data=None, affected_rows=2, duration=0.25):
    result = MagicMock()
    result.affected_rows = affected_rows
    result.duration = duration
    result.data = data
    return result


@contextmanager
def _handle_env(is_async=False):
    """Patch every seam ``handle()`` touches before it reaches a backend."""
    with patch.object(mod, "create_provider") as cp, patch.object(
        mod.logging, "basicConfig"
    ), patch.object(mod, "RICH_AVAILABLE", False), patch.object(
        mod, "resolve_connection_config_from_args", return_value=MagicMock()
    ):
        if is_async:
            with patch.object(mod, "AsyncMySQLBackend") as backend_cls, patch.object(
                mod, "_execute_query_async", new_callable=AsyncMock
            ) as execute:
                yield cp.return_value, backend_cls, execute
        else:
            with patch.object(mod, "MySQLBackend") as backend_cls, patch.object(
                mod, "_execute_query_sync"
            ) as execute:
                yield cp.return_value, backend_cls, execute


# ---------------------------------------------------------------------------
# create_parser
# ---------------------------------------------------------------------------


class TestCreateParser:
    def _parser(self):
        subs = argparse.ArgumentParser(prog="mysql").add_subparsers(dest="command")
        return mod.create_parser(subs)

    def test_defaults(self):
        args = self._parser().parse_args([])
        assert args.sql is None
        assert args.file is None
        assert args.output == "table"
        assert args.log_level == "INFO"
        assert args.rich_ascii is False
        assert args.is_async is False

    def test_sql_is_an_optional_positional(self):
        assert self._parser().parse_args(["SELECT 1"]).sql == "SELECT 1"

    def test_file_flag(self):
        args = self._parser().parse_args(["-f", "query.sql"])
        assert args.file == "query.sql"
        assert self._parser().parse_args(["--file", "query.sql"]).file == "query.sql"

    @pytest.mark.parametrize("choice", OUTPUT_CHOICES)
    def test_output_choices(self, choice):
        assert self._parser().parse_args(["-o", choice]).output == choice

    def test_unknown_output_is_rejected(self):
        with pytest.raises(SystemExit) as exc:
            self._parser().parse_args(["-o", "xml"])
        assert exc.value.code == 2

    def test_log_level_and_flags(self):
        args = self._parser().parse_args(
            ["--log-level", "DEBUG", "--rich-ascii", "--async", "SELECT 1"]
        )
        assert args.log_level == "DEBUG"
        assert args.rich_ascii is True
        assert args.is_async is True
        assert args.sql == "SELECT 1"


# ---------------------------------------------------------------------------
# handle(): log level, SQL sourcing and dispatch
# ---------------------------------------------------------------------------


class TestHandleValidation:
    @pytest.mark.parametrize("level", ["DEBUG", "info", "WARNING"])
    def test_valid_log_levels_are_accepted(self, level):
        with _handle_env() as (provider, _backend, execute):
            mod.handle(_args(sql="SELECT 1", log_level=level))
        provider.display_greeting.assert_called_once()
        execute.assert_called_once()

    def test_invalid_log_level_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid log level"):
            mod.handle(_args(sql="SELECT 1", log_level="NOPE"))

    def test_no_sql_anywhere_exits_one(self, capsys):
        with _handle_env(), patch.object(mod.sys, "stdin") as stdin:
            stdin.isatty.return_value = True
            with pytest.raises(SystemExit) as exc:
                mod.handle(_args())
        assert exc.value.code == 1
        assert "No SQL query provided" in capsys.readouterr().err

    def test_multiple_statements_are_refused(self):
        with _handle_env():
            with pytest.raises(SystemExit) as exc:
                mod.handle(_args(sql="SELECT 1; SELECT 2"))
        assert exc.value.code == 1

    def test_a_single_trailing_semicolon_is_allowed(self):
        with _handle_env() as (_provider, _backend, execute):
            mod.handle(_args(sql="SELECT 1;"))
        assert execute.call_args.args[0] == "SELECT 1;"


class TestHandleSqlSource:
    def test_sql_argument_wins(self):
        with _handle_env() as (provider, backend_cls, execute):
            mod.handle(_args(sql="SELECT 1", file="ignored.sql"))
        assert execute.call_args.args[0] == "SELECT 1"
        assert execute.call_args.args[1] is backend_cls.return_value
        assert execute.call_args.args[2] is provider
        assert execute.call_args.kwargs == {"use_ascii": False}
        backend_cls.assert_called_once()

    def test_file_content_is_used_when_sql_is_absent(self):
        with _handle_env() as (_provider, _backend, execute), patch(
            "builtins.open", mock_open(read_data="SELECT 2")
        ):
            mod.handle(_args(file="query.sql"))
        assert execute.call_args.args[0] == "SELECT 2"

    def test_missing_file_exits_one(self):
        with _handle_env(), patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(SystemExit) as exc:
                mod.handle(_args(file="missing.sql"))
        assert exc.value.code == 1

    def test_stdin_is_used_when_not_a_tty(self):
        with _handle_env() as (_provider, _backend, execute), patch.object(
            mod.sys, "stdin"
        ) as stdin:
            stdin.isatty.return_value = False
            stdin.read.return_value = "SELECT 3"
            mod.handle(_args())
        assert execute.call_args.args[0] == "SELECT 3"

    def test_provider_receives_output_and_ascii_flag(self):
        with patch.object(mod, "create_provider") as cp, patch.object(
            mod.logging, "basicConfig"
        ), patch.object(mod, "RICH_AVAILABLE", False), patch.object(
            mod, "resolve_connection_config_from_args", return_value=MagicMock()
        ), patch.object(
            mod, "MySQLBackend"
        ), patch.object(
            mod, "_execute_query_sync"
        ):
            mod.handle(_args(sql="SELECT 1", output="csv", rich_ascii=True))
        cp.assert_called_once_with("csv", ascii_borders=True)


class TestHandleRichLoggingBranches:
    """Both halves of the ``RICH_AVAILABLE`` switch, with fake rich modules."""

    @pytest.fixture
    def fake_rich_modules(self):
        output_rich = types.ModuleType("rhosocial.activerecord.backend.output_rich")

        class _RichProvider:
            def display_greeting(self):
                pass

        output_rich.RichOutputProvider = _RichProvider
        console_mod = types.ModuleType("rich.console")
        console_mod.Console = MagicMock()
        logging_mod = types.ModuleType("rich.logging")
        logging_mod.RichHandler = MagicMock()
        rich_mod = types.ModuleType("rich")
        rich_mod.console = console_mod
        rich_mod.logging = logging_mod
        modules = {
            "rhosocial.activerecord.backend.output_rich": output_rich,
            "rich": rich_mod,
            "rich.console": console_mod,
            "rich.logging": logging_mod,
        }
        with patch.dict(sys.modules, modules):
            yield _RichProvider

    def test_rich_provider_uses_rich_handler(self, fake_rich_modules):
        with patch.object(mod, "RICH_AVAILABLE", True), patch.object(
            mod, "create_provider", return_value=fake_rich_modules()
        ), patch.object(mod.logging, "basicConfig") as basic_config, patch.object(
            mod, "resolve_connection_config_from_args", return_value=MagicMock()
        ), patch.object(
            mod, "MySQLBackend"
        ), patch.object(
            mod, "_execute_query_sync"
        ):
            mod.handle(_args(sql="SELECT 1"))
        assert "handlers" in basic_config.call_args.kwargs
        assert basic_config.call_args.kwargs["format"] == "%(message)s"

    def test_plain_provider_uses_stderr_stream(self, fake_rich_modules):
        with patch.object(mod, "RICH_AVAILABLE", True), patch.object(
            mod, "create_provider", return_value=MagicMock()
        ), patch.object(mod.logging, "basicConfig") as basic_config, patch.object(
            mod, "resolve_connection_config_from_args", return_value=MagicMock()
        ), patch.object(
            mod, "MySQLBackend"
        ), patch.object(
            mod, "_execute_query_sync"
        ):
            mod.handle(_args(sql="SELECT 1"))
        assert basic_config.call_args.kwargs["stream"] is sys.stderr

    def test_rich_unavailable_uses_stderr_stream(self):
        with patch.object(mod, "RICH_AVAILABLE", False), patch.object(
            mod, "create_provider", return_value=MagicMock()
        ), patch.object(mod.logging, "basicConfig") as basic_config, patch.object(
            mod, "resolve_connection_config_from_args", return_value=MagicMock()
        ), patch.object(
            mod, "MySQLBackend"
        ), patch.object(
            mod, "_execute_query_sync"
        ):
            mod.handle(_args(sql="SELECT 1"))
        assert basic_config.call_args.kwargs["stream"] is sys.stderr


class TestHandleAsyncDispatch:
    def test_async_backend_and_executor_are_used(self):
        # Kept synchronous: ``handle`` owns the event loop via ``asyncio.run``.
        with _handle_env(is_async=True) as (_provider, backend_cls, execute):
            mod.handle(_args(sql="SELECT 1", is_async=True))
        backend_cls.assert_called_once()
        execute.assert_awaited_once()
        assert execute.await_args.args[0] == "SELECT 1"


# ---------------------------------------------------------------------------
# _execute_query_sync
# ---------------------------------------------------------------------------


class TestExecuteQuerySync:
    def test_success_with_data(self):
        backend = MagicMock()
        backend._connection = object()
        backend.execute.return_value = _result(data=[{"id": 1}])
        provider = MagicMock()

        mod._execute_query_sync("SELECT 1", backend, provider, use_ascii=True)

        backend.connect.assert_called_once()
        provider.display_query.assert_called_once_with("SELECT 1", is_async=False)
        provider.display_success.assert_called_once_with(2, 0.25)
        provider.display_results.assert_called_once_with([{"id": 1}], use_ascii=True)
        provider.display_no_data.assert_not_called()
        provider.display_disconnect.assert_called_once_with(is_async=False)

    def test_success_without_data(self):
        backend = MagicMock()
        backend._connection = object()
        backend.execute.return_value = _result(data=[])
        provider = MagicMock()

        mod._execute_query_sync("UPDATE t SET x=1", backend, provider)

        provider.display_success.assert_called_once()
        provider.display_no_data.assert_called_once()
        provider.display_results.assert_not_called()

    def test_no_result_object(self):
        backend = MagicMock()
        backend._connection = object()
        backend.execute.return_value = None
        provider = MagicMock()

        mod._execute_query_sync("SELECT 1", backend, provider)

        provider.display_no_result_object.assert_called_once()
        provider.display_success.assert_not_called()

    def test_no_connection_skips_disconnect(self):
        backend = MagicMock()
        backend._connection = None
        backend.execute.return_value = _result(data=[])
        provider = MagicMock()

        mod._execute_query_sync("SELECT 1", backend, provider)

        backend.disconnect.assert_not_called()
        provider.display_disconnect.assert_not_called()

    @pytest.mark.parametrize(
        "error, expected_provider_call",
        [
            (ConnectionError("nope"), "display_connection_error"),
            (QueryError("bad sql"), "display_query_error"),
            (RuntimeError("boom"), "display_unexpected_error"),
        ],
    )
    def test_errors_exit_one(self, error, expected_provider_call):
        backend = MagicMock()
        backend._connection = None
        backend.connect.side_effect = error
        provider = MagicMock()

        with pytest.raises(SystemExit) as exc:
            mod._execute_query_sync("SELECT 1", backend, provider)
        assert exc.value.code == 1
        call = getattr(provider, expected_provider_call)
        call.assert_called_once()
        if expected_provider_call == "display_unexpected_error":
            call.assert_called_once_with(error, is_async=False)

    def test_disconnect_still_runs_after_an_error(self):
        backend = MagicMock()
        backend._connection = object()
        backend.execute.side_effect = QueryError("bad")
        provider = MagicMock()

        with pytest.raises(SystemExit):
            mod._execute_query_sync("SELECT 1", backend, provider)
        backend.disconnect.assert_called_once()
        provider.display_disconnect.assert_called_once_with(is_async=False)


# ---------------------------------------------------------------------------
# _execute_query_async
# ---------------------------------------------------------------------------


class TestExecuteQueryAsync:
    @staticmethod
    def _async_backend(result):
        backend = MagicMock()
        backend._connection = object()
        backend.connect = AsyncMock()
        backend.execute = AsyncMock(return_value=result)
        backend.disconnect = AsyncMock()
        return backend

    async def test_success_with_data(self):
        backend = self._async_backend(_result(data=[{"id": 1}]))
        provider = MagicMock()

        await mod._execute_query_async("SELECT 1", backend, provider, use_ascii=True)

        backend.execute.assert_awaited_once_with("SELECT 1")
        provider.display_query.assert_called_once_with("SELECT 1", is_async=True)
        provider.display_success.assert_called_once_with(2, 0.25)
        provider.display_results.assert_called_once_with([{"id": 1}], use_ascii=True)
        provider.display_disconnect.assert_called_once_with(is_async=True)
        backend.disconnect.assert_awaited_once()

    async def test_success_without_data(self):
        backend = self._async_backend(_result(data=[]))
        provider = MagicMock()

        await mod._execute_query_async("SELECT 1", backend, provider)

        provider.display_no_data.assert_called_once()
        provider.display_results.assert_not_called()

    async def test_no_result_object(self):
        backend = self._async_backend(None)
        provider = MagicMock()

        await mod._execute_query_async("SELECT 1", backend, provider)

        provider.display_no_result_object.assert_called_once()
        provider.display_success.assert_not_called()

    async def test_no_connection_skips_disconnect(self):
        backend = self._async_backend(_result(data=[]))
        backend._connection = None
        provider = MagicMock()

        await mod._execute_query_async("SELECT 1", backend, provider)

        backend.disconnect.assert_not_awaited()
        provider.display_disconnect.assert_not_called()

    @pytest.mark.parametrize(
        "error, expected_provider_call",
        [
            (ConnectionError("nope"), "display_connection_error"),
            (QueryError("bad sql"), "display_query_error"),
            (RuntimeError("boom"), "display_unexpected_error"),
        ],
    )
    async def test_errors_exit_one(self, error, expected_provider_call):
        backend = self._async_backend(None)
        backend.connect.side_effect = error
        provider = MagicMock()

        with pytest.raises(SystemExit) as exc:
            await mod._execute_query_async("SELECT 1", backend, provider)
        assert exc.value.code == 1
        call = getattr(provider, expected_provider_call)
        call.assert_called_once()
        if expected_provider_call == "display_unexpected_error":
            call.assert_called_once_with(error, is_async=True)

    async def test_disconnect_still_runs_after_an_error(self):
        backend = self._async_backend(None)
        backend.execute.side_effect = QueryError("bad")
        provider = MagicMock()

        with pytest.raises(SystemExit):
            await mod._execute_query_async("SELECT 1", backend, provider)
        backend.disconnect.assert_awaited_once()
        provider.display_disconnect.assert_called_once_with(is_async=True)
