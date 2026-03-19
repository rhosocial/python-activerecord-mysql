# src/rhosocial/activerecord/backend/impl/mysql/__main__.py
"""
MySQL backend command-line interface.

Provides SQL execution and database information display capabilities.
"""
import argparse
import asyncio
import inspect
import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional, Tuple

from . import MySQLBackend, AsyncMySQLBackend
from .config import MySQLConnectionConfig
from .dialect import MySQLDialect
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError
from rhosocial.activerecord.backend.output import (
    JsonOutputProvider, CsvOutputProvider, TsvOutputProvider
)
from rhosocial.activerecord.backend.dialect.protocols import (
    WindowFunctionSupport, CTESupport, FilterClauseSupport,
    ReturningSupport, UpsertSupport, LateralJoinSupport, JoinSupport,
    JSONSupport, ExplainSupport, GraphSupport,
    SetOperationSupport, ViewSupport,
    TableSupport, TruncateSupport, GeneratedColumnSupport,
    TriggerSupport, FunctionSupport,
    AdvancedGroupingSupport, ArraySupport, ILIKESupport,
    IndexSupport, LockingSupport, MergeSupport,
    OrderedSetAggregationSupport, QualifyClauseSupport,
    SchemaSupport, SequenceSupport, TemporalTableSupport,
)
from .protocols import (
    MySQLTriggerSupport,
    MySQLTableSupport,
    MySQLSetTypeSupport,
    MySQLJSONFunctionSupport,
    MySQLSpatialSupport,
)

# Attempt to import rich for formatted output
try:
    from rich.logging import RichHandler
    from rhosocial.activerecord.backend.output_rich import RichOutputProvider
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    RichOutputProvider = None  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)

# Groups that are specific to MySQL dialect
DIALECT_SPECIFIC_GROUPS = {"MySQL-specific"}

# Protocol family groups for display
PROTOCOL_FAMILY_GROUPS: Dict[str, list] = {
    "Query Features": [
        WindowFunctionSupport, CTESupport, FilterClauseSupport,
        SetOperationSupport, AdvancedGroupingSupport,
    ],
    "JOIN Support": [JoinSupport, LateralJoinSupport],
    "Data Types": [JSONSupport, ArraySupport],
    "DML Features": [
        ReturningSupport, UpsertSupport, MergeSupport,
        OrderedSetAggregationSupport,
    ],
    "Transaction & Locking": [LockingSupport, TemporalTableSupport],
    "Query Analysis": [ExplainSupport, GraphSupport, QualifyClauseSupport],
    "DDL - Table": [TableSupport, TruncateSupport, GeneratedColumnSupport],
    "DDL - View": [ViewSupport],
    "DDL - Schema & Index": [SchemaSupport, IndexSupport],
    "DDL - Sequence & Trigger": [SequenceSupport, TriggerSupport, FunctionSupport],
    "String Matching": [ILIKESupport],
    "MySQL-specific": [
        MySQLTriggerSupport, MySQLTableSupport,
        MySQLSetTypeSupport, MySQLJSONFunctionSupport, MySQLSpatialSupport,
    ],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Execute SQL queries against a MySQL backend.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # Input source arguments
    parser.add_argument(
        'query',
        nargs='?',
        default=None,
        help='SQL query to execute. If not provided, reads from --file or stdin.'
    )
    parser.add_argument(
        '-f', '--file',
        default=None,
        help='Path to a file containing SQL to execute.'
    )
    # Connection parameters
    parser.add_argument(
        '--host',
        default=os.getenv('MYSQL_HOST', 'localhost'),
        help='Database host'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('MYSQL_PORT', '3306')),
        help='Database port'
    )
    parser.add_argument(
        '--database',
        default=os.getenv('MYSQL_DATABASE'),
        help='Database name'
    )
    parser.add_argument(
        '--user',
        default=os.getenv('MYSQL_USER', 'root'),
        help='Database user'
    )
    parser.add_argument(
        '--password',
        default=os.getenv('MYSQL_PASSWORD', ''),
        help='Database password'
    )
    parser.add_argument(
        '--charset',
        default=os.getenv('MYSQL_CHARSET', 'utf8mb4'),
        help='Connection charset'
    )

    # Execution options
    parser.add_argument('--use-async', action='store_true', help='Use asynchronous backend')

    # Output and logging options
    parser.add_argument(
        '--output',
        choices=['table', 'json', 'csv', 'tsv'],
        default='table',
        help='Output format. Defaults to "table" if rich is installed.'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        help='Set logging level (e.g., DEBUG, INFO)'
    )
    parser.add_argument(
        '--rich-ascii',
        action='store_true',
        help='Use ASCII characters for rich table borders.'
    )

    # Info display options
    parser.add_argument(
        '--info',
        action='store_true',
        help='Display MySQL environment information.'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity. -v for families, -vv for details.'
    )
    parser.add_argument(
        '--version',
        type=str,
        default=None,
        help='MySQL version to simulate (e.g., "8.0.0", "5.7.8"). Default: 8.0.0.'
    )

    return parser.parse_args()


