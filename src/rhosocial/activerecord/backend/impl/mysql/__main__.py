# src/rhosocial/activerecord/backend/impl/mysql/__main__.py
import argparse
import asyncio
import logging
import os
import sys

from .backend import MySQLBackend, AsyncMySQLBackend
from .config import MySQLConnectionConfig
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError
from rhosocial.activerecord.backend.output import JsonOutputProvider, CsvOutputProvider, TsvOutputProvider

# Attempt to import rich for formatted output
try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rhosocial.activerecord.backend.output_rich import RichOutputProvider
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    RichOutputProvider = None

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Execute a single SQL query against a MySQL backend.",
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
        help='Path to a file containing a single SQL query to execute.'
    )
    # Connection parameters
    parser.add_argument('--host', default=os.getenv('MYSQL_HOST', 'localhost'), help='Database host')
    parser.add_argument('--port', type=int, default=int(os.getenv('MYSQL_PORT', 3306)), help='Database port')
    parser.add_argument('--database', default=os.getenv('MYSQL_DATABASE'), help='Database name')
    parser.add_argument('--user', default=os.getenv('MYSQL_USER', 'root'), help='Database user')
    parser.add_argument('--password', default=os.getenv('MYSQL_PASSWORD', ''), help='Database password')
    parser.add_argument('--charset', default=os.getenv('MYSQL_CHARSET', 'utf8mb4'), help='Connection charset')
    
    # Execution options
    parser.add_argument('--use-async', action='store_true', help='Use asynchronous backend')

    # Output and logging options
    parser.add_argument(
        '--output',
        choices=['table', 'json', 'csv', 'tsv'],
        default='table',
        help='Output format. Defaults to "table" if rich is installed, otherwise "json".'
    )
    parser.add_argument('--log-level', default='INFO', help='Set logging level (e.g., DEBUG, INFO)')
    parser.add_argument('--rich-ascii', action='store_true', help='Use ASCII characters for rich table borders.')

    return parser.parse_args()


def get_provider(args):
    """Factory function to get the correct output provider."""
    output_format = args.output
    if output_format == 'table' and not RICH_AVAILABLE:
        output_format = 'json'

    if output_format == 'table':
        return RichOutputProvider(console=Console(), ascii_borders=args.rich_ascii)
    if output_format == 'json':
        return JsonOutputProvider()
    if output_format == 'csv':
        return CsvOutputProvider()
    if output_format == 'tsv':
        return TsvOutputProvider()
    
    return JsonOutputProvider()


def execute_query_sync(sql_query: str, backend: MySQLBackend, provider: 'OutputProvider', **kwargs):
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
        if backend._connection:
            backend.disconnect()
            provider.display_disconnect(is_async=False)


async def execute_query_async(sql_query: str, backend: AsyncMySQLBackend, provider: 'OutputProvider', **kwargs):
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
        if backend._connection:
            await backend.disconnect()
            provider.display_disconnect(is_async=True)


def main():
    args = parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    provider = get_provider(args)

    if isinstance(provider, RichOutputProvider):
        logging.basicConfig(
            level=numeric_level, format="%(message)s", datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_path=False, console=Console(stderr=True))]
        )
    else:
        logging.basicConfig(
            level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s',
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
        print("Error: No SQL query provided. Use the query argument, --file flag, or pipe from stdin.", file=sys.stderr)
        sys.exit(1)
    
    # Ensure only one statement is provided, as multi-statement execution is not supported
    if ';' in sql_source.strip().rstrip(';'):
        logger.error("Error: Multiple SQL statements are not supported. Please provide a single query.")
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