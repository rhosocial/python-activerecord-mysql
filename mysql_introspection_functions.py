#!/usr/bin/env python3
"""
MySQL 内省函数模块

定义 MySQL 特有的内省函数作为独立函数:
- USER(): 当前会话用户
- CURRENT_USER(): 当前有效用户
- VERSION(): 服务器版本
- DATABASE(): 当前数据库
- SHOW GRANTS: 用户权限
- SHOW PROCESSLIST: 进程列表
- SHOW STATUS: 状态变量
- SHOW VARIABLES: 系统变量
- SHOW MASTER STATUS: 主服务器状态
- SHOW SLAVE STATUS: 从服务器状态

这些函数可以直接调用, 也可以被 explore_mysql.py 等脚本使用。
"""

from typing import Optional, List, Dict, Any
from mysql.connector import Error as MySQLError


# ========== 基础内省函数 ==========

def introspect_session_user(conn) -> str:
    """获取当前会话用户名

    MySQL 内省函数:
    - USER(): 返回当前 MySQL 会话的用户名和主机名
    - 格式: 'user_name@host_name'

    示例:
        >>> user = introspect_session_user(conn)
        >>> print(user)  # 'root@localhost'
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT USER() AS session_user")
    row = cursor.fetchone()
    cursor.close()
    return row['session_user'] if row else None


def introspect_current_user(conn) -> str:
    """获取当前有效用户名

    MySQL 内省函数:
    - CURRENT_USER(): 返回用于权限验证的用户名和主机名
    - 格式: 'user_name@host_name'

    与 USER() 的区别:
    - USER() 是实际连接的用户
    - CURRENT_USER() 是权限检查时使用的用户身份
    - 如果使用代理用户或角色, 两者可能不同

    示例:
        >>> user = introspect_current_user(conn)
        >>> print(user)  # 'root@%'
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT CURRENT_USER() AS current_user")
    row = cursor.fetchone()
    cursor.close()
    return row['current_user'] if row else None


def introspect_version(conn) -> str:
    """获取 MySQL 服务器版本

    MySQL 内省函数:
    - VERSION(): 返回 MySQL 服务器版本字符串
    - 格式: 'major.minor.patch' (如 '8.0.45')
    - 可能包含后缀: '8.0.45-log' 或 '5.7.44-community'

    示例:
        >>> ver = introspect_version(conn)
        >>> print(ver)  # '8.0.45'
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT VERSION() AS version")
    row = cursor.fetchone()
    cursor.close()
    return row['version'] if row else None


def introspect_database(conn) -> str:
    """获取当前选中的数据库名

    MySQL 内省函数:
    - DATABASE(): 返回当前选中的数据库名
    - 如果没有选择数据库, 返回 NULL

    示例:
        >>> db = introspect_database(conn)
        >>> print(db)  # 'test_db' or None
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DATABASE() AS database")
    row = cursor.fetchone()
    cursor.close()
    return row['database'] if row else None


def introspect_server_version(conn) -> dict:
    """获取服务器版本详细信息

    返回版本号的各个组成部分:
    - major: 主版本号
    - minor: 次版本号
    - patch: 补丁版本号
    - full: 完整版本字符串

    示例:
        >>> ver = introspect_server_version(conn)
        >>> print(ver)
        {'major': 8, 'minor': 0, 'patch': 45, 'full': '8.0.45'}
    """
    version_str = introspect_version(conn)
    if not version_str:
        return {'major': 0, 'minor': 0, 'patch': 0, 'full': None}

    # 解析版本号
    parts = version_str.split('.')
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1].split('-')[0]) if len(parts) > 1 else 0
    patch = int(parts[2].split('-')[0]) if len(parts) > 2 else 0

    return {
        'major': major,
        'minor': minor,
        'patch': patch,
        'full': version_str
    }


# ========== 权限内省函数 ==========

