# src/rhosocial/activerecord/backend/impl/mysql/__main__.py
import argparse
import asyncio
import datetime
import decimal
import logging
import json
import os
import sys

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.logging import RichHandler
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .backend import MySQLBackend, AsyncMySQLBackend
from .config import MySQLConnectionConfig
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError


logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Execute SQL queries against a MySQL backend.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Connection parameters with defaults from environment variables
    parser.add_argument(
        '--host',
        default=os.getenv('MYSQL_HOST', 'localhost'),
        help='Database host (default: MYSQL_HOST environment variable or localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('MYSQL_PORT', 3306)),
        help='Database port (default: MYSQL_PORT environment variable or 3306)'
    )
    parser.add_argument(
        '--database',
        default=os.getenv('MYSQL_DATABASE'),
        help='Database name (optional, default: MYSQL_DATABASE environment variable)'
    )
    parser.add_argument(
        '--user',
        default=os.getenv('MYSQL_USER', 'root'),
        help='Database user (default: MYSQL_USER environment variable or root)'
    )
    parser.add_argument(
        '--password',
        default=os.getenv('MYSQL_PASSWORD', ''),
        help='Database password (default: MYSQL_PASSWORD environment variable or empty string)'
    )
    parser.add_argument(
        '--charset',
        default=os.getenv('MYSQL_CHARSET', 'utf8mb4'),
        help='Connection charset (default: MYSQL_CHARSET environment variable or utf8mb4)'
    )

    # Positional argument for the SQL query
    parser.add_argument(
        'query', # Changed to positional argument
        help='SQL query to execute. Must be enclosed in quotes.'
    )
    
    parser.add_argument('--use-async', action='store_true', help='Use asynchronous backend')
    parser.add_argument('--log-level', default='INFO', help='Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    parser.add_argument('--rich-ascii', action='store_true', help='Use ASCII characters for rich table borders.')

    return parser.parse_args()

def execute_query_sync(args, backend):
    try:
        backend.connect()
        if RICH_AVAILABLE:
            Console().print(f"Executing synchronous query: [bold cyan]{args.query}[/bold cyan]")
        else:
            logger.info(f"Executing synchronous query: {args.query}")
        result = backend.execute(args.query)
        handle_result(args, result)
    except ConnectionError as e:
        if RICH_AVAILABLE:
            Console().print(Panel(f"[bold]Database Connection Error[/bold]\n[red]{e}[/red]", title="[bold red]Error[/bold red]", border_style="red"))
        else:
            logger.error(f"Database connection error: {e}")
        sys.exit(1)
    except QueryError as e:
        if RICH_AVAILABLE:
            Console().print(Panel(f"[bold]Database Query Error[/bold]\n[red]{e}[/red]", title="[bold red]Error[/bold red]", border_style="red"))
        else:
            logger.error(f"Database query error: {e}")
        sys.exit(1)
    except Exception as e:
        if RICH_AVAILABLE:
            Console().print(Panel(f"[bold]An unexpected error occurred during synchronous execution[/bold]\n[red]{e}[/red]", title="[bold red]Error[/bold red]", border_style="red"))
        else:
            logger.error(f"An unexpected error occurred during synchronous execution: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if backend._connection:
            backend.disconnect()
            if RICH_AVAILABLE:
                Console().print("[dim]Disconnected from database (synchronous).[/dim]")
            else:
                logger.info("Disconnected from database (synchronous).")

async def execute_query_async(args, backend):
    try:
        await backend.connect()
        if RICH_AVAILABLE:
            Console().print(f"Executing asynchronous query: [bold cyan]{args.query}[/bold cyan]")
        else:
            logger.info(f"Executing asynchronous query: {args.query}")
        result = await backend.execute(args.query)
        handle_result(args, result)
    except ConnectionError as e:
        if RICH_AVAILABLE:
            Console().print(Panel(f"[bold]Database Connection Error[/bold]\n[red]{e}[/red]", title="[bold red]Error[/bold red]", border_style="red"))
        else:
            logger.error(f"Database connection error: {e}")
        sys.exit(1)
    except QueryError as e:
        if RICH_AVAILABLE:
            Console().print(Panel(f"[bold]Database Query Error[/bold]\n[red]{e}[/red]", title="[bold red]Error[/bold red]", border_style="red"))
        else:
            logger.error(f"Database query error: {e}")
        sys.exit(1)
    except Exception as e:
        if RICH_AVAILABLE:
            Console().print(Panel(f"[bold]An unexpected error occurred during asynchronous execution[/bold]\n[red]{e}[/red]", title="[bold red]Error[/bold red]", border_style="red"))
        else:
            logger.error(f"An unexpected error occurred during asynchronous execution: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if backend._connection:
            await backend.disconnect()
            if RICH_AVAILABLE:
                Console().print("[dim]Disconnected from database (asynchronous).[/dim]")
            else:
                logger.info("Disconnected from database (asynchronous).")

def json_serializer(obj):
    """Handles serialization of types not supported by default JSON encoder."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, datetime.timedelta):
        return str(obj)
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def handle_result(args, result):
    if not result:
        if RICH_AVAILABLE:
            Console().print("[yellow]Query executed, but no result object returned.[/yellow]")
        else:
            logger.info("Query executed, but no result object returned.")
        return

    if RICH_AVAILABLE:
        console = Console()
        console.print(f"[bold green]Query executed successfully.[/bold green] "
                      f"Affected rows: [bold cyan]{result.affected_rows}[/bold cyan], "
                      f"Duration: [bold cyan]{result.duration:.4f}s[/bold cyan]")
        if result.data:
            # Ensure data is a list of dicts
            if not isinstance(result.data, list) or not result.data or not all(isinstance(i, dict) for i in result.data):
                console.print(result.data)
                return

            box_style = box.ASCII if args.rich_ascii else box.SQUARE
            table = Table(show_header=True, header_style="bold magenta", box=box_style)
            headers = result.data[0].keys()
            for header in headers:
                table.add_column(header, style="dim", overflow="fold")
            
            for row in result.data:
                table.add_row(*(str(v) for v in row.values()))
            
            console.print(table)
        else:
            console.print("[yellow]No data returned.[/yellow]")
    else:
        logger.info(f"Query executed successfully. Affected rows: {result.affected_rows}, Duration: {result.duration:.4f}s")
        if result.data:
            logger.info("Results:")
            for row in result.data:
                if isinstance(row, (dict, list)):
                    print(json.dumps(row, indent=2, ensure_ascii=False, default=json_serializer))
                else:
                    print(row)
        else:
            logger.info("No data returned.")

def main():
    args = parse_args()

    # Set logging level
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    if RICH_AVAILABLE:
        logging.basicConfig(
            level=numeric_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
        )
        Console().print("[bold green]Rich library detected. Logging and output are beautified.[/bold green]")
    else:
        logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s')
        print("Rich library not found. We recommend installing rich for a more user-friendly output.")

    config = MySQLConnectionConfig(
        host=args.host,
        port=args.port,
        database=args.database,
        username=args.user,
        password=args.password,
        charset=args.charset,
        log_level=numeric_level
    )

    if args.use_async:
        backend = AsyncMySQLBackend(connection_config=config)
        asyncio.run(execute_query_async(args, backend))
    else:
        backend = MySQLBackend(connection_config=config)
        execute_query_sync(args, backend)

if __name__ == "__main__":
    main()