#!/usr/bin/env python3
"""
检查 MySQL 场景配置中的所有数据库信息。

使用新实现的 SHOW 功能来挖掘数据库信息。
"""

import yaml
import sys
import os

# 添加项目路径到 sys.path
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_path, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from rhosocial.activerecord.backend.impl.mysql import MySQLBackend


def load_scenarios(config_path):
    """加载 YAML 配置文件"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('scenarios', {})


def inspect_database(scenario_name, config):
    """检验单个数据库"""
    print(f"\n{'='*60}")
    print(f"检查数据库: {scenario_name}")
    print(f"{'='*60}")

    backend = None
    try:
        # 创建 backend 实例
        backend = MySQLBackend(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            username=config['username'],
            password=config['password'],
            charset=config.get('charset', 'utf8mb4'),
            autocommit=config.get('autocommit', True),
            ssl_verify_cert=config.get('ssl_verify_cert', True),
            ssl_disabled=config.get('ssl_disabled', False),
            init_command=config.get('init_command'),
        )

        # 连接数据库
        backend.connect()
        print(f"✓ 连接成功: {config['host']}:{config['port']}")

        # 获取服务器版本
        version = backend.get_server_version()
        version_str = '.'.join(map(str, version))
        print(f"✓ 服务器版本: {version_str}")

        # 使用 SHOW 功能
        show = backend.show()

        # 1. 显示数据库列表
        print("\n--- 数据库列表 ---")
        databases = show.databases()
        for db in databases[:10]:  # 只显示前10个
            print(f"  - {db.name}")
        if len(databases) > 10:
            print(f"  ... 还有 {len(databases) - 10} 个数据库")

        # 2. 显示当前数据库的表
        print(f"\n--- 当前数据库 '{config['database']}' 的表 ---")
        tables = show.tables()
        if tables:
            for table in tables[:10]:
                table_type = f" ({table.table_type})" if table.table_type else ""
                print(f"  - {table.name}{table_type}")
            if len(tables) > 10:
                print(f"  ... 还有 {len(tables) - 10} 个表")
        else:
            print("  (无表)")

        # 3. 显示表状态
        print(f"\n--- 表状态信息 ---")
        if tables:
            statuses = show.table_status()
            for status in statuses[:5]:
                print(f"  - {status.name}")
                print(f"    引擎: {status.engine}, 行数: {status.rows}, 大小: {status.data_length} bytes")

        # 4. 显示字符集
        print(f"\n--- 支持的字符集 (前5个) ---")
        charsets = show.charset()
        for cs in charsets[:5]:
            print(f"  - {cs.charset}: {cs.description}")

        # 5. 显示存储引擎
        print(f"\n--- 存储引擎 ---")
        engines = show.engines()
        for engine in engines:
            support = "✓" if engine.support in ('YES', 'DEFAULT') else "✗"
            print(f"  {support} {engine.engine}: {engine.support}")

        # 6. 显示关键变量
        print(f"\n--- 关键变量 ---")
        variables = show.variables(like='version%')
        for var in variables:
            print(f"  {var.variable_name}: {var.value}")

        # 7. 显示状态信息
        print(f"\n--- 状态信息 (前5个) ---")
        status = show.status()
        for stat in status[:5]:
            print(f"  {stat.variable_name}: {stat.value}")

        print(f"\n✓ 检查完成: {scenario_name}")

    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if backend:
            try:
                backend.disconnect()
            except:
                pass


def main():
    """主函数"""
    # 配置文件路径
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'mysql_scenarios.yaml')

    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
        sys.exit(1)

    # 加载场景配置
    scenarios = load_scenarios(config_path)

    if not scenarios:
        print("没有找到场景配置")
        sys.exit(1)

    print(f"找到 {len(scenarios)} 个数据库场景")

    # 检查每个数据库
    for scenario_name, config in scenarios.items():
        inspect_database(scenario_name, config)

    print(f"\n{'='*60}")
    print("所有数据库检查完成")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
