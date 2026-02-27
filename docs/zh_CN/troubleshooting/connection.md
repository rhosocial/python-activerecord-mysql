# 常见连接错误

## 概述

本节介绍 MySQL 连接常见错误及解决方案。

## 连接被拒绝 (Connection Refused)

### 错误信息
```
ERROR 2003 (HY000): Can't connect to MySQL server
```

### 原因
- MySQL 服务未运行
- 端口错误
- 防火墙阻止

### 解决方案
```bash
# 检查 MySQL 是否运行
sudo systemctl status mysql

# 检查端口
telnet localhost 3306
```

## 认证失败 (Authentication Failed)

### 错误信息
```
ERROR 1045 (28000): Access denied for user 'root'@'localhost'
```

### 原因
- 用户名或密码错误
- 用户没有远程访问权限

### 解决方案
```sql
-- 在 MySQL 服务器上执行
CREATE USER 'user'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON database.* TO 'user'@'%';
FLUSH PRIVILEGES;
```

## 连接超时 (Connection Timeout)

### 错误信息
```
ERROR 2003: Can't connect to MySQL server (110)
```

### 原因
- 网络问题
- connect_timeout 设置过短

### 解决方案
```python
config = MySQLConnectionConfig(
    host='remote.host.com',
    connect_timeout=30,  # 增加超时时间
)
```

## SSL 连接错误

### 错误信息
```
ERROR 2026 (HY000): SSL connection error
```

### 原因
- SSL 证书问题
- SSL 配置错误

### 解决方案
```python
config = MySQLConnectionConfig(
    host='remote.host.com',
    ssl_verify_cert=False,  # 禁用证书验证（仅测试环境）
)
```

💡 *AI 提示词：* "MySQL 连接错误如何排查？"
