# config_loader.py - MySQL Connection Configuration for FastAPI
# docs/examples/chapter_10_fastapi/config_loader.py

from __future__ import annotations

import os
import sys

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))
if _src not in sys.path:
    sys.path.insert(0, _src)

from rhosocial.activerecord.backend.impl.mysql import MySQLConnectionConfig


def load_config() -> MySQLConnectionConfig:
    """Load MySQL connection configuration from environment or defaults."""
    return MySQLConnectionConfig(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        database=os.environ.get("MYSQL_DATABASE", "test_db"),
        username=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
        autocommit=True,
    )
