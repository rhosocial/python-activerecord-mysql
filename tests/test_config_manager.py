"""
配置管理器测试
用于验证配置管理器的多级优先级加载机制是否正常工作
"""
import os
import tempfile
from pathlib import Path
import json
import pytest

# 从tests.config_manager导入，需要确保PYTHONPATH包含tests目录
from tests.config_manager import load_config


def test_load_config_from_default_file():
    """测试从默认配置文件加载配置"""
    # 准备测试配置文件
    config_data = {
        "databases": {
            "mysql": {
                "versions": [
                    {
                        "label": "test",
                        "version": [8, 0, 21],
                        "host": "test_host",
                        "port": 3307,
                        "database": "test_db",
                        "username": "test_user",
                        "password": "test_password"
                    }
                ]
            }
        },
        "connection_pool": {
            "pool_name": "test_pool",
            "pool_size": 5,
            "pool_reset_session": True
        }
    }
    
    config_file = Path("config.json")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
    
    try:
        # 测试配置加载
        config = load_config()
        assert config["databases"]["mysql"]["versions"][0]["host"] == "test_host"
        assert config["databases"]["mysql"]["versions"][0]["port"] == 3307
        print("PASS: Load config from default config file test passed")
    finally:
        # 清理测试文件
        if config_file.exists():
            config_file.unlink()


def test_load_config_from_env_var():
    """测试从环境变量指定的配置文件加载配置"""
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        config_data = {
            "databases": {
                "mysql": {
                    "versions": [
                        {
                            "label": "env_test",
                            "version": [5, 7, 25],
                            "host": "env_host",
                            "port": 3308,
                            "database": "env_db",
                            "username": "env_user",
                            "password": "env_password"
                        }
                    ]
                }
            },
            "connection_pool": {
                "pool_name": "test_pool",
                "pool_size": 5,
                "pool_reset_session": True
            }
        }
        json.dump(config_data, tmp_file)
        tmp_file_path = tmp_file.name
    
    # 设置环境变量
    original_env = os.environ.get("MYSQL_ACTIVERECCORD_CONFIG_PATH")
    os.environ["MYSQL_ACTIVERECCORD_CONFIG_PATH"] = tmp_file_path
    
    try:
        # 测试配置加载
        config = load_config()
        assert config["databases"]["mysql"]["versions"][0]["host"] == "env_host"
        assert config["databases"]["mysql"]["versions"][0]["port"] == 3308
        print("PASS: Load config from env var specified config file test passed")
    finally:
        # 恢复环境变量
        if original_env is not None:
            os.environ["MYSQL_ACTIVERECCORD_CONFIG_PATH"] = original_env
        else:
            del os.environ["MYSQL_ACTIVERECCORD_CONFIG_PATH"]
        
        # 清理临时文件
        Path(tmp_file_path).unlink()


def test_load_config_from_env_vars():
    """测试从环境变量加载MySQL连接参数"""
    # 设置MySQL相关的环境变量
    original_env = {
        'MYSQL_HOST': os.environ.get('MYSQL_HOST'),
        'MYSQL_PORT': os.environ.get('MYSQL_PORT'),
        'MYSQL_USER': os.environ.get('MYSQL_USER'),
        'MYSQL_PASSWORD': os.environ.get('MYSQL_PASSWORD'),
        'MYSQL_DATABASE': os.environ.get('MYSQL_DATABASE')
    }
    
    os.environ['MYSQL_HOST'] = 'envvar_host'
    os.environ['MYSQL_PORT'] = '3309'
    os.environ['MYSQL_USER'] = 'envvar_user'
    os.environ['MYSQL_PASSWORD'] = 'envvar_password'
    os.environ['MYSQL_DATABASE'] = 'envvar_db'
    
    try:
        # 删除可能存在的默认配置文件以确保使用环境变量
        default_config_path = Path("config.json")
        was_exists = default_config_path.exists()
        if was_exists:
            default_config_path.unlink()
        
        # 测试配置加载
        config = load_config()
        mysql_config = config["databases"]["mysql"]["versions"][0]
        assert mysql_config["host"] == "envvar_host"
        assert mysql_config["port"] == 3309
        assert mysql_config["username"] == "envvar_user"
        assert mysql_config["password"] == "envvar_password"
        assert mysql_config["database"] == "envvar_db"
        print("PASS: Load MySQL connection params from env vars test passed")
    finally:
        # 恢复原始环境变量
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
        
        # 恢复默认配置文件（如果之前存在）
        if was_exists and not Path("config.json").exists():
            # 创建一个简单的默认配置文件
            with open("config.json", "w") as f:
                json.dump({
                    "databases": {
                        "mysql": {
                            "versions": [{
                                "label": "default",
                                "host": "localhost",
                                "port": 3306,
                                "database": "test_activerecord",
                                "username": "test_user",
                                "password": "test_password"
                            }]
                        }
                    }
                }, f)


def test_load_default_hardcoded_config():
    """测试加载硬编码的默认配置"""
    # 确保没有配置文件和环境变量
    default_config_path = Path("config.json")
    was_exists = default_config_path.exists()
    if was_exists:
        default_config_path.unlink()
    
    original_env = {
        'MYSQL_ACTIVERECCORD_CONFIG_PATH': os.environ.get('MYSQL_ACTIVERECCORD_CONFIG_PATH'),
        'MYSQL_HOST': os.environ.get('MYSQL_HOST'),
        'MYSQL_PORT': os.environ.get('MYSQL_PORT'),
        'MYSQL_USER': os.environ.get('MYSQL_USER'),
        'MYSQL_PASSWORD': os.environ.get('MYSQL_PASSWORD'),
        'MYSQL_DATABASE': os.environ.get('MYSQL_DATABASE')
    }
    
    # 清除相关环境变量
    for key in original_env:
        if key:
            os.environ.pop(key, None)
    
    try:
        # 测试配置加载
        config = load_config()
        mysql_config = config["databases"]["mysql"]["versions"][0]
        assert mysql_config["host"] == "localhost"
        assert mysql_config["port"] == 3306
        assert mysql_config["username"] == "test_user"
        assert mysql_config["password"] == "test_password"
        assert mysql_config["database"] == "test_activerecord"
        print("PASS: Load hardcoded default config test passed")
    finally:
        # 恢复原始环境变量
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
        
        # 恢复默认配置文件（如果之前存在）
        if was_exists and not Path("config.json").exists():
            # 创建一个简单的默认配置文件
            with open("config.json", "w") as f:
                json.dump({
                    "databases": {
                        "mysql": {
                            "versions": [{
                                "label": "default",
                                "host": "localhost",
                                "port": 3306,
                                "database": "test_activerecord",
                                "username": "test_user",
                                "password": "test_password"
                            }]
                        }
                    }
                }, f)


if __name__ == "__main__":
    test_load_config_from_default_file()
    test_load_config_from_env_var()
    test_load_config_from_env_vars()
    test_load_default_hardcoded_config()
    print("\nPASSED: All config manager tests passed")