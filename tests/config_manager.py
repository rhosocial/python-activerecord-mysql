"""Configuration Management Module, implementing multi-level priority configuration mechanism"""
import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path


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
            print(f"[INFO] Loaded configuration from {file_path}")
            return config
    except Exception as e:
        print(f"[ERROR] Failed to load configuration file {file_path}: {e}")
        raise


def load_json_config(file_path: Path) -> Dict[str, Any]:
    """
    Load JSON configuration file
    
    Args:
        file_path: JSON file path
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = json.load(f) or {}
            print(f"[INFO] Loaded configuration from {file_path}")
            return config
    except Exception as e:
        print(f"[ERROR] Failed to load configuration file {file_path}: {e}")
        raise


def load_config_from_file(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration from file based on its extension
    
    Args:
        config_path: Configuration file path
        
    Returns:
        Configuration dictionary
    """
    # Remove any potential trailing spaces from the suffix
    suffix = config_path.suffix.lower().strip()
    if suffix in ['.yaml', '.yml']:
        return load_yaml_config(config_path)
    elif suffix == '.json':
        return load_json_config(config_path)
    else:
        raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")


def load_config() -> Dict[str, Any]:
    """
    Load configuration using multi-level priority mechanism:
    1. Environment variable specified config file (MYSQL_ACTIVERECCORD_CONFIG_PATH)
    2. Default config file (config.json in tests directory)
    3. Environment variables for MySQL connection parameters
    4. Hard-coded default values
    """
    # 1. Check environment variable for config file path
    config_file_path_env = os.getenv("MYSQL_ACTIVERECCORD_CONFIG_PATH")
    if config_file_path_env:
        config_path = Path(config_file_path_env)
        if config_path.exists():
            print(f"[INFO] Using configuration file from environment variable: {config_path}")
            try:
                return load_config_from_file(config_path)
            except Exception as e:
                print(f"[ERROR] Configuration file from environment variable exists but failed to read: {e}")
                print("[ERROR] Terminating due to configuration read error.")
                raise
        else:
            print(f"[WARNING] Configuration file specified in environment variable does not exist: {config_path}")
            raise FileNotFoundError(f"Configuration file {config_path} specified in MYSQL_ACTIVERECCORD_CONFIG_PATH does not exist")
    
    # 2. Check default config file in tests directory
    default_config_path = Path(__file__).parent.parent / "config.json"  # Looking in project root
    if default_config_path.exists():
        print(f"[INFO] Using default configuration file: {default_config_path}")
        try:
            return load_config_from_file(default_config_path)
        except Exception as e:
            print(f"[ERROR] Default configuration file exists but failed to read: {e}")
            print("[ERROR] Terminating due to configuration read error.")
            raise
    
    # 3. Try to get connection parameters from environment variables
    mysql_host = os.getenv("MYSQL_HOST")
    mysql_port = os.getenv("MYSQL_PORT")
    mysql_user = os.getenv("MYSQL_USER")
    mysql_password = os.getenv("MYSQL_PASSWORD")
    mysql_database = os.getenv("MYSQL_DATABASE")
    
    if all([mysql_host, mysql_port, mysql_user, mysql_password, mysql_database]):
        print("[INFO] Using MySQL connection parameters from environment variables")
        return {
            'databases': {
                'mysql': {
                    'versions': [
                        {
                            'label': 'environment',
                            'version': [8, 0, 0],  # Default version assumption
                            'host': mysql_host,
                            'port': int(mysql_port),
                            'database': mysql_database,
                            'username': mysql_user,
                            'password': mysql_password
                        }
                    ]
                }
            }
        }
    
    # 4. Use default hard-coded configuration
    print("[INFO] Using default hard-coded configuration")
    return {
        'databases': {
            'mysql': {
                'versions': [
                    {
                        'label': 'default',
                        'version': [8, 0, 21],  # Default version assumption
                        'host': 'localhost',
                        'port': 3306,
                        'database': 'test_activerecord',
                        'username': 'test_user',
                        'password': 'test_password',
                        'charset': 'utf8mb4',
                        'autocommit': True,
                        'connect_timeout': 10,
                        'read_timeout': 30,
                        'write_timeout': 30
                    }
                ]
            }
        },
        'connection_pool': {
            'pool_name': 'test_pool',
            'pool_size': 5,
            'pool_reset_session': True
        }
    }


def get_mysql_configurations() -> Dict[str, Any]:
    """
    Get MySQL configurations using the multi-level priority mechanism
    
    Returns:
        MySQL configurations dictionary
    """
    return load_config()


# For backward compatibility with existing scenarios code
def get_mysql_connection_params() -> Dict[str, Any]:
    """
    Get basic MySQL connection parameters for backward compatibility
    
    Returns:
        Connection parameters dictionary
    """
    config = load_config()
    
    # Extract default MySQL connection parameters from config
    mysql_configs = config.get('databases', {}).get('mysql', {}).get('versions', [])
    if mysql_configs:
        # Return the first configuration as default
        first_config = mysql_configs[0]
        return {
            'host': first_config.get('host', 'localhost'),
            'port': first_config.get('port', 3306),
            'user': first_config.get('username', 'root'),
            'password': first_config.get('password', 'password'),
            'database': first_config.get('database', 'test_activerecord'),
        }
    
    # Fallback to basic environment variables or defaults
    return {
        'host': os.getenv("MYSQL_HOST", "localhost"),
        'port': int(os.getenv("MYSQL_PORT", "3306")),
        'user': os.getenv("MYSQL_USER", "root"),
        'password': os.getenv("MYSQL_PASSWORD", "password"),
        'database': os.getenv("MYSQL_DATABASE", "test_activerecord"),
    }