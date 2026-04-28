# src/rhosocial/activerecord/backend/impl/mysql/cli/connection.py
"""Connection argument parsing and backend creation for MySQL CLI."""

import os



def add_connection_args(parser):
    """Add MySQL connection arguments to a subcommand parser.

    Each subcommand that needs a database connection calls this.
    """
    parser.add_argument(
        "--host",
        default=os.getenv("MYSQL_HOST", "localhost"),
        help="Database host (env: MYSQL_HOST, default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MYSQL_PORT", "3306")),
        help="Database port (env: MYSQL_PORT, default: 3306)",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("MYSQL_DATABASE"),
        help="Database name (env: MYSQL_DATABASE, optional for some operations)",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("MYSQL_USER", "root"),
        help="Database user (env: MYSQL_USER, default: root)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("MYSQL_PASSWORD", ""),
        help="Database password (env: MYSQL_PASSWORD)",
    )
    parser.add_argument(
        "--charset",
        default=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        help="Connection charset (env: MYSQL_CHARSET, default: utf8mb4)",
    )
    parser.add_argument(
        "--use-async",
        action="store_true",
        help="Use asynchronous backend",
    )
    parser.add_argument(
        "--named-connection",
        dest="named_connection",
        metavar="QUALIFIED_NAME",
        help="Named connection from Python module (e.g., myapp.connections.prod_db).",
    )
    parser.add_argument(
        "--conn-param",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        dest="connection_params",
        help="Connection parameter override for named connection. Can be specified multiple times.",
    )


def add_version_arg(parser):
    """Add --version argument (used only by info subcommand)."""
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help='MySQL version to simulate (e.g., "8.0.0", "5.7.8"). Default: 8.0.0.',
    )


def create_connection_parent_parser():
    """Create a parent parser with connection and output arguments.

    Used by shared CLI helpers (named-query, named-procedure) that
    require a parent_parser containing connection parameters.
    """
    import argparse
    parent = argparse.ArgumentParser(add_help=False)
    add_connection_args(parent)
    # Output parameters
    parent.add_argument(
        "-o", "--output",
        choices=["table", "json", "csv", "tsv"],
        default="table",
        help='Output format. Defaults to "table" if rich is installed.',
    )
    parent.add_argument(
        "--rich-ascii",
        action="store_true",
        help="Use ASCII characters for rich table borders.",
    )
    return parent


def resolve_connection_config_from_args(args):
    """Resolve MySQL connection config from parsed args.

    Priority order:
        1. --named-connection + --conn-param
        2. Explicit connection parameters (--host, --port, etc.)
        3. Default values
    """
    from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
    from rhosocial.activerecord.backend.named_connection.cli import parse_params
    from rhosocial.activerecord.backend.named_connection import NamedConnectionResolver

    named_conn = getattr(args, "named_connection", None)
    conn_params = getattr(args, "connection_params", [])

    if conn_params:
        conn_params = parse_params(conn_params)
    else:
        conn_params = {}

    if named_conn:
        resolver = NamedConnectionResolver(named_conn).load()
        if conn_params:
            return resolver.resolve(conn_params)
        return resolver.resolve({})

    # Fallback to explicit connection parameters
    return MySQLConnectionConfig(
        host=args.host or "localhost",
        port=args.port or 3306,
        database=args.database,
        username=args.user,
        password=args.password,
        charset=args.charset,
    )


def create_backend(args):
    """Create, connect, and introspect a MySQL backend from parsed args."""
    from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
    config = resolve_connection_config_from_args(args)
    backend = MySQLBackend(connection_config=config)
    backend.connect()
    backend.introspect_and_adapt()
    return backend
