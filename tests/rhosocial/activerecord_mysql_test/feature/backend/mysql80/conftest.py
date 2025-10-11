# tests/rhosocial/activerecord_mysql_test/backend/mysql80/conftest.py
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import pytest
import yaml

# Setup logger
logger = logging.getLogger("mysql_test")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Import required backend classes
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend


def find_config_file(config_dir: Path) -> Optional[Path]:
    """
    Find configuration file in the specified directory

    Args:
        config_dir: Configuration file directory

    Returns:
        Configuration file path or None (if not found)
    """
    for ext in ['.yml', '.yaml']:
        config_path = config_dir / f"config{ext}"
        if config_path.exists():
            logger.info(f"Found configuration file: {config_path}")
            return config_path

    logger.warning(f"No configuration file found in {config_dir}")
    return None


def load_yaml_config(file_path: Path) -> Dict[str, Any]:
    """
    Load YAML configuration file

    Args:
        file_path: YAML file path

    Returns:
        Configuration dictionary
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            logger.debug(f"Loaded configuration from {file_path}")
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration file {file_path}: {e}")
        return {}


def load_config() -> Dict[str, Any]:
    """
    Load configuration

    Search in priority order:
    1. 'config' subdirectory of current directory
    2. Current directory
    3. 'config' subdirectory of conftest.py directory
    4. conftest.py directory

    Returns:
        Configuration dictionary
    """
    # Try multiple paths
    search_paths = [
        Path.cwd() / 'config',  # 'config' subdirectory of current working directory
        Path.cwd(),  # Current working directory
        Path(__file__).parent / 'config',  # 'config' subdirectory of conftest.py directory
        Path(__file__).parent,  # conftest.py directory
    ]

    # Find configuration file
    config_file = None
    for path in search_paths:
        config_file = find_config_file(path)
        if config_file:
            break

    # Load configuration file or use default configuration
    if config_file:
        return load_yaml_config(config_file)
    else:
        logger.warning("Configuration file not found, using default configuration")
        return {
            'databases': {
                'mysql': {
                    'versions': [
                        {'label': 'mysql8', 'version': [8, 0, 0], 'host': '127.0.0.1', 'port': 3306,
                         'database': 'test', 'username': 'root', 'password': ''},
                    ]
                }
            }
        }


# Load configuration when the module is imported
CONFIG = load_config()


def get_mysql_versions() -> List[Dict[str, Any]]:
    """
    Get all configured MySQL versions

    Returns:
        MySQL version configuration list
    """
    try:
        return CONFIG.get('databases', {}).get('mysql', {}).get('versions', [])
    except:
        return []


def create_mysql_connection_config(version_config: Dict[str, Any]) -> MySQLConnectionConfig:
    """
    Create MySQLConnectionConfig based on version configuration

    Args:
        version_config: Version configuration dictionary

    Returns:
        MySQLConnectionConfig object
    """
    # Extract basic connection information
    config_dict = {
        'host': version_config.get('host', '127.0.0.1'),
        'port': version_config.get('port', 3306),
        'database': version_config.get('database', 'test'),
        'username': version_config.get('username', 'root'),
        'password': version_config.get('password', ''),
        'version': tuple(version_config.get('version', [0, 0, 0])),
    }

    # Extract MySQL specific optional parameters
    for key in ['charset', 'timezone', 'pool_size', 'pool_timeout', 'pool_name',
                'ssl_ca', 'ssl_cert', 'ssl_key', 'ssl_mode', 'auth_plugin']:
        if key in version_config:
            config_dict[key] = version_config[key]

    # Extract MySQL specific pragma settings if available
    if 'pragmas' in version_config:
        config_dict['pragmas'] = version_config['pragmas']

    # Create and return MySQLConnectionConfig
    return MySQLConnectionConfig(**config_dict)


# Parameterized fixture for MySQL versions
@pytest.fixture(params=get_mysql_versions(), ids=lambda v: v.get('label', f"mysql-{v.get('version', [0, 0, 0])}"))
def mysql_config(request):
    """
    Fixture providing MySQL connection configuration, executed once for each configured version

    Args:
        request: Pytest request object for accessing parameters

    Returns:
        MySQLConnectionConfig object
    """
    version_config = request.param
    logger.info(f"Using MySQL configuration: {version_config.get('label')}, version: {version_config.get('version')}")
    return create_mysql_connection_config(version_config)


@pytest.fixture
def mysql_connection(mysql_config):
    """
    Fixture providing MySQL connection

    Args:
        mysql_config: MySQL connection configuration (MySQLConnectionConfig)

    Returns:
        MySQLBackend instance
    """
    logger.info(f"Creating MySQL connection: {mysql_config.host}:{mysql_config.port}")

    # Directly pass the MySQLConnectionConfig instance
    backend = MySQLBackend(connection_config=mysql_config)

    try:
        backend.connect()
        logger.info("MySQL connection created successfully")
        yield backend
    finally:
        # Ensure proper cleanup
        if backend:
            logger.info("Cleaning up MySQL connection")
            # Roll back any active transactions
            if hasattr(backend,
                       '_transaction_manager') and backend._transaction_manager and backend._transaction_manager.is_active:
                logger.warning("Active transaction detected during cleanup, rolling back")
                try:
                    backend._transaction_manager.rollback()
                except Exception as e:
                    logger.error(f"Transaction rollback error: {e}")

            # Disconnect properly
            if hasattr(backend, '_connection') and backend._connection:
                logger.info("Disconnecting MySQL connection")
                try:
                    backend.disconnect()
                except Exception as e:
                    logger.error(f"Disconnect error: {e}")


@pytest.fixture
def mysql_test_db(mysql_connection):
    """
    Fixture to setup and teardown test database

    Args:
        mysql_connection: MySQL connection

    Returns:
        MySQL connection with prepared test tables
    """
    # Import setup and teardown functions from test_crud.py
    try:
        # Try direct import
        from test_curd import setup_test_table, teardown_test_table
    except ImportError:
        # If import fails, try dynamic module loading
        import importlib.util
        import sys

        # Find test_curd.py file
        for search_path in [Path.cwd(), Path(__file__).parent]:
            module_path = search_path / 'test_curd.py'
            if module_path.exists():
                logger.info(f"Found test_curd.py: {module_path}")
                spec = importlib.util.spec_from_file_location("test_curd", module_path)
                test_curd_module = importlib.util.module_from_spec(spec)
                sys.modules["test_curd"] = test_curd_module
                spec.loader.exec_module(test_curd_module)
                setup_test_table = test_curd_module.setup_test_table
                teardown_test_table = test_curd_module.teardown_test_table
                break
        else:
            pytest.skip("Could not find test_curd.py module")

    logger.info("Setting up test tables")
    # Ensure starting from a clean state
    if not mysql_connection._connection:
        mysql_connection.connect()
    elif hasattr(mysql_connection,
                 '_transaction_manager') and mysql_connection._transaction_manager and mysql_connection._transaction_manager.is_active:
        # If there's an active transaction, roll back first
        try:
            mysql_connection._transaction_manager.rollback()
            logger.info("Rolled back previous active transaction")
        except Exception as e:
            logger.error(f"Error rolling back previous transaction: {e}")
            # Reconnect on connection error
            mysql_connection.disconnect()
            mysql_connection.connect()
            logger.info("Reconnected after transaction error")

    # Setup test tables
    setup_test_table(mysql_connection)
    logger.info("Test tables created successfully")

    # Return connection for tests to use
    yield mysql_connection

    # Cleanup after tests
    logger.info("Cleaning up test tables")
    teardown_test_table(mysql_connection)
    logger.info("Test tables deleted successfully")


def pytest_configure(config):
    """Configure pytest"""
    # No special markers needed as we use parameterized fixtures
    pass