def introspect_grants(conn, user: str = None) -> List[str]:
    """获取用户权限列表

    MySQL 内省函数:
    - SHOW GRANTS: 显示用户权限
    - SHOW GRANTS FOR CURRENT_USER(): 当前用户的权限
    - SHOW GRANTS FOR 'user'@'host': 指定用户的权限

    GRANT 语句格式:
    - GRANT ALL PRIVILEGES ON *.* TO 'user'@'host'         (全局权限)
    - GRANT SELECT, INSERT ON db_name.* TO 'user'@'host'    (数据库权限)
    - GRANT SELECT ON db_name.table_name TO 'user'@'host'   (表权限)

    Args:
        conn: 数据库连接
        user: 可选,指定用户 (格式: 'user'@'host'), 默认为当前用户

    Returns:
        GRANT 语句字符串列表

    示例:
        >>> grants = introspect_grants(conn)
        >>> for g in grants:
        ...     print(g)
        GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION
    """
    cursor = conn.cursor(dictionary=True)

    if user:
        cursor.execute(f"SHOW GRANTS FOR {user}")
    else:
        cursor.execute("SHOW GRANTS FOR CURRENT_USER()")

    grants = []
    for row in cursor.fetchall():
        # 结果是字典, 需要获取第一个值
        grant_str = list(row.values())[0] if row else None
        if grant_str:
            grants.append(grant_str)

    cursor.close()
    return grants


def introspect_user_privileges(conn) -> dict:
    """解析用户权限结构

    将 GRANT 语句解析为结构化的权限信息:
    - global: 全局权限列表
    - database: 数据库级别权限 {db_name: [privileges]}
    - table: 表级别权限 {table_key: [privileges]}

    GRANT 语句格式:
    - GRANT ALL PRIVILEGES ON *.* TO 'user'@'host'         (全局)
    - GRANT SELECT, INSERT ON db_name.* TO 'user'@'host'    (数据库)
    - GRANT SELECT ON db_name.table_name TO 'user'@'host'   (表)

    示例:
        >>> privs = introspect_user_privileges(conn)
        >>> print(privs['global'])
        ['ALL PRIVILEGES']
        >>> print(privs['database'])
        {'test_db': ['SELECT', 'INSERT']}
    """
    grants = introspect_grants(conn)

    privileges = {
        'global': [],
        'database': {},
        'table': {}
    }

    for grant_str in grants:
        if not grant_str.startswith('GRANT '):
            continue

        # 解析: GRANT [privilege] ON [object] TO [user]
        main_part = grant_str[6:]  # 去掉 "GRANT "
        on_parts = main_part.split(' ON ')

        if len(on_parts) < 2:
            continue

        priv_part = on_parts[0].strip()
        rest = on_parts[1]

        # 提取对象部分
        to_parts = rest.split(' TO ')
        obj_part = to_parts[0].strip() if to_parts else rest.strip()

        # 分类存储
        if obj_part == '*.*':
            privileges['global'].append(priv_part)
        elif obj_part.endswith('.*'):
            # 数据库级别: db_name.*
            db_name = obj_part[:-2]
            if db_name not in privileges['database']:
                privileges['database'][db_name] = []
            privileges['database'][db_name].append(priv_part)
        elif '.' in obj_part and '*' not in obj_part:
            # 表级别: db_name.table_name
            if obj_part not in privileges['table']:
                privileges['table'][obj_part] = []
            privileges['table'][obj_part].append(priv_part)

    return privileges


def introspect_users(conn) -> List[Dict]:
    """获取 MySQL 服务器上所有用户列表

    查询 mysql.user 系统表获取用户信息:
    - User: 用户名
    - Host: 允许连接的主机
    - authentication_string: 认证字符串 (密码哈希)
    - plugin: 认证插件
    - password_expired: 密码是否过期
    - password_last_changed: 密码最后修改时间
    - max_questions: 每小时最大查询数限制
    - ssl_type: SSL 连接要求

    示例:
        >>> users = introspect_users(conn)
        >>> for u in users:
        ...     print(f"{u['User']}@{u['Host']}")
        root@%
        mysql.sys@%
    """
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


# ========== 进程内省函数 ==========

