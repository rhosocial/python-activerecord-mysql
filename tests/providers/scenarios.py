# tests/providers/scenarios.py
"""MySQL后端的测试场景配置映射表"""

import os
from typing import Dict, Any, Tuple, Type
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

# 场景名 -> 配置字典 的映射表（只关心MySQL）
SCENARIO_MAP: Dict[str, Dict[str, Any]] = {}


def register_scenario(name: str, config: Dict[str, Any]):
    """注册MySQL测试场景"""
    SCENARIO_MAP[name] = config


def get_scenario(name: str) -> Tuple[Type[MySQLBackend], MySQLConnectionConfig]:
    """
    Retrieves the backend class and a connection configuration object for a given
    scenario name. This is called by the provider to set up the database for a test.
    """
    if name not in SCENARIO_MAP:
        name = "local"  # Fallback to the default scenario if not found.

    # Unpack the configuration dictionary into the dataclass constructor.
    config = MySQLConnectionConfig(**SCENARIO_MAP[name])
    return MySQLBackend, config


def get_enabled_scenarios() -> Dict[str, Any]:
    """
    Returns the map of all currently enabled scenarios. The testsuite's conftest
    uses this to parameterize the tests, causing them to run for each scenario.
    """
    return SCENARIO_MAP


def _register_default_scenarios():
    """
    Registers the default scenarios supported by this MySQL backend.
    More complex scenarios (e.g., for performance or concurrency testing)
    can be added here, often controlled by environment variables.
    """
    # 本地MySQL实例场景 - 使用环境变量或默认值
    mysql_host = os.getenv("MYSQL_HOST", "localhost")
    mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user = os.getenv("MYSQL_USER", "root")
    mysql_password = os.getenv("MYSQL_PASSWORD", "password")
    mysql_database = os.getenv("MYSQL_DATABASE", "test_activerecord")

    register_scenario("local", {
        "host": mysql_host,
        "port": mysql_port,
        "user": mysql_user,
        "password": mysql_password,
        "database": mysql_database,
    })

    # 环境变量控制的其他场景
    if os.getenv("TEST_MYSQL_DOCKER", "false").lower() == "true":
        register_scenario("docker", {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_DOCKER_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", "password"),
            "database": os.getenv("MYSQL_DATABASE", "test_activerecord_docker"),
        })

    if os.getenv("TEST_MYSQL_PERFORMANCE", "false").lower() == "true":
        register_scenario("performance", {
            "host": mysql_host,
            "port": mysql_port,
            "user": mysql_user,
            "password": mysql_password,
            "database": mysql_database + "_perf",
            # 可能包含特定的性能配置参数
        })


# 初始化时注册默认场景
_register_default_scenarios()