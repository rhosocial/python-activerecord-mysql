# tests/mysql_live_server.py
"""Collection-time check that a MySQL server is reachable.

The backend-feature suite connects from its fixtures, so a missing server
surfaces as a fixture error rather than a skip. Tests whose whole point is
a live server use :func:`mysql_server_available` in a module-level
``skipif`` marker instead, which is decided at collection time and before
any fixture tries to connect.

The scenarios are read from the same YAML the test conftest reads, with
the same ``MYSQL_SCENARIOS_CONFIG_PATH`` override, so "reachable" means
"one of the servers this run is configured to use".
"""

import os
import socket
from pathlib import Path
from typing import Iterator, Optional

import yaml

DEFAULT_SCENARIO_FILE = (
    Path(__file__).resolve().parent / "config" / "mysql_scenarios.yaml"
)


def scenario_config_path() -> Optional[Path]:
    """Return the scenario file this run will use, if any."""
    explicit = os.getenv("MYSQL_SCENARIOS_CONFIG_PATH")
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    return DEFAULT_SCENARIO_FILE if DEFAULT_SCENARIO_FILE.is_file() else None


def _scenarios() -> Iterator[dict]:
    path = scenario_config_path()
    if path is None:
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return
    for config in (data.get("scenarios") or {}).values():
        if isinstance(config, dict):
            yield config


def mysql_server_available(timeout: float = 1.0) -> bool:
    """Return True if any configured MySQL server accepts a TCP connection.

    Only the transport is checked: a server that accepts and then refuses
    the credentials still means "a server is there", and the fixture that
    actually connects reports the refusal in the usual way.
    """
    for config in _scenarios():
        host = config.get("host")
        port = config.get("port")
        if not host or not port:
            continue
        try:
            with socket.create_connection((str(host), int(port)), timeout=timeout):
                return True
        except OSError:
            continue
    return False
