# 性能问题

## 概述

本节介绍 MySQL 性能问题及优化方法。

## 慢查询分析

### 启用慢查询日志

```sql
-- 查看慢查询配置
SHOW VARIABLES LIKE 'slow_query_log%';

-- 启用慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
```

### 使用 EXPLAIN 分析查询

后端提供 `ExplainExpression` 类用于生成 EXPLAIN 语句。**请勿直接执行原始 EXPLAIN SQL** — 应使用表达式系统：

```python
from rhosocial.activerecord.backend.expression.statements.explain import (
    ExplainExpression,
    ExplainOptions,
    ExplainFormat,
)

# 构建查询表达式
query = User.query().where(User.c.name == "Tom").select(User.c.id, User.c.name)

# 基本 EXPLAIN
explain = ExplainExpression(dialect, statement=query)
sql, params = explain.to_sql()
# 输出: EXPLAIN SELECT `id`, `name` FROM `users` WHERE `name` = %s

# EXPLAIN ANALYZE（执行并显示实际统计信息）
explain_analyze = ExplainExpression(
    dialect,
    statement=query,
    options=ExplainOptions(analyze=True),
)

# EXPLAIN JSON 格式
explain_json = ExplainExpression(
    dialect,
    statement=query,
    options=ExplainOptions(format=ExplainFormat.JSON),
)

# EXPLAIN TREE 格式（MySQL 8.0.16+）
explain_tree = ExplainExpression(
    dialect,
    statement=query,
    options=ExplainOptions(format=ExplainFormat.TREE),
)
```

## 常见性能问题

### 1. 缺少索引

```sql
-- 添加索引
CREATE INDEX idx_name ON users(name);
```

### 2. SELECT *

```python
# 避免 SELECT *，只查询需要的列
users = User.query().select(User.c.id, User.c.name).all()
```

### 3. N+1 查询问题

```python
# 使用 with_() 预加载关联数据，避免 N+1 查询
users = User.query().with_('posts').all()

# 加载嵌套关联
users = User.query().with_('posts.comments').all()

# 带查询修饰符加载
users = User.query().with_(('posts', lambda q: q.limit(5))).all()
```

### 4. JSON 类型性能（MySQL 5.6 vs 5.7+）

存储 `dict` 或 `list` 类型时，后端使用 `MySQLJSONAdapter` 序列化数据。不同 MySQL 版本的存储行为有所不同：

| 特性 | MySQL 5.6 | MySQL 5.7+ |
|------|-----------|------------|
| JSON 数据类型 | 不支持 | 原生 JSON 类型 |
| 存储格式 | TEXT（字符串） | 二进制 JSON |
| 验证 | 无 | 自动验证 |
| JSON 函数 | 不可用 | JSON_EXTRACT 等 |
| 索引 | 不支持 | 通过生成列 |
| 最大大小 | 65,535 字节 | 1 GB |
| 性能 | 较慢 | 较快 |

```python
# 适配器自动处理版本差异
# MySQL 5.6: dict/list 存储为 TEXT（JSON 字符串）
# MySQL 5.7+: dict/list 存储为原生 JSON 类型

from rhosocial.activerecord.backend.impl.mysql.adapters import MySQLJSONAdapter

adapter = MySQLJSONAdapter()
data = {"name": "Tom", "tags": ["admin"]}

# 转换为数据库值（两个版本相同）
db_value = adapter.to_database(data, dict)
# 输出: '{"name": "Tom", "tags": ["admin"]}'

# 转换回 Python（两个版本相同）
python_value = adapter.from_database(db_value, dict)
# 输出: {'name': 'Tom', 'tags': ['admin']}
```

**建议**：新项目请使用 MySQL 8.0+ 以获得完整的 JSON 支持，包括 `JSON_TABLE` 函数。

## 连接超时

```python
config = MySQLConnectionConfig(
    connect_timeout=30,
    read_timeout=60,
    write_timeout=60,
)
```

💡 *AI 提示：* "如何优化 MySQL 查询性能？"
