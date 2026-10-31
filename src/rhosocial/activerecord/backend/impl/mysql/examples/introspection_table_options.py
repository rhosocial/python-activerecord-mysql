# src/rhosocial/activerecord/backend/impl/mysql/examples/introspection_table_options.py
"""What MySQL knows about a table's storage, and what the cache buys.

Run::

    python -m rhosocial.activerecord.backend.impl.mysql.examples.introspection_table_options

The example creates a small partitioned table, asks the introspector for
its storage options (``list_table_options`` / ``get_table_options``) and
its partitions (``list_partitions``), and prints what the server answered.
It then walks the schema twice, counting the questions each walk actually
puts to the server:

* **no cache** -- the manager holds a cache whose TTL is 0, so every
  question is answered by asking;
* **warm** -- the default cache, on a manager that has walked this schema
  before, so every question is answered from memory.

Unlike SQLite, the questions here cross a socket, so the point of the
counts is not microseconds but round trips: the cold walk is what a schema
walk costs a server-backed application, and the warm walk is what the same
walk costs once the answer is remembered.

Configuration is the same as the test suite's: the first scenario in
``tests/config/mysql_scenarios.yaml`` (or the file named by
``MYSQL_SCENARIOS_CONFIG_PATH``) is used when one is present, otherwise
the ``MYSQL_HOST`` / ``MYSQL_PORT`` / ``MYSQL_DATABASE`` / ``MYSQL_USER``
/ ``MYSQL_PASSWORD`` environment variables. If no server can be reached,
the example says how to configure one and exits non-zero; it never
invents output.
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.backend.introspection import InMemoryIntrospectionCache
from rhosocial.activerecord.backend.introspection.executor import SyncIntrospectorExecutor

DEMO_TABLE = "mysql_introspection_demo"
DEMO_PARTITIONS = ("p_before_2020", "p_before_2024", "p_max")


# --------------------------------------------------------------------- #
# Connecting the way the tests do
# --------------------------------------------------------------------- #


def _scenario_settings() -> Optional[Dict[str, Any]]:
    """Return the first scenario from the test suite's YAML, if readable.

    ``MYSQL_SCENARIOS_CONFIG_PATH`` wins over the repository-local file,
    which is the same precedence the test conftest applies. ``MYSQL_SCENARIO``
    picks a scenario by name when the file holds more than one.
    """
    try:
        import yaml
    except ImportError:  # pragma: no cover - PyYAML ships with the test extras
        return None

    explicit = os.getenv("MYSQL_SCENARIOS_CONFIG_PATH")
    candidates: List[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    else:
        candidates.append(Path.cwd() / "tests" / "config" / "mysql_scenarios.yaml")

    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        scenarios = data.get("scenarios") or {}
        if not scenarios:
            continue
        wanted = os.getenv("MYSQL_SCENARIO")
        if wanted and wanted in scenarios:
            return dict(scenarios[wanted])
        return dict(next(iter(scenarios.values())))
    return None


def connection_config() -> MySQLConnectionConfig:
    """Build the connection config from a scenario file or environment."""
    scenario = _scenario_settings()
    if scenario is not None:
        # The scenario names the fields exactly as MySQLConnectionConfig
        # does; drop nothing, because ssl_disabled is part of the test
        # suite's local-server settings.
        return MySQLConnectionConfig(**scenario)

    ssl_setting = os.getenv("MYSQL_SSL", "auto")
    return MySQLConnectionConfig(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE"),
        username=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        ssl_disabled=ssl_setting == "disabled",
    )


def _explain_configuration(reason: str) -> None:
    """Say how to point this example at a server, and stop."""
    print(f"Could not connect to MySQL: {reason}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Configure a server in one of these ways:", file=sys.stderr)
    print(
        "  1. tests/config/mysql_scenarios.yaml (the file the test suite reads),",
        file=sys.stderr,
    )
    print(
        "     or set MYSQL_SCENARIOS_CONFIG_PATH to such a file "
        "(MYSQL_SCENARIO picks one by name).",
        file=sys.stderr,
    )
    print(
        "  2. MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, "
        "MYSQL_PASSWORD, MYSQL_CHARSET, MYSQL_SSL.",
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    print(
        "Then re-run: python -m "
        "rhosocial.activerecord.backend.impl.mysql.examples.introspection_table_options",
        file=sys.stderr,
    )
    sys.exit(1)


# --------------------------------------------------------------------- #
# The demo schema, and what is asked about it
# --------------------------------------------------------------------- #


def build_demo_table(backend: MySQLBackend) -> None:
    """Create a partitioned table, replacing any leftovers from a prior run.

    The low-level cursor is used on purpose: this is setup for a
    measurement about introspection, so it should not pay the execution
    hooks and logging of the public ``execute`` path.
    """
    cursor = backend._get_cursor()
    try:
        cursor.execute(f"DROP TABLE IF EXISTS `{DEMO_TABLE}`")
        cursor.execute(
            f"CREATE TABLE `{DEMO_TABLE}` ("
            "  id INT NOT NULL AUTO_INCREMENT,"
            "  created_at DATE NOT NULL,"
            "  note VARCHAR(64) DEFAULT NULL,"
            "  PRIMARY KEY (id, created_at)"
            ") ENGINE=InnoDB ROW_FORMAT=DYNAMIC COMMENT='introspection demo' "
            "PARTITION BY RANGE (YEAR(created_at)) ("
            "  PARTITION p_before_2020 VALUES LESS THAN (2020),"
            "  PARTITION p_before_2024 VALUES LESS THAN (2024),"
            "  PARTITION p_max VALUES LESS THAN MAXVALUE"
            ")"
        )
    finally:
        cursor.close()


def drop_demo_table(backend: MySQLBackend) -> None:
    """Remove the demo table, tolerating a connection that already went away."""
    try:
        cursor = backend._get_cursor()
        try:
            cursor.execute(f"DROP TABLE IF EXISTS `{DEMO_TABLE}`")
        finally:
            cursor.close()
    except Exception:
        pass


def walk_schema(backend: MySQLBackend) -> int:
    """Ask the introspector everything it knows about this schema's storage.

    Returns the number of values answered, so the report can say what the
    questions bought rather than only how many there were.
    """
    introspector = backend.introspector
    answers = 0
    for option in introspector.list_table_options():
        answers += 1
        one = introspector.get_table_options(option.table_name)
        answers += 1 if one is not None else 0
        answers += len(introspector.list_partitions(option.table_name))
    return answers


# --------------------------------------------------------------------- #
# Counting what the executor is asked to do
# --------------------------------------------------------------------- #


class CountingExecutor(SyncIntrospectorExecutor):
    """An executor that also reports how many questions it was asked."""

    def __init__(self, backend: Any) -> None:
        super().__init__(backend)
        self.calls = 0

    def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        self.calls += 1
        return super().execute(sql, params)


def uncached(backend: MySQLBackend) -> CountingExecutor:
    """Install a cache that keeps nothing, and a counting executor."""
    introspector = backend.introspector
    introspector._cache = InMemoryIntrospectionCache(ttl=0)
    executor = CountingExecutor(backend)
    introspector._executor = executor
    return executor


def cached(backend: MySQLBackend) -> CountingExecutor:
    """Install the default cache, and a counting executor."""
    introspector = backend.introspector
    introspector._cache = InMemoryIntrospectionCache()
    executor = CountingExecutor(backend)
    introspector._executor = executor
    return executor


def measure(backend: MySQLBackend) -> Tuple[float, int, int]:
    """Time one walk, and report what it cost in questions and answers."""
    executor = backend.introspector._executor
    before = executor.calls
    started = time.perf_counter()
    answers = walk_schema(backend)
    elapsed = time.perf_counter() - started
    return elapsed, executor.calls - before, answers


# --------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------- #


def _ms(seconds: float) -> str:
    return f"{seconds * 1000:9.2f} ms"


def print_demo(backend: MySQLBackend) -> None:
    """Print the demo table's storage options and partitions as answered."""
    introspector = backend.introspector
    options = introspector.get_table_options(DEMO_TABLE)
    if options is None:
        print(f"{DEMO_TABLE} was not found by the server; nothing to report.")
        return

    print(f"Table options for {options.schema}.{options.table_name}")
    print(f"  engine              {options.engine}")
    print(f"  row format          {options.row_format}")
    print(f"  collation           {options.table_collation}")
    print(f"  auto increment      {options.auto_increment}")
    print(f"  comment             {options.table_comment!r}")
    print(f"  create options      {options.create_options!r}")
    print(f"  data length         {options.data_length} bytes (server estimate)")
    print(f"  index length        {options.index_length} bytes (server estimate)")

    partitions = introspector.list_partitions(DEMO_TABLE)
    print(f"\nPartitions of {DEMO_TABLE} ({len(partitions)}):")
    for partition in partitions:
        print(
            f"  {partition.partition_ordinal_position}. "
            f"{partition.partition_name:<16} "
            f"method={partition.partition_method} "
            f"expression={partition.partition_expression} "
            f"boundary={partition.partition_description} "
            f"rows={partition.table_rows} "
            f"data={partition.data_length}B index={partition.index_length}B"
        )


