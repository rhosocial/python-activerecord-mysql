#!/usr/bin/env python3
"""
MySQL 数据库内省探索脚本
连接所有配置的 MySQL 服务器并获取详细信息
包括用户权限信息
"""

import yaml
import sys
from pathlib import Path
from mysql.connector import connect, Error as MySQLError


def load_config():
    """加载测试配置"""
    config_path = Path(__file__).parent / 'tests' / 'config' / 'mysql_scenarios.yaml'
    with open(config_path) as f:
        return yaml.safe_load(f)


def create_connection(scenario_config):
    """创建数据库连接"""
    config = {
        'host': scenario_config['host'],
        'port': scenario_config['port'],
        'database': scenario_config['database'],
        'user': scenario_config['username'],
        'password': scenario_config['password'],
        'charset': scenario_config.get('charset', 'utf8mb4'),
        'autocommit': scenario_config.get('autocommit', True),
        'consume_results': True,
    }

    if scenario_config.get('ssl_disabled'):
        config['ssl_disabled'] = True
    if scenario_config.get('ssl_verify_cert') is False:
        config['ssl_verify_cert'] = False
    if scenario_config.get('init_command'):
        config['init_command'] = scenario_config['init_command']

    return connect(**config)


def format_size(bytes_val):
    """格式化字节大小"""
    if bytes_val is None:
        return 'N/A'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"


def format_uptime(seconds):
    """格式化运行时间"""
    seconds = int(seconds)
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    if secs > 0 or not parts:
        parts.append(f"{secs}秒")
    return " ".join(parts)


# ========== MySQL 内省函数 ==========

def introspect_session_user(conn) -> str:
    """获取当前会话用户名 (USER())"""
    cursor = conn.cursor()
    cursor.execute("SELECT USER()")
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def introspect_current_user(conn) -> str:
    """获取当前有效用户名 (CURRENT_USER())"""
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_USER()")
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def introspect_version(conn) -> str:
    """获取 MySQL 服务器版本 (VERSION())"""
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def introspect_database(conn) -> str:
    """获取当前选中的数据库名 (DATABASE())"""
    cursor = conn.cursor()
    cursor.execute("SELECT DATABASE()")
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def introspect_grants(conn, user: str = None) -> list:
    """获取用户权限列表 (SHOW GRANTS)"""
    cursor = conn.cursor()
    if user:
        cursor.execute(f"SHOW GRANTS FOR {user}")
    else:
        cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
    grants = []
    for row in cursor.fetchall():
        grant_str = row[0] if row else None
        if grant_str:
            grants.append(grant_str)
    cursor.close()
    return grants


def introspect_users(conn) -> list:
    """获取所有用户列表"""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT User, Host, authentication_string, plugin,
                   password_expired, password_last_changed,
                   max_questions, ssl_type
            FROM mysql.user
            ORDER BY User, Host
        """)
        users = cursor.fetchall()
    except MySQLError:
        users = []
    cursor.close()
    return users


def introspect_processlist(conn) -> list:
    """获取当前连接进程列表"""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SHOW PROCESSLIST")
    processes = cursor.fetchall()
    cursor.close()
    return processes


def introspect_user_privileges(conn) -> dict:
    """解析用户权限结构"""
    grants = introspect_grants(conn)
    privileges = {'global': [], 'database': {}, 'table': {}}

    for grant_str in grants:
        if not grant_str.startswith('GRANT '):
            continue
        main_part = grant_str[6:]
        on_parts = main_part.split(' ON ')
        if len(on_parts) < 2:
            continue
        priv_part = on_parts[0].strip()
        rest = on_parts[1]
        to_parts = rest.split(' TO ')
        obj_part = to_parts[0].strip() if to_parts else rest.strip()

        if obj_part == '*.*':
            privileges['global'].append(priv_part)
        elif obj_part.endswith('.*'):
            db_name = obj_part[:-2]
            if db_name not in privileges['database']:
                privileges['database'][db_name] = []
            privileges['database'][db_name].append(priv_part)
        elif '.' in obj_part:
            if obj_part not in privileges['table']:
                privileges['table'][obj_part] = []
            privileges['table'][obj_part].append(priv_part)
    return privileges


def introspect_users(conn) -> list:
    """获取所有用户列表"""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT User, Host, authentication_string, plugin,
                   password_expired, password_last_changed,
                   max_questions, ssl_type
            FROM mysql.user
            ORDER BY User, Host
        """)
        users = cursor.fetchall()
    except MySQLError:
        users = []
    cursor.close()
    return users


def introspect_processlist(conn) -> list:
    """获取当前所有连接进程 (SHOW PROCESSLIST)"""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SHOW PROCESSLIST")
    processes = cursor.fetchall()
    cursor.close()
    return processes


def introspect_status(conn, pattern: str = None) -> dict:
    """获取服务器状态变量 (SHOW STATUS)"""
    cursor = conn.cursor(dictionary=True)
    if pattern:
        cursor.execute(f"SHOW STATUS LIKE '{pattern}'")
    else:
        cursor.execute("SHOW STATUS")
    status = {}
    for row in cursor.fetchall():
        key = list(row.values())[0]
        value = list(row.values())[1]
        status[key] = value
    cursor.close()
    return status


