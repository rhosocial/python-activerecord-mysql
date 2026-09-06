# 命令行界面

## 概述

MySQL 后端包含用于数据库操作的命令行界面。CLI 提供查询、自省和管理 MySQL 数据库的命令，无需编写 Python 代码。

CLI 命令分为两类：

1. **MySQL 特定命令** -- MySQL 独有的操作（query、introspect、info、status）
2. **核心继承命令** -- 所有后端共享（named-expression、named-procedure、named-migration、named-connection）

## 调用方式

安装包后 CLI 会注册为 `rhosocial-activerecord-mysql`：

```bash
pip install rhosocial-activerecord-mysql
```

然后直接调用命令：

```bash
rhosocial-activerecord-mysql <command> [options]
```

此命令在 `pyproject.toml` 中注册，等同于 `python -m rhosocial.activerecord.backend.impl.mysql`。

## 输出格式

CLI 通过 `-o` / `--output` 选项支持多种输出格式：

| 格式 | 描述 | 需要 Rich |
|------|------|----------|
| `table` | 带边框的人类可读表格（默认） | 是 |
| `json` | JSON 对象数组 | 否 |
| `csv` | 逗号分隔值 | 否 |
| `tsv` | 制表符分隔值 | 否 |

安装 Rich 时，`table` 格式提供带彩色边框的美化输出。当 Rich 不可用时，CLI 自动回退到 `json` 格式。

### Rich 集成

