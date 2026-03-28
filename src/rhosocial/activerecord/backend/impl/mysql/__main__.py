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
from dataclasses import asdict, is_dataclass
from enum import Enum
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

# Supported introspection types for CLI
INTROSPECT_TYPES = [
    "tables", "views", "table", "columns",
    "indexes", "foreign-keys", "triggers", "database"
]


def _serialize_for_output(obj: Any) -> Any:
    """Serialize object for JSON output, handling non-serializable types.

    Handles Pydantic models, dataclasses, Enums, and nested structures.
    """
    if obj is None:
        return None
    if hasattr(obj, 'model_dump'):
        # Pydantic model
        try:
            result = obj.model_dump(mode='json')
            return _serialize_for_output(result)
        except TypeError:
            result = obj.model_dump()
            return _serialize_for_output(result)
    if is_dataclass(obj) and not isinstance(obj, type):
        # Dataclass instance
        return {k: _serialize_for_output(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _serialize_for_output(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize_for_output(item) for item in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    # Fallback: convert to string
    return str(obj)


def parse_args():
    # =========================================================================
    # Design Notes:
    # =========================================================================
    # Uses explicit subcommand mode: query and introspect are mutually exclusive.
    # This avoids argparse misidentifying SQL queries as subcommand names.
    #
    # Connection parameters are shared between subcommands and placed in parent parser.
    # The main parser also inherits from parent, so global options like --info
    # can access these parameters.
    # =========================================================================

    # Parent parser: shared connection parameters
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        '--host',
        default=os.getenv('MYSQL_HOST', 'localhost'),
        help='Database host'
    )
    parent_parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('MYSQL_PORT', '3306')),
        help='Database port'
    )
    parent_parser.add_argument(
        '--database',
        default=os.getenv('MYSQL_DATABASE'),
        help='Database name (optional for some operations like SHOW DATABASES)'
    )
    parent_parser.add_argument(
        '--user',
        default=os.getenv('MYSQL_USER', 'root'),
        help='Database user'
    )
    parent_parser.add_argument(
        '--password',
        default=os.getenv('MYSQL_PASSWORD', ''),
        help='Database password'
    )
    parent_parser.add_argument(
        '--charset',
        default=os.getenv('MYSQL_CHARSET', 'utf8mb4'),
        help='Connection charset'
    )
    parent_parser.add_argument(
        '--output',
        choices=['table', 'json', 'csv', 'tsv'],
        default='table',
        help='Output format. Defaults to "table" if rich is installed.'
    )
    parent_parser.add_argument(
        '--log-level',
        default='INFO',
        help='Set logging level (e.g., DEBUG, INFO)'
    )
    parent_parser.add_argument(
        '--rich-ascii',
        action='store_true',
        help='Use ASCII characters for rich table borders.'
    )
    parent_parser.add_argument(
        '--use-async',
        action='store_true',
        help='Use asynchronous backend'
    )
    parent_parser.add_argument(
        '--version',
        type=str,
        default=None,
        help='MySQL version to simulate (e.g., "8.0.0", "5.7.8"). Default: 8.0.0.'
    )

    # Main parser inherits from parent, so --info can access shared parameters
    parser = argparse.ArgumentParser(
        description="Execute SQL queries against a MySQL backend.",
        formatter_class=argparse.RawTextHelpFormatter,
        parents=[parent_parser]
    )

    # Global options (no subcommand required)
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

    # Subcommands: query and introspect
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # query subcommand
    query_parser = subparsers.add_parser(
        'query',
        help='Execute SQL query',
        parents=[parent_parser]
    )
    query_parser.add_argument(
        'sql',
        nargs='?',
        default=None,
        help='SQL query to execute. If not provided, reads from --file or stdin.'
    )
    query_parser.add_argument(
        '-f', '--file',
        default=None,
        help='Path to a file containing SQL to execute.'
    )

    # introspect subcommand
    introspect_parser = subparsers.add_parser(
        'introspect',
        help='Database introspection commands',
        parents=[parent_parser]
    )
    introspect_parser.add_argument(
        'type',
        choices=INTROSPECT_TYPES,
        help='Introspection type: tables, views, table, columns, indexes, foreign-keys, triggers, database'
    )
    introspect_parser.add_argument(
        'name',
        nargs='?',
        default=None,
        help='Table/view name (required for table, columns, indexes, foreign-keys types)'
    )
    introspect_parser.add_argument(
        '--schema',
        default=None,
        help='Schema name (for databases that support schemas)'
    )
    introspect_parser.add_argument(
        '--include-system',
        action='store_true',
        help='Include system tables in output'
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


def _calculate_protocol_stats(support_methods: Dict[str, Any]) -> Tuple[int, int]:
    """Calculate supported and total counts from support methods.

    Args:
        support_methods: Dict with method names as keys.
            For no-arg methods: bool value.
            For methods with parameters: dict with 'supported', 'total', 'args' keys.

    Returns:
        Tuple of (supported_count, total_count)
    """
    supported_count = 0
    total_count = 0
    for value in support_methods.values():
        if isinstance(value, dict):
            supported_count += value['supported']
            total_count += value['total']
        else:
            total_count += 1
            if value:
                supported_count += 1
    return supported_count, total_count


def _build_protocol_info(
    dialect: MySQLDialect,
    group_name: str,
    protocols: List[type],
    verbose: int
) -> Dict[str, Dict[str, Any]]:
    """Build protocol support information for a single group.

    Args:
        dialect: MySQLDialect instance to check against
        group_name: Name of the protocol group
        protocols: List of protocol classes in this group
        verbose: Verbosity level for output detail

    Returns:
        Dict mapping protocol names to their support statistics
    """
    group_info = {}
    for protocol in protocols:
        protocol_name = protocol.__name__
        support_methods = check_protocol_support(dialect, protocol)
        supported_count, total_count = _calculate_protocol_stats(support_methods)

        percentage = round(supported_count / total_count * 100, 1) if total_count > 0 else 0

        if verbose >= 2:
            group_info[protocol_name] = {
                "supported": supported_count,
                "total": total_count,
                "percentage": percentage,
                "methods": support_methods
            }
        else:
            group_info[protocol_name] = {
                "supported": supported_count,
                "total": total_count,
                "percentage": percentage
            }
    return group_info


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

    # Build protocol support information
    for group_name, protocols in PROTOCOL_FAMILY_GROUPS.items():
        info["protocols"][group_name] = _build_protocol_info(
            dialect, group_name, protocols, verbose
        )

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


def _get_status_style(pct: float) -> Tuple[str, str]:
    """Get color and symbol based on percentage.

    Args:
        pct: Percentage value (0-100)

    Returns:
        Tuple of (color, symbol) for rich display
    """
    SYM_OK = "[OK]"
    SYM_PARTIAL = "[~]"
    SYM_FAIL = "[X]"

    if pct == 100:
        return "green", SYM_OK
    elif pct >= 50:
        return "yellow", SYM_PARTIAL
    elif pct > 0:
        return "red", SYM_PARTIAL
    else:
        return "red", SYM_FAIL


def _format_method_display(method: str) -> str:
    """Format method name for display.

    Args:
        method: Original method name

    Returns:
        Human-readable method name
    """
    return (
        method.replace("supports_", "")
        .replace("_", " ")
        .replace("is_", "")
        .replace("_available", "")
    )


def _display_method_details(console: Any, method: str, value: Any) -> None:
    """Display detailed method support information.

    Args:
        console: Rich console instance
        method: Method name
        value: Support value (bool or dict with args)
    """
    method_display = _format_method_display(method)

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


def _display_protocol_item(
    console: Any,
    protocol_name: str,
    stats: Dict[str, Any],
    verbose: int
) -> None:
    """Display a single protocol's support information.

    Args:
        console: Rich console instance
        protocol_name: Name of the protocol
        stats: Support statistics dict
        verbose: Verbosity level
    """
    pct = stats["percentage"]
    color, symbol = _get_status_style(pct)

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
            _display_method_details(console, method, value)


def _display_protocol_group(
    console: Any,
    group_name: str,
    protocols: Dict[str, Any],
    verbose: int
) -> None:
    """Display a protocol group's support information.

    Args:
        console: Rich console instance
        group_name: Name of the protocol group
        protocols: Dict mapping protocol names to their stats
        verbose: Verbosity level
    """
    # Mark dialect-specific groups
    if group_name in DIALECT_SPECIFIC_GROUPS:
        console.print(f"\n  [bold underline]{group_name}:[/bold underline] [dim](dialect-specific)[/dim]")
    else:
        console.print(f"\n  [bold underline]{group_name}:[/bold underline]")

    for protocol_name, stats in protocols.items():
        _display_protocol_item(console, protocol_name, stats, verbose)


def _display_info_rich(info: Dict, verbose: int, version_display: str):
    """Display info using rich console."""
    from rich.console import Console

    console = Console(force_terminal=True)

    console.print("\n[bold cyan]MySQL Environment Information[/bold cyan]\n")

    console.print(f"[bold]MySQL Version:[/bold] {version_display}\n")

    label = 'Detailed' if verbose >= 2 else 'Family Overview'
    console.print(f"[bold green]Protocol Support ({label}):[/bold green]")

    for group_name, protocols in info["protocols"].items():
        _display_protocol_group(console, group_name, protocols, verbose)

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


def handle_introspect_sync(args, backend: MySQLBackend, provider: Any):
    """Handle introspect subcommand synchronously."""
    try:
        backend.connect()

        introspector = backend.introspector

        if args.type == "tables":
            tables = introspector.list_tables(
                schema=args.schema,
                include_system=args.include_system
            )
            data = _serialize_for_output(tables)
            provider.display_results(data, title="Tables")

        elif args.type == "views":
            views = introspector.list_views(schema=args.schema)
            data = _serialize_for_output(views)
            provider.display_results(data, title="Views")

        elif args.type == "table":
            if not args.name:
                print("Error: Table name is required for 'table' introspection", file=sys.stderr)
                sys.exit(1)
            info = introspector.get_table_info(args.name, schema=args.schema)
            if info:
                # Display columns
                provider.display_results(_serialize_for_output(info.columns), title=f"Columns of {args.name}")
                # Display indexes
                if info.indexes:
                    provider.display_results(_serialize_for_output(info.indexes), title=f"Indexes of {args.name}")
                # Display foreign keys
                if info.foreign_keys:
                    provider.display_results(_serialize_for_output(info.foreign_keys), title=f"Foreign Keys of {args.name}")
            else:
                print(f"Error: Table '{args.name}' not found", file=sys.stderr)
                sys.exit(1)

        elif args.type == "columns":
            if not args.name:
                print("Error: Table name is required for 'columns' introspection", file=sys.stderr)
                sys.exit(1)
            columns = introspector.list_columns(args.name, schema=args.schema)
            data = _serialize_for_output(columns)
            provider.display_results(data, title=f"Columns of {args.name}")

        elif args.type == "indexes":
            if not args.name:
                print("Error: Table name is required for 'indexes' introspection", file=sys.stderr)
                sys.exit(1)
            indexes = introspector.list_indexes(args.name, schema=args.schema)
            data = _serialize_for_output(indexes)
            provider.display_results(data, title=f"Indexes of {args.name}")

        elif args.type == "foreign-keys":
            if not args.name:
                print("Error: Table name is required for 'foreign-keys' introspection", file=sys.stderr)
                sys.exit(1)
            fks = introspector.list_foreign_keys(args.name, schema=args.schema)
            data = _serialize_for_output(fks)
            provider.display_results(data, title=f"Foreign Keys of {args.name}")

        elif args.type == "triggers":
            triggers = introspector.list_triggers(
                table_name=args.name,
                schema=args.schema
            )
            data = _serialize_for_output(triggers)
            provider.display_results(data, title="Triggers")

        elif args.type == "database":
            info = introspector.get_database_info()
            data = _serialize_for_output(info)
            provider.display_results([data], title="Database Info")

    except ConnectionError as e:
        provider.display_connection_error(e)
        sys.exit(1)
    except QueryError as e:
        provider.display_query_error(e)
        sys.exit(1)
    except Exception as e:
        print(f"Error during introspection: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if backend._connection:  # type: ignore
            backend.disconnect()


async def handle_introspect_async(args, backend: AsyncMySQLBackend, provider: Any):
    """Handle introspect subcommand asynchronously."""
    try:
        await backend.connect()

        introspector = backend.introspector

        if args.type == "tables":
            tables = await introspector.list_tables_async(
                schema=args.schema,
                include_system=args.include_system
            )
            data = _serialize_for_output(tables)
            provider.display_results(data, title="Tables")

        elif args.type == "views":
            views = await introspector.list_views_async(schema=args.schema)
            data = _serialize_for_output(views)
            provider.display_results(data, title="Views")

        elif args.type == "table":
            if not args.name:
                print("Error: Table name is required for 'table' introspection", file=sys.stderr)
                sys.exit(1)
            info = await introspector.get_table_info_async(args.name, schema=args.schema)
            if info:
                # Display columns
                provider.display_results(_serialize_for_output(info.columns), title=f"Columns of {args.name}")
                # Display indexes
                if info.indexes:
                    provider.display_results(_serialize_for_output(info.indexes), title=f"Indexes of {args.name}")
                # Display foreign keys
                if info.foreign_keys:
                    provider.display_results(_serialize_for_output(info.foreign_keys), title=f"Foreign Keys of {args.name}")
            else:
                print(f"Error: Table '{args.name}' not found", file=sys.stderr)
                sys.exit(1)

        elif args.type == "columns":
            if not args.name:
                print("Error: Table name is required for 'columns' introspection", file=sys.stderr)
                sys.exit(1)
            columns = await introspector.list_columns_async(args.name, schema=args.schema)
            data = _serialize_for_output(columns)
            provider.display_results(data, title=f"Columns of {args.name}")

        elif args.type == "indexes":
            if not args.name:
                print("Error: Table name is required for 'indexes' introspection", file=sys.stderr)
                sys.exit(1)
            indexes = await introspector.list_indexes_async(args.name, schema=args.schema)
            data = _serialize_for_output(indexes)
            provider.display_results(data, title=f"Indexes of {args.name}")

        elif args.type == "foreign-keys":
            if not args.name:
                print("Error: Table name is required for 'foreign-keys' introspection", file=sys.stderr)
                sys.exit(1)
            fks = await introspector.list_foreign_keys_async(args.name, schema=args.schema)
            data = _serialize_for_output(fks)
            provider.display_results(data, title=f"Foreign Keys of {args.name}")

        elif args.type == "triggers":
            triggers = await introspector.list_triggers_async(
                table_name=args.name,
                schema=args.schema
            )
            data = _serialize_for_output(triggers)
            provider.display_results(data, title="Triggers")

        elif args.type == "database":
            info = await introspector.get_database_info_async()
            data = _serialize_for_output(info)
            provider.display_results([data], title="Database Info")

    except ConnectionError as e:
        provider.display_connection_error(e)
        sys.exit(1)
    except QueryError as e:
        provider.display_query_error(e)
        sys.exit(1)
    except Exception as e:
        print(f"Error during introspection: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if backend._connection:  # type: ignore
            await backend.disconnect()


def main():
    args = parse_args()

    # Handle --info flag (global option, no subcommand needed)
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

    # Require a subcommand if --info is not specified
    if args.command is None:
        print("Error: Please specify a command: 'query' or 'introspect'", file=sys.stderr)
        print("Use --help for more information.", file=sys.stderr)
        sys.exit(1)

    # Handle introspect subcommand
    if args.command == "introspect":
        if not args.database:
            print("Error: --database is required for introspection", file=sys.stderr)
            sys.exit(1)

        provider = get_provider(args)
        config = MySQLConnectionConfig(
            host=args.host, port=args.port, database=args.database,
            username=args.user, password=args.password, charset=args.charset,
        )

        if args.use_async:
            backend = AsyncMySQLBackend(connection_config=config)
            asyncio.run(handle_introspect_async(args, backend, provider))
        else:
            backend = MySQLBackend(connection_config=config)
            handle_introspect_sync(args, backend, provider)
        return

    # Handle query subcommand
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
    if args.sql:
        sql_source = args.sql
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
        msg = "Error: No SQL query provided. Use SQL argument, --file, or stdin."
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