def introspect_processlist(conn) -> List[Dict]:
    """获取当前所有连接进程

    MySQL 内省函数:
    - SHOW PROCESSLIST: 显示所有当前线程

    返回字段:
    - Id: 线程标识符
    - User: 用户名
    - Host: 客户端主机
    - db: 当前数据库
    - Command: 线程命令类型 (Query, Sleep, Connect 等)
    - Time: 线程当前状态持续时间 (秒)
    - State: 线程状态
    - Info: 线程执行的语句

    常见 Command 类型:
    - Query: 正在执行查询
    - Sleep: 空闲等待
    - Connect: 正在连接
    - Binlog Dump: 正在发送二进制日志
    - Killed: 被终止

    示例:
        >>> procs = introspect_processlist(conn)
        >>> print(f"当前连接数: {len(procs)}")
        当前连接数: 5
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SHOW PROCESSLIST")
    processes = cursor.fetchall()
    cursor.close()
    return processes


# ========== 状态变量内省函数 ==========

def introspect_status(conn, pattern: str = None) -> Dict[str, str]:
    """获取服务器状态变量

    MySQL 内省函数:
    - SHOW STATUS: 显示服务器状态信息
    - SHOW GLOBAL STATUS: 全局状态
    - SHOW SESSION STATUS: 会话状态

    常见状态变量:
    - Uptime: 服务器运行秒数
    - Threads_connected: 当前连接数
    - Threads_running: 正在运行的线程数
    - Connections: 总连接数
    - Aborted_connects: 中断的连接数
    - Bytes_received: 接收的字节数
    - Bytes_sent: 发送的字节数
    - Qcache_hits: 查询缓存命中数
    - Slow_queries: 慢查询数量

    Args:
        conn: 数据库连接
        pattern: 可选的匹配模式 (如 'Threads%')

    示例:
        >>> status = introspect_status(conn, 'Threads%')
        >>> print(status['Threads_connected'])
        '5'
    """
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


def introspect_variables(conn, pattern: str = None) -> Dict[str, str]:
    """获取服务器系统变量

    MySQL 内省函数:
    - SHOW VARIABLES: 显示服务器系统变量
    - SHOW GLOBAL VARIABLES: 全局变量
    - SHOW SESSION VARIABLES: 会话变量

    常见变量:
    - version: 版本号
    - max_connections: 最大连接数
    - character_set_server: 服务器字符集
    - collation_server: 服务器排序规则
    - time_zone: 时区设置
    - innodb_buffer_pool_size: InnoDB 缓冲池大小
    - log_bin: 二进制日志开关

    Args:
        conn: 数据库连接
        pattern: 可选的匹配模式 (如 'innodb%')

    示例:
        >>> vars = introspect_variables(conn, 'max%')
        >>> print(vars['max_connections'])
        '151'
    """
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


# ========== 复制内省函数 ==========

def introspect_master_status(conn) -> Optional[Dict]:
    """获取主服务器复制状态

    MySQL 内省函数:
    - SHOW MASTER STATUS: 显示二进制日志状态

    返回字段:
    - File: 当前二进制日志文件名
    - Position: 当前二进制日志位置
    - Binlog_Do_DB: 需要复制的数据库
    - Binlog_Ignore_DB: 忽略复制的数据库

    示例:
        >>> status = introspect_master_status(conn)
        >>> if status:
        ...     print(f"Binlog: {status['File']}, Position: {status['Position']}")
        Binlog: binlog.000002, Position: 12345
    """
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SHOW MASTER STATUS")
        row = cursor.fetchone()
        cursor.close()
        return row
    except MySQLError:
        cursor.close()
        return None


def introspect_slave_status(conn) -> Optional[Dict]:
    """获取从服务器复制状态

    MySQL 内省函数:
    - SHOW SLAVE STATUS: 显示从服务器复制状态

    返回字段:
    - Master_Host: 主服务器地址
    - Master_Port: 主服务器端口
    - Master_User: 连接主服务器的用户
    - Slave_IO_Running: IO 线程状态 (Yes/No)
    - Slave_SQL_Running: SQL 线程状态 (Yes/No)
    - Seconds_Behind_Master: 与主服务器的延迟秒数
    - Last_Error: 最后的错误信息
    - Relay_Master_Log_File: 当前正在读取的主服务器 Binlog 文件
    - Exec_Master_Log_Pos: 已执行的主服务器 Binlog 位置

    示例:
        >>> status = introspect_slave_status(conn)
        >>> if status:
        ...     print(f"IO: {status['Slave_IO_Running']}, SQL: {status['Slave_SQL_Running']}")
        IO: Yes, SQL: Yes
    """
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SHOW SLAVE STATUS")
        row = cursor.fetchone()
        cursor.close()
        return row
    except MySQLError:
        cursor.close()
        return None


# ========== 组合函数 ==========

def get_user_privileges_info(conn) -> dict:
    """获取完整的用户权限信息 (组合函数)

    组合多个内省函数的结果:
    - introspect_session_user(): 会话用户
    - introspect_current_user(): 有效用户
    - introspect_grants(): 原始 GRANT 语句
    - introspect_user_privileges(): 解析后的权限结构

    示例:
        >>> info = get_user_privileges_info(conn)
        >>> print(info['session_user'])
        root@localhost
        >>> print(info['privileges']['global'])
        ['ALL PRIVILEGES']
    """
    return {
        'session_user': introspect_session_user(conn),
        'current_user': introspect_current_user(conn),
        'grants_raw': introspect_grants(conn),
        'privileges': introspect_user_privileges(conn)
    }


def get_connection_info(conn) -> dict:
    """获取连接相关信息 (组合函数)

    组合多个内省函数的结果:
    - introspect_database(): 当前数据库
    - introspect_version(): 服务器版本
    - introspect_session_user(): 会话用户
    - introspect_current_user(): 有效用户

    示例:
        >>> info = get_connection_info(conn)
        >>> print(info['version'])
        8.0.45
    """
    return {
        'database': introspect_database(conn),
        'version': introspect_version(conn),
        'server_version': introspect_server_version(conn),
        'session_user': introspect_session_user(conn),
        'current_user': introspect_current_user(conn)
    }


def get_replication_info(conn) -> dict:
    """获取复制配置信息 (组合函数)

    组合多个内省函数的结果:
    - introspect_variables(): log_bin 等变量
    - introspect_master_status(): 主服务器状态
    - introspect_slave_status(): 从服务器状态

    示例:
        >>> info = get_replication_info(conn)
        >>> print(info['role'])
        master
    """
    variables = introspect_variables(conn, 'log_bin%')

    info = {
        'binary_log_enabled': variables.get('log_bin') == 'ON',
        'is_master': False,
        'is_slave': False
    }

    master_status = introspect_master_status(conn)
    if master_status:
        info['is_master'] = True
        info['master_status'] = master_status

    slave_status = introspect_slave_status(conn)
    if slave_status:
        info['is_slave'] = True
        info['slave_status'] = slave_status

    if info['is_master'] and info['is_slave']:
        info['role'] = 'master_slave'
    elif info['is_master']:
        info['role'] = 'master'
    elif info['is_slave']:
        info['role'] = 'slave'
    else:
        info['role'] = 'standalone'

    return info


# ========== 使用示例 ==========

if __name__ == '__main__':
    import mysql.connector

    # 示例连接 (需要替换为实际配置)
    print("MySQL 内省函数模块")
    print("=" * 50)
    print("可用函数:")
    print("  - introspect_session_user(conn)  # 获取会话用户")
    print("  - introspect_current_user(conn)  # 获取有效用户")
    print("  - introspect_version(conn)        # 获取服务器版本")
    print("  - introspect_database(conn)       # 获取当前数据库")
    print("  - introspect_grants(conn)         # 获取用户权限")
    print("  - introspect_user_privileges(conn) # 解析权限结构")
    print("  - introspect_users(conn)          # 获取所有用户")
    print("  - introspect_processlist(conn)    # 获取进程列表")
    print("  - introspect_status(conn)         # 获取状态变量")
    print("  - introspect_variables(conn)      # 获取系统变量")
    print("  - introspect_master_status(conn)  # 获取主服务器状态")
    print("  - introspect_slave_status(conn)   # 获取从服务器状态")
