# docs/examples/migration/02_named_migration.py
"""Class-style migrations on MySQL through this repo's backend and CLI wiring.

The same migration can be run two ways:

  * via the MySQL backend CLI (note the CLI builds and adapts the backend for you):

        python -m rhosocial.activerecord.backend.impl.mysql named-migration \\
          rhosocial.activerecord.backend.impl.mysql.examples.named_migrations.migrations.V001CreateUsers \\
          --host localhost --database test --direction up \\
          --record-store ./migrations.json

    Add ``--dry-run`` to preview, ``--direction down`` to roll back, or
    ``--single-transaction`` for batch record writes. Remember that MySQL DDL
    auto-commits: ``--single-transaction`` cannot make DDL atomic (see
    docs/en_US/migration/README.md, §4).

  * programmatically, as this script does — using this repo's MySQLBackend and
    MySQLConnectionConfig, plus the class-style ``MigrationRunner``.

Requires a reachable MySQL server (MYSQL_* environment variables); it will not
run locally without one. Run from the repository root with ``PYTHONPATH=src``.
"""

import os
import tempfile

from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.backend.migration import (
    JSONFileMigrationRecordStore,
    MigrationDirection,
    MigrationRunner,
)

# The demo migration class shipped with this backend (no new migration needed).
MIGRATION_FQN = (
    "rhosocial.activerecord.backend.impl.mysql.examples"
    ".named_migrations.migrations.V001CreateUsers"
)


def main() -> None:
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
    # The CLI does this automatically; hand-built backends must not skip it.
    backend.introspect_and_adapt()

    store_path = tempfile.mktemp(suffix=".json")
    runner = MigrationRunner(MIGRATION_FQN)
    try:
        store = JSONFileMigrationRecordStore(store_path)

        preview = runner.run(backend, MigrationDirection.UP, dry_run=True)
        print("== dry run ==", preview.version, preview.success)

        up = runner.run(backend, MigrationDirection.UP, record_store=store)
        print("== UP ==", up.version, up.success)

        down = runner.run(backend, MigrationDirection.DOWN, record_store=store)
        print("== DOWN ==", down.version, down.success)

        print("applied versions after rollback:", [r.version for r in store.get_applied()])
    finally:
        backend.disconnect()
        if os.path.exists(store_path):
            os.remove(store_path)


if __name__ == "__main__":
    main()
