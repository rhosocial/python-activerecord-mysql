# 故障排除

本节介绍常见的 MySQL 后端问题及其解决方案。

## 内容

- [连接错误](connection.md)：错误代码、诊断和自动恢复
- [性能问题](performance.md)：慢查询分析和优化

## 常见问题

### 连接被拒绝 (2003)

```
Can't connect to MySQL server on 'localhost' (111)
```

验证 MySQL 服务器是否正在运行并监听预期端口。检查 `host`、`port` 和 `bind-address` 设置。

### 访问被拒绝 (1045)

```
Access denied for user 'root'@'localhost' (using password: YES)
```

验证凭据以及用户是否有权从您的主机连接。MySQL 授权是主机特定的 -- 允许从 `localhost` 连接的用户可能不允许从 `127.0.0.1` 连接。

### 连接数过多 (1040)

```
Too many connections
```

MySQL 有 `max_connections` 限制（默认 151）。在 `my.cnf` 中增加它或关闭空闲连接。按需连接模型意味着每个 `configure()` 调用都会创建连接 -- 确保使用后断开连接。

### 连接丢失 (2013)

```
Lost connection to MySQL server during query
```

这通常发生在大型结果集或长时间运行的查询中。在 MySQL 配置中增加 `net_read_timeout` 和 `net_write_timeout`，或将大型操作分解为更小的批次。

### 字符集问题

如果看到乱码 Unicode 数据或 `incorrect string value` 错误，确保连接字符集和列字符集都设置为 `utf8mb4`：

```python
config = MySQLConnectionConfig(
    ...,
    charset='utf8mb4',
)
```

同时验证 MySQL 服务器默认字符集：

```sql
SHOW VARIABLES LIKE 'character_set%';
```

### 死锁 (1213)

```
Deadlock found when trying to get lock; try restarting transaction
```

InnoDB 自动检测死锁并回滚开销较低的事务。捕获异常并使用指数退避重试。预防策略请参阅[死锁处理](../transaction_support/deadlock.md)。

### 性能建议

- 使用 `EXPLAIN` 分析慢查询（参见 [EXPLAIN](../backend_specific_features/explain.md)）
- 为 WHERE、JOIN 和 ORDER BY 子句添加适当的索引
- 避免 `SELECT *` -- 只获取需要的列
- 使用连接超时防止挂起连接

AI 提示: "如何诊断应用程序中的 MySQL 连接超时？"