def introspect_variables(conn, pattern: str = None) -> dict:
    """获取服务器系统变量 (SHOW VARIABLES)"""
    cursor = conn.cursor(dictionary=True)
    if pattern:
        cursor.execute(f"SHOW VARIABLES LIKE '{pattern}'")
    else:
        cursor.execute("SHOW VARIABLES")
    variables = {}
    for row in cursor.fetchall():
        key = list(row.values())[0]
        value = list(row.values())[1]
        variables[key] = value
    cursor.close()
    return variables


def introspect_master_status(conn) -> dict:
    """获取主服务器复制状态 (SHOW MASTER STATUS)"""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SHOW MASTER STATUS")
        row = cursor.fetchone()
        cursor.close()
        return row
    except MySQLError:
        cursor.close()
        return None


def introspect_slave_status(conn) -> dict:
    """获取从服务器复制状态 (SHOW SLAVE STATUS)"""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SHOW SLAVE STATUS")
        row = cursor.fetchone()
        cursor.close()
        return row
    except MySQLError:
        cursor.close()
        return None


# ========== 主程序 ==========
def main():
    config = load_config()
    scenarios = config.get('scenarios', {})

    print("=" * 80)
    print("MySQL 数据库内省探索报告")
    print("=" * 80)

    results = []

    for name, scenario in scenarios.items():
        print(f"\n{'=' * 80}")
        print(f"连接场景: {name}")
        print(f"地址: {scenario['host']}:{scenario['port']}")
        print("-" * 80)

        try:
            conn = create_connection(scenario)

            # ===== 服务器信息 =====
            version = introspect_version(conn)
            variables = introspect_variables(conn)
            status = introspect_status(conn)

            print(f"\n【服务器信息】")
            print(f"  版本: {version}")
            print(f"  版本注释: {variables.get('version_comment')}")
            print(f"  编译机器: {variables.get('version_compile_machine')}")
            print(f"  编译系统: {variables.get('version_compile_os')}")
            print(f"  默认存储引擎: {variables.get('default_storage_engine')}")
            print(f"  服务器字符集: {variables.get('character_set_server')}")
            print(f"  服务器排序规则: {variables.get('collation_server')}")

            uptime = int(status.get('Uptime', 0))
            print(f"  运行时间: {format_uptime(uptime)}")

            # ===== 时区配置 =====
            print(f"\n【时区配置】")
            print(f"  服务器时区: {variables.get('time_zone')}")
            print(f"  系统时区: {variables.get('system_time_zone')}")
            print(f"  日志时间戳: {variables.get('log_timestamps')}")

            # ===== SSL/TLS 配置 =====
            ssl_status = introspect_status(conn, 'Ssl%')
            print(f"\n【SSL/TLS 配置】")
            print(f"  SSL 支持: {variables.get('have_ssl', 'UNKNOWN')}")
            print(f"  当前连接加密: {'是 (' + ssl_status.get('Ssl_cipher', 'unknown') + ')' if ssl_status.get('Ssl_cipher') else '否'}")
            if ssl_status.get('Ssl_version'):
                print(f"  当前SSL版本: {ssl_status.get('Ssl_version')}")

            # ===== 复制配置 =====
            master_status = introspect_master_status(conn)
            slave_status = introspect_slave_status(conn)
            print(f"\n【复制配置】")
            print(f"  二进制日志: {'启用' if variables.get('log_bin') == 'ON' else '禁用'}")

            if master_status:
                print(f"  角色: 主服务器")
                print(f"  当前Binlog文件: {master_status.get('File')}")
                print(f"  当前Binlog位置: {master_status.get('Position')}")
            elif slave_status:
                print(f"  角色: 从服务器")
                print(f"  主服务器: {slave_status.get('Master_Host')}:{slave_status.get('Master_Port')}")
                print(f"  IO线程: {slave_status.get('Slave_IO_Running')}")
                print(f"  SQL线程: {slave_status.get('Slave_SQL_Running')}")
                print(f"  延迟秒数: {slave_status.get('Seconds_Behind_Master')}")
            else:
                print(f"  角色: 独立服务器")

            # ===== InnoDB 配置 =====
            innodb_vars = introspect_variables(conn, 'innodb%')
            print(f"\n【InnoDB 配置】")
            print(f"  InnoDB版本: {innodb_vars.get('innodb_version', 'N/A')}")
            buffer_pool = int(innodb_vars.get('innodb_buffer_pool_size', 0))
            print(f"  缓冲池大小: {format_size(buffer_pool)}")
            print(f"  刷新日志策略: {innodb_vars.get('innodb_flush_log_at_trx_commit', 'N/A')}")
            print(f"  刷新方法: {innodb_vars.get('innodb_flush_method', 'N/A')}")
            print(f"  锁等待超时: {innodb_vars.get('innodb_lock_wait_timeout', 'N/A')} 秒")

            # ===== 连接配置 =====
            print(f"\n【连接配置】")
            print(f"  最大连接数: {variables.get('max_connections')}")
            print(f"  当前连接数: {status.get('Threads_connected', 'N/A')}")
            print(f"  正在运行的线程: {status.get('Threads_running', 'N/A')}")
            print(f"  等待超时: {variables.get('wait_timeout')} 秒")
            print(f"  最大数据包: {format_size(int(variables.get('max_allowed_packet', 0)))}")

            # ===== 用户权限信息 =====
            session_user = introspect_session_user(conn)
            current_user = introspect_current_user(conn)
            privileges = introspect_user_privileges(conn)

            print(f"\n【用户权限信息】")
            print(f"  会话用户 (USER()): {session_user}")
            print(f"  有效用户 (CURRENT_USER()): {current_user}")

            if privileges['global']:
                print(f"  全局权限: {', '.join(privileges['global'])}")
            else:
                print(f"  全局权限: 无")

            if privileges['database']:
                print(f"  数据库权限:")
                for db, privs in privileges['database'].items():
                    print(f"    {db}: {', '.join(privs)}")

            if privileges['table']:
                print(f"  表级权限:")
                for table_key, privs in privileges['table'].items():
                    print(f"    {table_key}: {', '.join(privs)}")

            # 打印原始 GRANT 语句
            grants = introspect_grants(conn)
            if grants:
                print(f"\n  原始GRANT语句:")
                for i, grant in enumerate(grants[:5]):
                    print(f"    {grant}")
                if len(grants) > 5:
                    print(f"    ... 共 {len(grants)} 条")

            # ===== 获取所有用户 =====
            try:
                all_users = introspect_users(conn)
                print(f"\n【所有用户】")
                print(f"  用户总数: {len(all_users)}")
                for user in all_users[:20]:
                    ssl_info_str = f", SSL: {user.get('ssl_type', 'N/A')}" if user.get('ssl_type') else ""
                    expired = " [过期]" if user.get('password_expired') == 'Y' else ""
                    print(f"    {user['User']}@{user['Host']}{expired}{ssl_info_str}")
                if len(all_users) > 20:
                    print(f"  ... 共 {len(all_users)} 个用户")
            except MySQLError as e:
                print(f"  无法获取用户列表: {e}")

            # ===== 数据库信息 =====
            db_name = scenario['database']
            print(f"\n【数据库 '{db_name}' 信息】")

            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_TYPE, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH, ENGINE
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
            """, (db_name,))
            tables = cursor.fetchall()

            if tables:
                total_data = 0
                total_index = 0
                print(f"  表数量: {len(tables)}")
                for table in tables:
                    data_size = table['DATA_LENGTH'] or 0
                    index_size = table['INDEX_LENGTH'] or 0
                    total_data += data_size
                    total_index += index_size
                    rows = table['TABLE_ROWS'] or 0
                    print(f"    - {table['TABLE_NAME']}: {table['ENGINE']}, {rows} 行, "
                          f"数据 {format_size(data_size)}, 索引 {format_size(index_size)}")
                print(f"  总数据大小: {format_size(total_data)}")
                print(f"  总索引大小: {format_size(total_index)}")
            else:
                print(f"  表数量: 0")
            cursor.close()

            # ===== 特性支持 =====
            print(f"\n【支持的特性】")
            cursor = conn.cursor()
            features = [
                ("JSON", "SELECT JSON_OBJECT('test', 1)"),
                ("Window Functions", "SELECT ROW_NUMBER() OVER () FROM (SELECT 1) t"),
                ("CTE", "WITH cte AS (SELECT 1) SELECT * FROM cte"),
            ]
            for name, query in features:
                try:
                    cursor.execute(query)
                    print(f"  {name}: ✓ 支持")
                except MySQLError:
                    print(f"  {name}: ✗ 不支持")
            cursor.close()

            # ===== 当前连接进程 =====
            processes = introspect_processlist(conn)
            print(f"\n【当前连接进程】")
            print(f"  连接数: {len(processes)}")
            if processes and len(processes) <= 10:
                for proc in processes:
                    cmd = str(proc.get('Command', ''))[:50]
                    print(f"    ID: {proc.get('Id')}, User: {proc.get('User')}, DB: {proc.get('db')}, Command: {cmd}")
            elif len(processes) > 10:
                print(f"  (显示前10个, 共 {len(processes)} 个)")
                for proc in processes[:10]:
                    print(f"    ID: {proc.get('Id')}, User: {proc.get('User')}, DB: {proc.get('db')}")

            conn.close()
            results.append({'scenario': name, 'success': True, 'version': version})

        except MySQLError as e:
            print(f"\n连接失败: {e}")
            results.append({'scenario': name, 'success': False, 'error': str(e)})

    # ===== 汇总报告 =====
    print("\n" + "=" * 80)
    print("汇总报告")
    print("=" * 80)

    for result in results:
        if result['success']:
            print(f"  {result['scenario']}: ✓ 成功 - {result['version']}")
        else:
            print(f"  {result['scenario']}: ✗ 失败 - {result.get('error', 'Unknown error')}")


if __name__ == '__main__':
    main()
