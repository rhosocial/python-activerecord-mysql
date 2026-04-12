# MySQL DDL 操作

MySQL 后端支持与核心库相同的类型安全 DDL 表达式。

## 支持的操作

| 操作 | MySQL 支持 | 备注 |
|----------|--------------|-------|
| `CreateTableExpression` | ✅ 完整 | PRIMARY KEY, NOT NULL, UNIQUE 等 |
| `DropTableExpression` | ✅ 完整 | IF EXISTS 支持 |
| `AlterTableExpression` | ✅ 完整 | ADD/DROP COLUMN |
| `CreateIndexExpression` | ✅ 完整 | 索引类型 (BTREE, HASH) |
| `DropIndexExpression` | ✅ 完整 | |
| `CreateViewExpression` | ✅ 完整 | MySQL ALGORITHM 选项 |
| `DropViewExpression` | ✅ 完整 | |

## MySQL 特性

### ALGORITHM 选项

MySQL 视图支持 ALGORITHM 来控制执行方式：

```python
from rhosocial.activerecord.backend.expression import ViewOptions, ViewAlgorithm

create_view = CreateViewExpression(
    dialect,
    view_name="optimized_view",
    query=query,
    options=ViewOptions(algorithm=ViewAlgorithm.MERGE)
)
```

### 存储引擎

MySQL 支持指定存储引擎：

```python
create_table = CreateTableExpression(
    dialect,
    table_name="users",
    columns=columns,
    dialect_options={"engine": "InnoDB"}
)
```

## 运行示例

```bash
cd python-activerecord-mysql
source .venv3.8/bin/activate
PYTHONPATH=src python docs/examples/chapter_04_ddl/ddl.py
```

示例测试：
1. 创建带约束的表
2. 使用 IF NOT EXISTS 创建表
3. ALTER TABLE - 添加列
4. ALTER TABLE - 删除列
5. 使用 IF EXISTS 删除表
6. 内省验证架构变化

> **注意**：MySQL 具有与 SQLite 不同的 ALTER TABLE 支持。完整的 MySQL DDL 功能请参考 [MySQL 9.6 文档](https://dev.mysql.com/doc/refman/9.6/en/sql-statements.html)。