def get_provider(args):
    """Factory function to get the correct output provider."""
    output_format = args.output
    if output_format == 'table' and not RICH_AVAILABLE:
        output_format = 'json'

    if output_format == 'table' and RICH_AVAILABLE:
        from rich.console import Console
        return RichOutputProvider(console=Console(), ascii_borders=args.rich_ascii)
    if output_format == 'json':
        return JsonOutputProvider()
    if output_format == 'csv':
        return CsvOutputProvider()
    if output_format == 'tsv':
        return TsvOutputProvider()

    return JsonOutputProvider()


def get_protocol_support_methods(protocol_class: type) -> List[str]:
    """Get all support check methods from a protocol class.

    Supports both 'supports_*' and 'is_*_available' naming patterns.
    """
    methods = []
    for name, member in inspect.getmembers(protocol_class):
        is_supports = name.startswith('supports_')
        is_available = (name.startswith('is_') and name.endswith('_available'))
        if callable(member) and (is_supports or is_available):
            methods.append(name)
    return sorted(methods)


# All possible test arguments for methods that require parameters
# This allows detailed display of which specific arguments are supported
SUPPORT_METHOD_ALL_ARGS: Dict[str, List[str]] = {
    # ExplainSupport: all possible format types
    'supports_explain_format': ['TEXT', 'JSON', 'TREE', 'XML', 'YAML', 'DOT'],
    # MySQLJSONFunctionSupport: JSON functions with version-specific support
    'supports_json_function': [
        'JSON_EXTRACT', 'JSON_ARRAY', 'JSON_OBJECT', 'JSON_MERGE',
        'JSON_TABLE', 'JSON_VALUE', 'JSON_SCHEMA_VALID', 'JSON_MERGE_PATCH'
    ],
    # MySQLSpatialSupport: spatial types
    'supports_spatial_type': [
        'GEOMETRY', 'POINT', 'LINESTRING', 'POLYGON',
        'MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON', 'GEOMETRYCOLLECTION'
    ],
}


