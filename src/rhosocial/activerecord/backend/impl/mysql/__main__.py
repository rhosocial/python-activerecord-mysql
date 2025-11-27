# src/rhosocial/activerecord/backend/impl/mysql/__main__.py
import argparse
import asyncio
import logging
import os
import sys

from .backend import MySQLBackend, AsyncMySQLBackend
from .config import MySQLConnectionConfig
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError
from .output import PlainTextOutputProvider

# Attempt to import rich and the RichOutputProvider
try:
    from rich.console import Console
    from rich.logging import RichHandler
    from .output import RichOutputProvider
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Execute SQL queries against a MySQL backend.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Connection parameters
    parser.add_argument('--host', default=os.getenv('MYSQL_HOST', 'localhost'), help='Database host')
    parser.add_argument('--port', type=int, default=int(os.getenv('MYSQL_PORT', 3306)), help='Database port')
    parser.add_argument('--database', default=os.getenv('MYSQL_DATABASE'), help='Database name')
    parser.add_argument('--user', default=os.getenv('MYSQL_USER', 'root'), help='Database user')
    parser.add_argument('--password', default=os.getenv('MYSQL_PASSWORD', ''), help='Database password')
    parser.add_argument('--charset', default=os.getenv('MYSQL_CHARSET', 'utf8mb4'), help='Connection charset')

    # Execution options
    parser.add_argument('query', help='SQL query to execute. Must be enclosed in quotes.')
    parser.add_argument('--use-async', action='store_true', help='Use asynchronous backend')

    # Output and logging options
    parser.add_argument('--log-level', default='INFO', help='Set logging level (e.g., DEBUG, INFO)')
    parser.add_argument('--plain', action='store_true', help='Use plain text output even if rich is installed.')
    parser.add_argument('--rich-ascii', action='store_true', help='Use ASCII characters for rich table borders.')

    return parser.parse_args()


def execute_query_sync(args, backend, provider):
    try:
        backend.connect()
        provider.display_query(args.query, is_async=False)
        result = backend.execute(args.query)
        handle_result(result, provider, use_ascii=args.rich_ascii)
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


async def execute_query_async(args, backend, provider):
    try:
        await backend.connect()
        provider.display_query(args.query, is_async=True)
        result = await backend.execute(args.query)
        handle_result(result, provider, use_ascii=args.rich_ascii)
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


def handle_result(result, provider, **kwargs):
    if not result:
        provider.display_no_result_object()
        return

    provider.display_success(result.affected_rows, result.duration)
    if result.data:
        provider.display_results(result.data, **kwargs)
    else:
        provider.display_no_data()


def main():
    args = parse_args()

    # Setup logging
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    # Choose output provider
    if RICH_AVAILABLE and not args.plain:
        provider = RichOutputProvider(console=Console(), ascii_borders=args.rich_ascii)
        logging.basicConfig(
            level=numeric_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
        )
    else:
        provider = PlainTextOutputProvider()
        logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s')

    provider.display_greeting()

    # Setup backend
    config = MySQLConnectionConfig(
        host=args.host,
        port=args.port,
        database=args.database,
        username=args.user,
        password=args.password,
        charset=args.charset,
    )

    if args.use_async:
        backend = AsyncMySQLBackend(connection_config=config)
        asyncio.run(execute_query_async(args, backend, provider))
    else:
        backend = MySQLBackend(connection_config=config)
        execute_query_sync(args, backend, provider)


if __name__ == "__main__":
    main()