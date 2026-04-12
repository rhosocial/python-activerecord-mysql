# config_loader.py - MySQL Connection Configuration Loader
# docs/examples/chapter_12_scenarios/parallel_workers/config_loader.py
"""
MySQL connection configuration loading (three-level priority):

1. tests/config/mysql_scenarios.yaml (if exists, use mysql_80 or first scenario)
2. Environment variables MYSQL_HOST / MYSQL_PORT / MYSQL_DATABASE / MYSQL_USER / MYSQL_PASSWORD
3. Hardcoded defaults (localhost:3306/test_db/root/)

Public interface:
    load_config(scenario=None)  → MySQLConnectionConfig
    list_scenarios()            → list[str]
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

# ─── sys.path patch (enables standalone execution) ─────────────────────────────────

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))
if _src not in sys.path:
    sys.path.insert(0, _src)

from rhosocial.activerecord.backend.impl.mysql import MySQLConnectionConfig  # noqa: E402

# ─── Default preferred scenarios (by priority) ─────────────────────────────────────

_PREFERRED_SCENARIOS = ["mysql_80", "mysql_84", "mysql_92", "mysql_96", "mysql_57", "mysql_56"]


def _find_scenarios_yaml() -> Optional[str]:
    """Find mysql_scenarios.yaml in standard locations."""
    # Relative to this file: ../../../../tests/config/mysql_scenarios.yaml
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(here, "..", "..", "..", "..", "tests", "config", "mysql_scenarios.yaml")),
        os.environ.get("MYSQL_ACTIVERECORD_CONFIG_PATH", ""),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def load_config(scenario: Optional[str] = None) -> MySQLConnectionConfig:
    """Load MySQL connection configuration.

    Args:
        scenario: Scenario name in YAML (e.g., "mysql_80"). If None, auto-select by priority.

    Returns:
        MySQLConnectionConfig instance.
    """
    yaml_path = _find_scenarios_yaml()
    if yaml_path:
        try:
            import yaml  # type: ignore[import]

            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            scenarios: dict = data.get("scenarios", {})
            if scenarios:
                if scenario and scenario in scenarios:
                    params = scenarios[scenario]
                else:
                    # Select scenario by priority
                    params = None
                    for preferred in _PREFERRED_SCENARIOS:
                        if preferred in scenarios:
                            params = scenarios[preferred]
                            break
                    if params is None:
                        params = next(iter(scenarios.values()))
                # Filter out None values to avoid dataclass field type conflicts
                return MySQLConnectionConfig(**{k: v for k, v in params.items() if v is not None})
        except ImportError:
            print("Warning: pyyaml not installed, skipping YAML config loading. Run pip install pyyaml", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Cannot read {yaml_path}: {e}, using environment variables/defaults", file=sys.stderr)

    # Build configuration from environment variables or hardcoded defaults
    return MySQLConnectionConfig(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        database=os.environ.get("MYSQL_DATABASE", "test_db"),
        username=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
        autocommit=True,
    )


def list_scenarios() -> List[str]:
    """Return all available scenario names in YAML, or empty list if config file not found."""
    yaml_path = _find_scenarios_yaml()
    if yaml_path:
        try:
            import yaml  # type: ignore[import]

            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return list(data.get("scenarios", {}).keys())
        except Exception:
            pass
    return []


def show_active_config(config: MySQLConnectionConfig) -> None:
    """Print current connection parameters (password hidden)."""
    print(f"  Host: {config.host}:{config.port}")
    print(f"  Database: {config.database}")
    print(f"  User: {config.username}")
    print(f"  Charset: {config.charset}")
