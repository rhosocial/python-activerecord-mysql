# docs/examples/migration/01_mysql_first_migration.py
"""Function-style migrations on MySQL: dry-run -> UP -> DOWN with version records.

This example demonstrates the MySQL-specific parts of a migration run:
  - building this repo's MySQLBackend / MySQLConnectionConfig and calling
    ``introspect_and_adapt()`` so version-gated DDL matches the live server;
  - an ``@migration``-decorated function that emits DDL with ``ctx.apply(...)``;
  - ``run_migration_group(dry_run=True)`` — essential on MySQL because DDL is
    not transactional and auto-commits (see docs/en_US/migration/README.md);
  - a real UP and DOWN with a ``JSONFileMigrationRecordStore``.

Requires a reachable MySQL server; connection settings come from the
MYSQL_HOST / MYSQL_PORT / MYSQL_DATABASE / MYSQL_USER / MYSQL_PASSWORD
environment variables. It will not run locally without a server.

Run from the repository root with ``PYTHONPATH=src``.
"""

import os
import tempfile
from typing import Annotated, Optional

from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.backend.migration import (
    MigrationDirection,
    migration,
    run_migration_group,
)
from rhosocial.activerecord.backend.migration.record import JSONFileMigrationRecordStore
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    """A minimal model whose DDL the migration applies."""

    @classmethod
    def table_name(cls) -> str:
        return "migration_demo_users"

    id: Annotated[Optional[int], UseSqlType(IntegerType())] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


@migration("v001_create_users", description="create the initial users table on MySQL")
def create_users(ctx):
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(User.create_table_statement(backend=ctx.backend))
    else:
        # DOWN is a compensating DDL statement; MySQL auto-commits it too.
        ctx.apply(User.drop_table_statement(if_exists=True, backend=ctx.backend))


def make_backend() -> MySQLBackend:
    config = MySQLConnectionConfig(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "test"),
        username=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
    )
    backend = MySQLBackend(connection_config=config)
    backend.connect()
    # Keep the dialect's version gates tied to the live server before migrating.
    backend.introspect_and_adapt()
    return backend


def main() -> None:
    backend = make_backend()
    rec_path = tempfile.mktemp(suffix=".json")
    try:
        store = JSONFileMigrationRecordStore(rec_path)
        fqn = f"{__name__}:create_users"

        # 1) dry run — renders every statement, touches neither schema nor records.
        preview = run_migration_group(backend, [fqn], dry_run=True)
        print("== dry run (nothing written) ==")
        print("  statements:", preview.dry_run_total)
        for label, sql, _params in preview.dry_run_sql:
            print(f"  [{label}] {sql}")
        print("  records written:", preview.records_written)

        # 2) real UP — commits DDL implicitly on MySQL, then writes a record.
        up = run_migration_group(backend, [fqn], record_store=store)
        print("\n== UP ==")
        print("  applied:", up.applied)
        print("  versions:", up.versions)
        print("  records written:", up.records_written)
        print("  applied versions:", [r.version for r in store.get_applied()])

        # 3) DOWN — drops the table as a new committed DDL statement.
        down = run_migration_group(
            backend, [fqn], direction=MigrationDirection.DOWN, record_store=store
        )
        print("\n== DOWN ==")
        print("  rolled back:", down.rolled_back)
        print("  applied versions after rollback:", [r.version for r in store.get_applied()])
    finally:
        backend.disconnect()
        if os.path.exists(rec_path):
            os.remove(rec_path)


if __name__ == "__main__":
    main()