def report(backend: MySQLBackend) -> None:
    """Measure cold and warm walks and print the comparison."""
    table_count = len(backend.introspector.list_tables())

    # No cache: every question is put to the server, every time.
    uncached(backend)
    measure(backend)  # warm whatever the process caches on its own
    cold, questions, answers = measure(backend)

    # Default cache: the same questions, answered from memory.
    cached(backend)
    measure(backend)  # fill the cache
    warm, warm_questions, _ = measure(backend)

    print(
        f"\nMySQL introspection over {table_count} tables, "
        f"{answers} values answered, {questions} questions put to the server"
    )
    print(f"  no cache                {_ms(cold)}   {questions} questions")
    print(f"  cached                  {_ms(warm)}   {warm_questions} questions")
    if cold > 0:
        print(
            f"\n  cache saves             {_ms(cold - warm)} "
            f"({(cold - warm) / cold * 100:.0f}% of the uncached pass)"
        )


def main() -> None:
    backend = MySQLBackend(connection_config=connection_config())
    try:
        backend.connect()
    except Exception as exc:
        _explain_configuration(str(exc))

    try:
        # The dialect gates its statements on a version; an unadapted
        # dialect has none, and the introspector builds SQL through it.
        backend.introspect_and_adapt()
        build_demo_table(backend)
        # The table did not exist when the schema was listed.
        backend.introspector.clear_cache()

        print_demo(backend)
        report(backend)
    finally:
        drop_demo_table(backend)
        backend.disconnect()


if __name__ == "__main__":
    main()
