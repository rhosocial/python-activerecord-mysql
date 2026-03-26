#!/usr/bin/env python3
"""
MySQL 服务探测脚本
连接到 mysql_scenarios.yaml 中的每个 MySQL 服务，使用 SHOW 命令挖掘服务信息。
"""

import sys
import yaml
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rhosocial.activerecord.backend.impl.mysql import MySQLBackend


def load_scenarios():
    """加载 MySQL 场景配置"""
    config_path = Path(__file__).parent / "tests" / "config" / "mysql_scenarios.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)['scenarios']


def create_backend(scenario_name: str, config: dict) -> MySQLBackend:
    """根据配置创建 MySQL 后端"""
    # 处理 ssl_disabled 参数转换为 ssl_verify_cert
    if config.get('ssl_disabled', False):
        config['ssl_verify_cert'] = False

    return MySQLBackend(**config)


def explore_server(backend: MySQLBackend, name: str):
    """探索单个 MySQL 服务器的信息"""
    print(f"\n{'='*60}")
    print(f"探索服务器: {name}")
    print('='*60)

    try:
        backend.connect()
        print("✓ 连接成功")

        # 1. 服务器版本
        print("\n--- 服务器版本 ---")
        version = backend.get_server_version()
        print(f"MySQL 版本: {'.'.join(map(str, version))}")

        # 2. SHOW VARIABLES - 关键变量
        print("\n--- 关键系统变量 ---")
        key_vars = ['version', 'version_comment', 'version_compile_os', 'version_compile_machine',
                    'character_set_server', 'collation_server', 'default_storage_engine',
                    'innodb_version', 'max_connections', 'port', 'socket',
                    'datadir', 'tmpdir', 'sql_mode']
        for var_name in key_vars:
            try:
                result = backend.execute(f"SHOW VARIABLES LIKE '{var_name}'")
                if result.data:
                    print(f"  {result.data[0][0]}: {result.data[0][1]}")
            except Exception as e:
                print(f"  {var_name}: 错误 - {e}")

        # 3. SHOW STATUS - 关键状态
        print("\n--- 关键状态信息 ---")
        status_vars = ['Uptime', 'Threads_connected', 'Threads_running', 'Queries',
                       'Connections', 'Innodb_buffer_pool_reads', 'Innodb_buffer_pool_read_requests']
        for var_name in status_vars:
            try:
                result = backend.execute(f"SHOW STATUS LIKE '{var_name}'")
                if result.data:
                    print(f"  {result.data[0][0]}: {result.data[0][1]}")
            except Exception as e:
                print(f"  {var_name}: 错误 - {e}")

        # 4. SHOW ENGINES - 存储引擎
        print("\n--- 存储引擎支持 ---")
        try:
            engines = backend.show_engines()
            for engine in engines:
                support_indicator = "✓" if engine.support in ('YES', 'DEFAULT') else "✗"
                default_marker = " (DEFAULT)" if engine.support == 'DEFAULT' else ""
                print(f"  {support_indicator} {engine.engine}{default_marker}")
                if engine.transactions:
                    print(f"      事务: {engine.transactions}, XA: {engine.xa}, Savepoints: {engine.savepoints}")
        except Exception as e:
            print(f"  错误: {e}")

        # 5. SHOW DATABASES
        print("\n--- 数据库列表 ---")
        try:
            databases = backend.show_databases()
            for db in databases[:10]:  # 只显示前10个
                print(f"  - {db.name}")
            if len(databases) > 10:
                print(f"  ... 共 {len(databases)} 个数据库")
        except Exception as e:
            print(f"  错误: {e}")

        # 6. 当前数据库的表
        print("\n--- 当前数据库表 ---")
        try:
            tables = backend.show_tables()
            if tables:
                for table in tables[:10]:
                    print(f"  - {table.name}")
                if len(tables) > 10:
                    print(f"  ... 共 {len(tables)} 张表")
            else:
                print("  (无表)")
        except Exception as e:
            print(f"  错误: {e}")

        # 7. 表状态（如果有表）
        print("\n--- 表状态详情 ---")
        try:
            tables = backend.show_tables()
            if tables:
                status_list = backend.show_table_status()
                for status in status_list[:5]:
                    print(f"  {status.name}:")
                    print(f"    引擎: {status.engine}, 行数: {status.rows}, 数据大小: {status.data_length} bytes")
                    print(f"    创建时间: {status.create_time}")
            else:
                print("  (无表)")
        except Exception as e:
            print(f"  错误: {e}")

        # 8. SHOW CHARSET
        print("\n--- 字符集支持 (前10个) ---")
        try:
            charsets = backend.show_charsets()
            for charset in charsets[:10]:
                print(f"  {charset.charset}: {charset.description} (默认排序: {charset.default_collation})")
        except Exception as e:
            print(f"  错误: {e}")

        # 9. SHOW PLUGINS
        print("\n--- 插件状态 (前10个) ---")
        try:
            plugins = backend.show_plugins()
            active_count = sum(1 for p in plugins if p.status == 'ACTIVE')
            print(f"  共 {len(plugins)} 个插件, {active_count} 个活跃")
            for plugin in plugins[:10]:
                print(f"  - {plugin.name}: {plugin.status} ({plugin.type})")
        except Exception as e:
            print(f"  错误: {e}")

        # 10. SHOW PROCESSLIST
        print("\n--- 进程列表 ---")
        try:
            processes = backend.show_processlist()
            print(f"  当前连接数: {len(processes)}")
            for proc in processes[:5]:
                db_info = f" [{proc.db}]" if proc.db else ""
                print(f"  ID {proc.id}: {proc.user}@{proc.host}{db_info} - {proc.command} ({proc.time}s)")
        except Exception as e:
            print(f"  错误: {e}")

        # 11. MySQL 8.0+ 特性
        if version >= (8, 0, 0):
            print("\n--- MySQL 8.0+ 特有功能 ---")

            # 检查窗口函数支持
            print("  窗口函数: 支持 (MySQL 8.0+)")

            # 检查 CTE 支持
            try:
                result = backend.execute("WITH RECURSIVE cte AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM cte WHERE n < 3) SELECT * FROM cte")
                print("  递归 CTE: 支持")
            except:
                print("  递归 CTE: 不支持")

            # 检查 JSON 支持
            try:
                result = backend.execute("SELECT JSON_OBJECT('key', 'value')")
                print("  JSON 函数: 支持")
            except:
                print("  JSON 函数: 不支持")

        # 12. 触发器和存储过程
        print("\n--- 触发器 ---")
        try:
            triggers = backend.show_triggers()
            if triggers:
                for trigger in triggers[:5]:
                    print(f"  - {trigger.trigger}: {trigger.timing} {trigger.event} ON {trigger.table}")
            else:
                print("  (无触发器)")
        except Exception as e:
            print(f"  错误: {e}")

        print("\n--- 存储过程 ---")
        try:
            procedures = backend.show_procedure_status()
            if procedures:
                for proc in procedures[:5]:
                    print(f"  - {proc.db}.{proc.name}")
            else:
                print("  (无存储过程)")
        except Exception as e:
            print(f"  错误: {e}")

        print("\n--- 存储函数 ---")
        try:
            functions = backend.show_function_status()
            if functions:
                for func in functions[:5]:
                    print(f"  - {func.db}.{func.name}")
            else:
                print("  (无存储函数)")
        except Exception as e:
            print(f"  错误: {e}")

        backend.disconnect()
        print("\n✓ 探测完成")

    except Exception as e:
        print(f"\n✗ 连接或探测失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    scenarios = load_scenarios()

    print("MySQL 服务探测脚本")
    print("=" * 60)
    print(f"发现 {len(scenarios)} 个 MySQL 服务场景")

    for name, config in scenarios.items():
        backend = create_backend(name, config)
        explore_server(backend, name)


if __name__ == "__main__":
    main()