CLI 与 [Rich](https://github.com/Textualize/rich) 库集成以增强终端输出：

- **彩色边框**: Unicode 制表符用于表格边框
- **ASCII 回退**: 使用 `--rich-ascii` 强制 ASCII 边框（`+`、`-`、`|`）
- **自动检测**: 如果未安装 Rich，自动回退到 JSON 输出

```bash
# 默认表格输出（Unicode 边框）
rhosocial-activerecord-mysql query --host localhost --database mydb "SELECT * FROM users;"

# ASCII 边框（用于不支持 Unicode 的终端）
rhosocial-activerecord-mysql query --host localhost --database mydb --rich-ascii "SELECT * FROM users;"

# 强制 JSON 输出
rhosocial-activerecord-mysql query --host localhost --database mydb -o json "SELECT * FROM users;"
```

### 输出示例

**表格格式（默认）：**
```
┌─────┬─────────┬───────┐
│ id  │ name    │ email │
├─────┼─────────┼───────┤
│ 1   │ Alice   │ a@x   │
│ 2   │ Bob     │ b@x   │
└─────┴─────────┴───────┘
```

**JSON 格式：**
```json
[
  {"id": 1, "name": "Alice", "email": "a@x"},
  {"id": 2, "name": "Bob", "email": "b@x"}
]
```

**CSV 格式：**
```csv
id,name,email
1,Alice,a@x
2,Bob,b@x
```

**TSV 格式：**
```tsv
id	name	email
1	Alice	a@x
2	Bob	b@x
```

## MySQL 特定命令

### info

显示环境信息，无需数据库连接：

```bash
rhosocial-activerecord-mysql info
```

输出包括：
- MySQL 版本信息
- 协议支持状态
- 功能可用性

### query

直接执行 SQL 查询：

```bash
# 简单查询
rhosocial-activerecord-mysql query \
    --host localhost --port 3306 --database mydb \
    --user root --password secret \
    "SELECT * FROM users LIMIT 10"

# JSON 输出
rhosocial-activerecord-mysql query \
    --host localhost --port 3306 --database mydb \
    --user root --password secret \
    -o json "SELECT * FROM users LIMIT 10"
```

### introspect

检查数据库元数据：

```bash
# 列出所有表
rhosocial-activerecord-mysql introspect tables \
    --host localhost --port 3306 --database mydb

# 列出所有视图
rhosocial-activerecord-mysql introspect views \
    --host localhost --port 3306 --database mydb

# 获取数据库信息
rhosocial-activerecord-mysql introspect database \
    --host localhost --port 3306 --database mydb

# 获取完整表信息（列、索引、外键）
rhosocial-activerecord-mysql introspect table users \
    --host localhost --port 3306 --database mydb

# 查询特定详情
rhosocial-activerecord-mysql introspect columns users \
    --host localhost --port 3306 --database mydb
rhosocial-activerecord-mysql introspect indexes users \
    --host localhost --port 3306 --database mydb
```

#### 自省类型

| 类型 | 描述 |
|------|------|
| `tables` | 列出所有表 |
| `views` | 列出所有视图 |
| `table` | 描述特定表 |
| `columns` | 列出表的列 |
| `indexes` | 列出表的索引 |
| `foreign-keys` | 列出表的外键 |
| `triggers` | 列出触发器 |
| `database` | 数据库信息 |

### status

显示服务器状态：

```bash
rhosocial-activerecord-mysql status \
    --host localhost --port 3306 --database mydb
```

## 核心继承命令

这些命令**从核心 `python-activerecord` 库继承**，在所有后端上工作方式相同：

| 命令 | 源模块 | 描述 |
|------|--------|------|
| `named-expression` | `backend.named_expression` | 执行在 Python 中定义的类型安全参数化 SQL |
| `named-procedure` | `backend.named_expression.procedure` | 执行带事务支持的多查询编排 |
| `named-procedure-graph` | `backend.named_expression.procedure` | 执行过程图（DAG 工作流） |
| `named-migration` | `backend.migration` | 执行带依赖跟踪的版本化架构变更 |
| `named-connection` | `backend.named_connection` | 管理和测试命名连接配置 |

### 为什么使用命名功能？

命名功能让您**将复杂配置编码为单个名称**，避免冗长的命令行参数，并实现无法通过 CLI 标志单独表达的参数组合。

**命名连接** -- 封装所有连接参数：

```bash
# 不使用命名连接：冗长的参数列表
rhosocial-activerecord-mysql query \
    --host prod-db.example.com --port 3306 --database myapp \
    --user readonly --password secret --charset utf8mb4 \
    --conn-param ssl-ca=/path/to/ca.pem \
    --conn-param ssl-cert=/path/to/client-cert.pem \
    --conn-param ssl-key=/path/to/client-key.pem \
    "SELECT * FROM users"

# 使用命名连接：一个名称包含一切
rhosocial-activerecord-mysql query \
    --named-connection myapp.connections.prod_readonly \
    "SELECT * FROM users"
```

**命名表达式** -- 封装复杂查询逻辑：

```bash
# 不使用命名表达式：难以 shell 转义的复杂 SQL
rhosocial-activerecord-mysql query \
    "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE o.created_at >= '2026-01-01' GROUP BY u.id HAVING COUNT(o.id) > 5 ORDER BY order_count DESC LIMIT 20"

# 使用命名表达式：一个名称，类型安全的参数
rhosocial-activerecord-mysql named-expression \
    myapp.queries.high_value_customers \
    --param since=2026-01-01 --param min_orders=5
```

**命名过程** -- 封装多步骤工作流：

```bash
# 不使用命名过程：多个顺序命令
rhosocial-activerecord-mysql query "BEGIN TRANSACTION; ..."
rhosocial-activerecord-mysql query "UPDATE inventory ..."
rhosocial-activerecord-mysql query "INSERT INTO orders ..."
rhosocial-activerecord-mysql query "COMMIT;"

# 使用命名过程：一个命令，事务管理
rhosocial-activerecord-mysql named-procedure \
    myapp.workflows.place_order \
    --param user_id=42 --param product_id=100 --param quantity=3
```

| 功能 | 优势 |
|------|------|
| 命名连接 | 在可版本化的 Python 代码中存储连接配置；跨脚本共享 |
| 命名表达式 | 封装复杂 SQL；类型安全的参数；跨工具复用 |
| 命名过程 | 带事务管理的多查询工作流；并行执行 |
| 命名迁移 | 带依赖跟踪的版本化架构变更；支持上/下 |

### named-expression

执行命名表达式（在 Python 模块中定义的参数化 SQL）：

```bash
rhosocial-activerecord-mysql named-expression \
    myapp.queries.orders_by_status \
    --host localhost --port 3306 --database mydb \
    --user root --password secret \
    --param status=pending
```

### named-procedure

执行命名过程：

```bash
rhosocial-activerecord-mysql named-procedure \
    myapp.procedures.sync_users \
    --host localhost --port 3306 --database mydb \
    --user root --password secret
```

### named-migration

执行命名迁移：

```bash
# 运行迁移上
rhosocial-activerecord-mysql named-migration up add_users_table \
    --host localhost --port 3306 --database mydb \
    --user root --password secret

# 运行迁移下
rhosocial-activerecord-mysql named-migration down add_users_table \
    --host localhost --port 3306 --database mydb \
    --user root --password secret
```

### named-connection

管理和测试命名连接配置：

```bash
rhosocial-activerecord-mysql named-connection my_connection \
    --params host=localhost port=3306 database=mydb user=root password=secret
```

## 连接参数

所有需要数据库连接的命令接受以下通用参数：

| 参数 | 描述 |
|------|------|
| `--host` | 数据库服务器主机名 |
| `--port` | 数据库服务器端口 |
| `--database` | 数据库名称 |
| `--user` | 认证用户名 |
| `--password` | 认证密码 |
| `--charset` | 字符集（MySQL 特定） |
| `--async` | 使用异步后端 |
| `--named-connection` | 使用命名连接配置 |
| `--conn-param` | 额外连接参数 |
| `--log-level` | 设置日志级别（DEBUG、INFO、WARNING、ERROR） |

## 全局选项

| 选项 | 描述 |
|------|------|
| `-h`, `--help` | 显示帮助信息并退出 |
| `--log-level` | 设置日志级别（DEBUG、INFO、WARNING、ERROR） |

## 架构

CLI 遵循一致的架构：

```
backend/impl/mysql/
├── __main__.py          # 入口点，构建解析器，分发到处理器
└── cli/
    ├── __init__.py      # COMMAND_NAMES 列表，register_commands()
    ├── connection.py    # 连接参数解析和后端创建
    ├── output.py        # 输出格式提供者（Rich/JSON/CSV/TSV）
    │
    │   # MySQL 特定命令
    ├── info.py          # 'info' 命令处理器
    ├── query.py         # 'query' 命令处理器
    ├── introspect.py    # 'introspect' 命令处理器
    ├── status.py        # 'status' 命令处理器
    │
    │   # 核心继承命令（薄适配器）
    ├── named_expression.py      # 委托给核心 named_expression.cli
    ├── named_procedure.py       # 委托给核心 named_expression.procedure.cli
    ├── named_procedure_graph.py # 委托给核心 named_expression.procedure.cli
    ├── named_migration.py       # 委托给核心 migration.cli
    └── named_connection.py      # 委托给核心 named_connection.cli
```

## 另请参阅

- [安装指南](../installation_and_configuration/installation.md) -- 安装说明
- [连接管理](../installation_and_configuration/pool.md) -- 连接配置
- [核心命名功能](https://github.com/Rhosocial/python-activerecord/tree/main/docs/zh_CN) -- 命名连接、表达式、过程、迁移文档

💡 *AI 提示:* "如何从命令行列出 MySQL 数据库中的所有表？"