def check_protocol_support(dialect: MySQLDialect, protocol_class: type) -> Dict[str, Any]:
    """Check all support methods for a protocol against the dialect.

    For methods requiring parameters, tests all possible arguments.

    Returns:
        Dict with method names as keys. For no-arg methods: bool value.
        For methods with parameters: dict with 'supported', 'total', 'args' keys.
    """
    results = {}
    methods = get_protocol_support_methods(protocol_class)
    for method_name in methods:
        if hasattr(dialect, method_name):
            try:
                method = getattr(dialect, method_name)
                # Check if method requires arguments (beyond self)
                sig = inspect.signature(method)
                params = [p for p in sig.parameters.values()
                          if p.default == inspect.Parameter.empty]
                required_params = [p for p in params if p.name != 'self']

                if len(required_params) == 0:
                    # No required parameters, call directly
                    result = method()
                    results[method_name] = bool(result)
                elif method_name in SUPPORT_METHOD_ALL_ARGS:
                    # Test all possible arguments
                    all_args = SUPPORT_METHOD_ALL_ARGS[method_name]
                    arg_results = {}
                    for arg in all_args:
                        try:
                            arg_results[arg] = bool(method(arg))
                        except Exception:
                            arg_results[arg] = False
                    supported_count = sum(1 for v in arg_results.values() if v)
                    results[method_name] = {
                        'supported': supported_count,
                        'total': len(all_args),
                        'args': arg_results
                    }
                else:
                    # Unknown method requiring parameters, skip
                    results[method_name] = False
            except Exception:
                results[method_name] = False
        else:
            results[method_name] = False
    return results


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse version string like '8.0.0' to tuple."""
    parts = version_str.split('.')
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return (major, minor, patch)


def display_info(verbose: int = 0, output_format: str = 'table',
                 version_str: Optional[str] = None):
    """Display MySQL environment information."""
    # Parse version
    if version_str:
        version = parse_version(version_str)
    else:
        version = (8, 0, 0)  # Default version

    dialect = MySQLDialect(version=version)
    version_display = f"{version[0]}.{version[1]}.{version[2]}"

    # Unified structure for JSON output
    info = {
        "database": {
            "type": "mysql",
            "version": version_display,
            "version_tuple": list(version),
        },
        "features": {},
        "protocols": {}
    }

    for group_name, protocols in PROTOCOL_FAMILY_GROUPS.items():
        info["protocols"][group_name] = {}
        for protocol in protocols:
            protocol_name = protocol.__name__
            support_methods = check_protocol_support(dialect, protocol)

            # Calculate supported/total counts
            # For no-arg methods: value is bool
            # For methods with parameters: value is dict with 'supported', 'total', 'args'
            supported_count = 0
            total_count = 0
            for _method_name, value in support_methods.items():
                if isinstance(value, dict):
                    supported_count += value['supported']
                    total_count += value['total']
                else:
                    total_count += 1
                    if value:
                        supported_count += 1

            if verbose >= 2:
                info["protocols"][group_name][protocol_name] = {
                    "supported": supported_count,
                    "total": total_count,
                    "percentage": (round(supported_count / total_count * 100, 1)
                                   if total_count > 0 else 0),
                    "methods": support_methods
                }
            else:
                info["protocols"][group_name][protocol_name] = {
                    "supported": supported_count,
                    "total": total_count,
                    "percentage": (round(supported_count / total_count * 100, 1)
                                   if total_count > 0 else 0)
                }

    if output_format == 'json' or not RICH_AVAILABLE:
        print(json.dumps(info, indent=2))
    else:
        # Use legacy structure for rich display
        info_legacy = {
            "mysql": info["database"],
            "protocols": info["protocols"]
        }
        _display_info_rich(info_legacy, verbose, version_display)

    return info


def _display_info_rich(info: Dict, verbose: int, version_display: str):
    """Display info using rich console."""
    from rich.console import Console

    console = Console(force_terminal=True)

    SYM_OK = "[OK]"
    SYM_PARTIAL = "[~]"
    SYM_FAIL = "[X]"

    console.print("\n[bold cyan]MySQL Environment Information[/bold cyan]\n")

    console.print(f"[bold]MySQL Version:[/bold] {version_display}\n")

    label = 'Detailed' if verbose >= 2 else 'Family Overview'
    console.print(f"[bold green]Protocol Support ({label}):[/bold green]")

    for group_name, protocols in info["protocols"].items():
        # Mark dialect-specific groups
        if group_name in DIALECT_SPECIFIC_GROUPS:
            console.print(f"\n  [bold underline]{group_name}:[/bold underline] [dim](dialect-specific)[/dim]")
        else:
            console.print(f"\n  [bold underline]{group_name}:[/bold underline]")
        for protocol_name, stats in protocols.items():
            pct = stats["percentage"]
            if pct == 100:
                color = "green"
                symbol = SYM_OK
            elif pct >= 50:
                color = "yellow"
                symbol = SYM_PARTIAL
            elif pct > 0:
                color = "red"
                symbol = SYM_PARTIAL
            else:
                color = "red"
                symbol = SYM_FAIL

            bar_len = 20
            filled = int(pct / 100 * bar_len)
            progress_bar = "#" * filled + "-" * (bar_len - filled)

            sup = stats['supported']
            tot = stats['total']
            console.print(
                f"    [{color}]{symbol}[/{color}] {protocol_name}: "
                f"[{color}]{progress_bar}[/{color}] {pct:.0f}% ({sup}/{tot})"
            )

            if verbose >= 2 and "methods" in stats:
                for method, value in stats["methods"].items():
                    # Format method name for display
                    method_display = (
                        method.replace("supports_", "")
                        .replace("_", " ")
                        .replace("is_", "")
                        .replace("_available", "")
                    )
                    if isinstance(value, dict):
                        # Method with parameters - show each arg's support
                        console.print(f"        [dim]{method_display}:[/dim]")
                        for arg, supported in value.get('args', {}).items():
                            m_status = "[green][OK][/green]" if supported else "[red][X][/red]"
                            console.print(f"            {m_status} {arg}")
                    else:
                        # No-arg method
                        m_status = "[green][OK][/green]" if value else "[red][X][/red]"
                        console.print(f"        {m_status} {method_display}")

    console.print()


def execute_query_sync(sql_query: str, backend: MySQLBackend,
                       provider: Any, **kwargs):
    """Execute a SQL query synchronously."""
    try:
        backend.connect()
        provider.display_query(sql_query, is_async=False)
        result = backend.execute(sql_query)

        if not result:
            provider.display_no_result_object()
        else:
            provider.display_success(result.affected_rows, result.duration)
            if result.data:
                provider.display_results(result.data, **kwargs)
            else:
                provider.display_no_data()

    except ConnectionError as e:
        provider.display_connection_error(e)
        sys.exit(1)
    except QueryError as e:
        provider.display_query_error(e)
        sys.exit(1)
    except Exception as e:
        provider.display_unexpected_error(e, is_async=False)
        sys.exit(1)
    finally:
        if backend._connection:  # type: ignore
            backend.disconnect()
            provider.display_disconnect(is_async=False)


async def execute_query_async(sql_query: str, backend: AsyncMySQLBackend,
                              provider: Any, **kwargs):
    """Execute a SQL query asynchronously."""
    try:
        await backend.connect()
        provider.display_query(sql_query, is_async=True)
        result = await backend.execute(sql_query)

        if not result:
            provider.display_no_result_object()
        else:
            provider.display_success(result.affected_rows, result.duration)
            if result.data:
                provider.display_results(result.data, **kwargs)
            else:
                provider.display_no_data()

    except ConnectionError as e:
        provider.display_connection_error(e)
        sys.exit(1)
    except QueryError as e:
        provider.display_query_error(e)
        sys.exit(1)
    except Exception as e:
        provider.display_unexpected_error(e, is_async=True)
        sys.exit(1)
    finally:
        if backend._connection:  # type: ignore
            await backend.disconnect()
            provider.display_disconnect(is_async=True)


def main():
    args = parse_args()

    if args.info:
        output_format = args.output if args.output != 'table' or RICH_AVAILABLE else 'json'

        # Try to connect and get real version if database is provided
        actual_version = args.version

        if args.database:
            try:
                config = MySQLConnectionConfig(
                    host=args.host, port=args.port, database=args.database,
                    username=args.user, password=args.password, charset=args.charset,
                )
                backend = MySQLBackend(connection_config=config)
                backend.connect()
                backend.introspect_and_adapt()

                # Get actual version
                version_tuple = backend.get_server_version()
                if version_tuple:
                    actual_version = f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"

                backend.disconnect()
            except Exception as e:
                logger.warning("Could not connect to database for introspection: %s", e)
                # Fall back to command-line version or default

        display_info(verbose=args.verbose, output_format=output_format,
                     version_str=actual_version)
        return

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    provider = get_provider(args)

    if RICH_AVAILABLE and isinstance(provider, RichOutputProvider):
        from rich.console import Console
        handler = RichHandler(
            rich_tracebacks=True,
            show_path=False,
            console=Console(stderr=True)
        )
        logging.basicConfig(
            level=numeric_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[handler]
        )
    else:
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )

    provider.display_greeting()

    sql_source = None
    if args.query:
        sql_source = args.query
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                sql_source = f.read()
        except FileNotFoundError:
            logger.error(f"Error: File not found at {args.file}")
            sys.exit(1)
    elif not sys.stdin.isatty():
        sql_source = sys.stdin.read()

    if not sql_source:
        msg = "Error: No SQL query provided. Use query argument, --file, or stdin."
        print(msg, file=sys.stderr)
        sys.exit(1)

    # Ensure only one statement is provided
    if ';' in sql_source.strip().rstrip(';'):
        logger.error("Error: Multiple SQL statements are not supported.")
        sys.exit(1)

    config = MySQLConnectionConfig(
        host=args.host, port=args.port, database=args.database,
        username=args.user, password=args.password, charset=args.charset,
    )

    kwargs = {'use_ascii': args.rich_ascii}
    if args.use_async:
        backend = AsyncMySQLBackend(connection_config=config)
        asyncio.run(execute_query_async(sql_source, backend, provider, **kwargs))
    else:
        backend = MySQLBackend(connection_config=config)
        execute_query_sync(sql_source, backend, provider, **kwargs)


if __name__ == "__main__":
    main()
