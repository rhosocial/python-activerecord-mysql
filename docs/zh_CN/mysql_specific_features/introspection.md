# 数据库内省

MySQL 后端回答三个层面的问题：数据库声明了什么（来自 `information_schema` 与 `SHOW`）、它一直在做什么（六个运行层家族）、它的行里装了什么（三个数据层家族）。`backend.introspector` 是这三者的入口，本页上的每个答案都是 MySQL 自己的答案：这个引擎怎么回答，而不是跨方言消费者期待的形状。

## 概述

MySQL 内省系统位于 `backend.introspector` 属性中，提供：

- **数据库信息**：名称、版本、字符集、排序规则
- **表信息**：表列表、表详情、存储引擎、表注释
- **列信息**：列名、数据类型、是否可空、默认值、字符集
- **索引信息**：索引名、列、唯一性、索引类型（BTREE、FULLTEXT 等）
- **外键信息**：引用表、列映射、更新/删除行为
- **视图信息**：视图定义 SQL
- **触发器信息**：触发事件、执行时机
- **运行层答案**：未使用索引、I/O 计数器、运行事实、依赖边、引擎自身的 DDL
- **数据层答案**：逐列画像、取值列表、连接覆盖率

## MySQL 的答案

内省契约中的每个问题在方言上都有一个探针，而探针问的是眼前这台服务器，不是这个产品。下表是 MySQL 对全部二十一个问题的回答。先读 `False` 的几行：探针回答 `False` 意味着这个问题在这台服务器上问不出口，绝不意味着答案为空或为零。

| 探针 | MySQL 的回答 | 它把守的问题 |
|-------|---------------|--------------|
| `supports_introspection()` | `True` | 关于模式的任何问题 |
| `supports_database_info()` | `True` | 数据库的名称、字符集与排序规则 |
| `supports_table_introspection()` | `True` | 表及其存储槽位 |
| `supports_column_introspection()` | `True` | 列及其声明 |
| `supports_index_introspection()` | `True` | 索引、其列与类型 |
| `supports_foreign_key_introspection()` | `True` | 外键及其行为 |
| `supports_view_introspection()` | `True` | 视图及其定义 |
| `supports_trigger_introspection()` | `True` | 触发器、执行时机与定义 |
| `supports_table_storage_introspection()` | `True` | 每表的数据与索引字节数 |
| `supports_runtime_stats()` | `True` | 服务器自身一直在做什么 |
| `supports_table_stats()` | `True` | 每表的 I/O 计数器 |
| `supports_index_stats()` | `True` | 每索引的使用计数器 |
| `supports_unused_indexes_detection()` | 5.7.0 起 `True`，以下及适配前 `False` | 没有任何访问记录的索引 |
| `supports_object_dependencies()` | `True` | 对象依赖图 |
| `supports_ddl_extraction()` | `True` | 重建一个对象的文本 |
| `supports_ddl_extraction_native()` | `True` | 该文本是否出自引擎自身 |
| `supports_column_data_profile()` | `True` | 表的每一列里装了什么 |
| `supports_column_value_sample()` | `True` | 出现过哪些取值，各多少次 |
| `supports_join_coverage()` | `True` | 两列的取值域重叠多少 |
| `supports_partition_info()` | `False` | 核心库的分区家族 |
| `supports_extensions()` | `False` | 已安装的附加组件 |

`supports_unused_indexes_detection()` 是本页唯一一个答案取决于服务器版本的探针：MySQL 5.7.0 起为 `True`，以下为 `False`，因为 `sys.schema_unused_indexes` 属于 `sys` 模式，而 5.6 没有 `sys` 模式。在那里回答 `True` 会把一个定义期的问题变成执行期错误——`1146`，"table does not exist"——所以这里问的是版本访问器，而不是裸的 `True`。尚未适配的方言同样回答 `False`，因为还没有任何版本被确认。

`supports_partition_info()` 因继承而保持 `False`。MySQL 通过它自己的 `supports_partition_introspection()` 回答一张表的分区，其结果类型是 `MySQLPartitionInfo`，空答案表示"这张表没有分区"。核心库的分区家族在这个后端上没有可承诺的方法，所以该探针就照实说它无法承诺，而不是把它指向一个 MySQL 并未实现的家族。CLI 的 `partitions` 类型读的是引擎自己的开关。

`supports_extensions()` 同样因继承而保持 `False`：MySQL 的可安装单元是插件，而本后端没有为它们声明任何目录——没有任何东西把扩展家族映射到 `information_schema.PLUGINS` 或 `SHOW PLUGINS`，所以 `True` 背后没有答案。

另有两个开关超出核心库的集合，属于本后端自己：`supports_table_options_introspection()` 把守 `table-options` 家族，`supports_partition_introspection()` 把守 `partitions`。两者都回答 `True`，每个 CLI 类型都由各自的开关把守。`True` 只承诺语句能渲染、服务器会接受；它不说明答案的形状，也不说明代价，每个家族的代价都在描述该家族的地方写明。

## 基本用法

### 访问内省器

```python
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend

backend = MySQLBackend(
    host="localhost",
    port=3306,
    database="mydb",
    user="root",
    password="password"
)
backend.connect()

# 通过 introspector 属性访问
introspector = backend.introspector
```

### 获取数据库信息

```python
# 获取数据库基本信息
db_info = backend.introspector.get_database_info()
print(f"数据库名称: {db_info.name}")
print(f"版本: {db_info.version}")
print(f"字符集: {db_info.encoding}")
print(f"排序规则: {db_info.collation}")
```

### 列出表

```python
# 列出所有用户表
tables = backend.introspector.list_tables()
for table in tables:
    print(f"表: {table.name}, 类型: {table.table_type.value}")
    if table.comment:
        print(f"  注释: {table.comment}")

# 包含系统数据库的表（通常不需要）
all_tables = backend.introspector.list_tables(include_system=True)

# 过滤特定类型
base_tables = backend.introspector.list_tables(table_type="BASE TABLE")
views = backend.introspector.list_tables(table_type="VIEW")

# 检查表是否存在
if backend.introspector.table_exists("users"):
    print("users 表存在")

# 获取表详情
table_info = backend.introspector.get_table_info("users")
if table_info:
    print(f"Table name: {table_info.name}")
    print(f"Row estimate: {table_info.row_count}")
    print(f"Data bytes: {table_info.data_size_bytes}")
    print(f"Index bytes: {table_info.index_size_bytes}")
```

表记录回答名称、类型、注释、行数估计与数据/索引字节拆分；存储引擎是另一个问题，由 `get_table_options()` 回答（见 [存储引擎信息](#存储引擎信息)）。

### 查询列信息

```python
# List all columns of a table
columns = backend.introspector.list_columns("users")
for col in columns:
    nullable = "NOT NULL" if col.nullable.value == "NOT_NULL" else "NULLABLE"
    pk = " [PK]" if col.is_primary_key else ""
    charset = f" ({col.charset})" if col.charset else ""
    print(f"{col.name}: {col.data_type}{charset} {nullable}{pk}")
    if col.comment:
        print(f"  注释: {col.comment}")

# 获取主键信息
pk = backend.introspector.get_primary_key("users")
if pk:
    print(f"主键: {[c.name for c in pk.columns]}")

# 获取单列信息
col_info = backend.introspector.get_column_info("users", "email")
```

### 查询索引

```python
# 列出表的所有索引
indexes = backend.introspector.list_indexes("users")
for idx in indexes:
    idx_type = idx.index_type.value if idx.index_type else "BTREE"
    unique = "UNIQUE " if idx.is_unique else ""
    print(f"{unique}索引: {idx.name} ({idx_type})")
    for col in idx.columns:
        print(f"  - {col.name}")
```

### 查询外键

```python
# 列出表的外键
foreign_keys = backend.introspector.list_foreign_keys("posts")
for fk in foreign_keys:
    print(f"外键: {fk.name}")
    print(f"  列: {fk.columns} -> {fk.referenced_table}.{fk.referenced_columns}")
    print(f"  ON DELETE: {fk.on_delete.value}")
    print(f"  ON UPDATE: {fk.on_update.value}")
```

### 查询视图

```python
# 列出所有视图
views = backend.introspector.list_views()
for view in views:
    print(f"视图: {view.name}")

# 获取视图详情
view_info = backend.introspector.get_view_info("user_posts_summary")
if view_info:
    print(f"定义: {view_info.definition}")
```

### 查询触发器

```python
# 列出所有触发器
triggers = backend.introspector.list_triggers()
for trigger in triggers:
    print(f"触发器: {trigger.name} on {trigger.table_name}")

# 列出特定表的触发器
table_triggers = backend.introspector.list_triggers("users")
```

## MySQL 专属：ShowIntrospector

MySQL 提供独特的 `SHOW` 命令支持，可通过 `backend.introspector.show` 访问：

```python
# 访问 ShowIntrospector
show = backend.introspector.show

# SHOW CREATE TABLE
create_table = show.show_create_table("users")
print(f"建表语句:\n{create_table.create_statement}")

# SHOW CREATE VIEW
create_view = show.show_create_view("user_posts_summary")
print(f"建视图语句:\n{create_view.create_statement}")

# SHOW COLUMNS
columns = show.show_columns("users")
for col in columns:
    print(f"{col.field}: {col.type} {col.null} {col.key} {col.default}")

# SHOW INDEX
indexes = show.show_index("users")
for idx in indexes:
    print(f"索引: {idx.index_name}, 列: {idx.column_name}")

# SHOW TABLE STATUS
table_status = show.show_table_status("users")
print(f"引擎: {table_status.engine}")
print(f"行数: {table_status.rows}")
print(f"自增: {table_status.auto_increment}")

# SHOW TABLES
tables = show.show_tables()
for table in tables:
    print(f"表: {table}")

# SHOW DATABASES
databases = show.show_databases()
for db in databases:
    print(f"数据库: {db}")

# SHOW TRIGGERS
triggers = show.show_triggers("users")
for trigger in triggers:
    print(f"触发器: {trigger.trigger}, 事件: {trigger.event}")

# SHOW VARIABLES
variables = show.show_variables("character_set_server")
for var in variables:
    print(f"{var.variable_name}: {var.value}")

# SHOW STATUS
status = show.show_status("Threads_connected")
for s in status:
    print(f"{s.variable_name}: {s.value}")

# SHOW PROCESSLIST
processes = show.show_processlist()
for proc in processes:
    print(f"ID: {proc.id}, 用户: {proc.user}, 状态: {proc.state}")

# SHOW ENGINES
engines = show.show_engines()
for engine in engines:
    print(f"{engine.engine}: {'支持' if engine.support == 'YES' else '不支持'}")

# SHOW CHARSET
charsets = show.show_charset()
for charset in charsets:
    print(f"{charset.charset}: {charset.description}")

# SHOW COLLATION
collations = show.show_collation("utf8mb4")
for collation in collations:
    print(f"{collation.collation}: {collation.charset}")
```

## 异步 API

异步后端提供相同的内省方法，方法名与同步版本相同：

```python
from rhosocial.activerecord.backend.impl.mysql.backend.async_backend import AsyncMySQLBackend

backend = AsyncMySQLBackend(
    host="localhost",
    port=3306,
    database="mydb",
    user="root",
    password="password"
)
await backend.connect()

# 异步内省方法（方法名与同步版本相同）
db_info = await backend.introspector.get_database_info()
tables = await backend.introspector.list_tables()
columns = await backend.introspector.list_columns("users")

# 异步 SHOW 命令
create_table = await backend.introspector.show.show_create_table("users")
```

## 缓存管理

内省结果默认会被缓存以提高性能：

```python
# 清除所有内省缓存
backend.introspector.clear_cache()

# 使特定作用域的缓存失效
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

# 使所有表相关缓存失效
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE)

# 使特定表的缓存失效
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.TABLE,
    name="users"
)
```

## MySQL 特定行为

### 系统数据库

MySQL 默认排除以下系统数据库：

- `information_schema` — 元数据信息
- `performance_schema` — 性能监控
- `mysql` — 系统用户和权限
- `sys` — 系统视图和存储过程

如需包含这些数据库，使用 `include_system=True` 参数。

### 存储引擎信息

`IntrospectionTableInfo` 不携带存储引擎——表记录回答名称、类型、注释、行数估计与字节拆分，`extra` 保持为空。引擎、行格式、排序规则、创建选项与自增计数器属于 `table-options` 家族，从同一个 `information_schema.TABLES` 关系中回答：

```python
options = backend.introspector.get_table_options("users")
if options:
    print(f"Engine: {options.engine}")
    print(f"Row format: {options.row_format}")
    print(f"Collation: {options.table_collation}")
    print(f"Auto increment: {options.auto_increment}")
    print(f"Data bytes: {options.data_length}")
    print(f"Index bytes: {options.index_length}")
```

`list_table_options()` 一次回答所有基表，`get_table_options()` 对视图名或不存在的名字返回 `None`——视图没有存储引擎，半空的记录比什么都不说更糟。`data_length` 与 `index_length` 是服务器自己的记账，对 InnoDB 而言是来自表空间的估计而非精确字节数；`total_length` 把两个分量相加，不重算其中任何一个。

### 字符集和排序规则

MySQL 列信息包含字符集和排序规则：

```python
columns = backend.introspector.list_columns("users")
for col in columns:
    if col.charset:
        print(f"{col.name}: charset={col.charset}, collation={col.collation}")
```

### 索引类型

MySQL 通过 `information_schema.STATISTICS` 回答四种 `INDEX_TYPE` 取值：

| `INDEX_TYPE` | 说明 |
|--------------|------|
| `BTREE` | 默认索引类型 |
| `HASH` | 仅 Memory 引擎支持 |
| `FULLTEXT` | 全文索引 |
| `RTREE` | 空间索引（`SPATIAL` 是 DDL 关键字，不是 `INDEX_TYPE` 取值） |

`SPATIAL` 与 `RTREE` 都解析为 `IndexType.SPATIAL`；其余三种映射到同名成员。

```python
from rhosocial.activerecord.backend.introspection.types import IndexType

indexes = backend.introspector.list_indexes("articles")
for idx in indexes:
    if idx.index_type == IndexType.FULLTEXT:
        print(f"Full-text index: {idx.name}")
```

## 运行层家族

MySQL 实现了全部六个家族。每一个都是一次目录读取——DDL 是一次 `SHOW CREATE`——都不扫描用户的行，所以一个家族的代价是它读取的那个视图的代价，而不是数据库的大小。

| 家族 | 方法 | MySQL 数据源 | 代价 |
|------|------|--------------|------|
| 未使用索引 | `list_unused_indexes()` | `sys.schema_unused_indexes` | 一次全库视图读取 |
| 表计数器 | `list_table_usage_stats()` | `performance_schema.table_io_waits_summary_by_table` | 一次汇总读取 |
| 运行指标 | `list_runtime_metrics()` | `performance_schema.setup_instruments` | 一次全服务器插桩列表 |
| 索引计数器 | `list_index_usage_stats()` | `performance_schema.table_io_waits_summary_by_index_usage` | 一次汇总读取 |
| 依赖关系 | `list_object_dependencies()` | `information_schema.referential_constraints` | 一次目录读取 |
| DDL | `get_ddl_statement()` | `SHOW CREATE TABLE` | 一条语句，引擎侧完成 |

最容易丢失的是时态。这里每个计数器都是自统计信息上次重置以来：两个 `performance_schema` 汇总的窗口是服务器的运行时间——方言明确说计数器计的是自服务器启动以来，而不是某个可重置的纪元——而 `sys.schema_unused_indexes` 的窗口是表统计信息的上次重置。答案里没有任何东西标注窗口的起点，所以零表示"在服务器记得的那段时间里没有"，绝不是"从来没有"。缓存答案在这里也比声明层老得更快：昨天缓存的模式多半还是那个模式，而计数器描述的窗口一直在走。

### 未使用索引

列表就是视图自己的三列——对象模式、对象名、索引名——由本后端的格式化器按模式过滤，因为该视图是全库的，问某一个数据库不该意味着事后过滤其余部分。这个视图意味着什么：一个性能模式从未见到访问的索引，从该表统计信息上次重置起算。自重启以来没人查询过的表会报告它的全部索引，而视图只覆盖收集器插桩到的表。所以答案只是"值得复查"，绝不是"可以安全删除"。没被列出的索引是没有证据，而不是它被用过的证据。

探针就是上文那个 5.7 门槛；门槛以下类型被拒绝，列表查询根本不会发出。

### 表使用计数器

来自 `performance_schema.table_io_waits_summary_by_table`，每张被插桩的表一行，按 `OBJECT_SCHEMA` 过滤。投影把视图的大写地址列改名为公共的 `schema_name` 与 `table_name`，并携带 `count_read`、`count_write`、`count_fetch`、`count_insert`、`count_update` 与 `count_delete`。公共形状里的 `sequential_scans`、`indexed_scans`、`inserts`、`updates` 与 `deletes` 保持 `None`——MySQL 的汇总在这些槽位上没有计数器——六个计数器以视图自己的名字进入 `extra`。`estimated_row_count` 同样保持 `None`：该汇总不携带行数估计，MySQL 的估计住在 `information_schema.TABLES`，那是另一个来源、另一套刷新节奏，把它的数字摆在这些计数器旁边会显得比实际更相关。

读侧的零表示"收集器没有看到 I/O"，不是"冷"；写侧的零在拆分的另一侧表达同样的事实。两者都不是"完全没有活动"。

### 运行指标

列表读取 `performance_schema.setup_instruments`，它命名这台服务器上真正在被计数的东西。投影把 `NAME` 作为 `name`、`ENABLED` 作为 `value`、`TIMED` 作为 `kind`。该关系没有模式列且是全服务器的，所以格式化器不加模式过滤——在这里加过滤会因一个无意义的理由拒绝一条正确的查询。这回答的是"什么还活着"：未启用的插桩不产生行，因此没有哪个零会被读成空闲。`unit`、`description` 与 `source` 保持 `None`，因为该关系没有命名它们。

### 索引使用计数器

来自 `performance_schema.table_io_waits_summary_by_index_usage`，该模式中每张表的每个索引一行：`COUNT_STAR` 投影为 `scans`，`COUNT_FETCH` 投影为 `rows_fetched`。`rows_read` 保持 `None`，因为引擎不保留每索引的"读取行数"计数器，而一次取数不是一行；`size_bytes` 保持 `None`，因为汇总不携带它。与未使用列表不同，这里的零是一次测量，而一次扫描和一百万次扫描的差别正是这个家族存在的理由。模式过滤在格式化器里做，因为该汇总是全服务器的。

### 对象依赖

`information_schema.referential_constraints` 为每个外键记录一条边：约束、声明它的表、它引用的表以及它的删除规则。投影把 `TABLE_NAME` 命名为 `dependent`、`REFERENCED_TABLE_NAME` 命名为 `referenced`，并把 `DELETE_RULE` 作为 `action` 携带。`kind`、`dependent_type` 与 `referenced_type` 保持 `None`：该目录只覆盖外键，不记录哪个视图、触发器或例程提到了哪张表。这是一张真实的图，也是一张不完整的图。给出表名会把答案收窄到它的被依赖者；省略名字则返回整张图。

### DDL 提取

`SHOW CREATE TABLE`，按引擎自己的结果列名读取：`Table` 与 `Create Table`。通用解析器找的是 `ddl`、`sql` 或 `definition`，而这些在 `SHOW CREATE` 的行里一个都没有——所以 MySQL 覆盖了该解析器，而不是让一个引擎刚刚描述过的表被报告为没有 DDL。`native` 为 `True`：这段文本是引擎的读取，不是拼装。只渲染 `TABLE`。给出 `VIEW`、`PROCEDURE`、`FUNCTION` 或 `TRIGGER` 会抛出 `UnsupportedFeatureError`，因为它们各自使用不同的 `SHOW CREATE` 语句与结果列，而本后端尚未映射。引擎没有复现出任何东西时 `get_ddl_statement()` 返回 `None`，这与"没有这张表"不是同一个答案。

六个家族都走同一个内省器，同步与异步一致：

```python
backend.introspect_and_adapt()

if backend.dialect.supports_unused_indexes_detection():
    for index in backend.introspector.list_unused_indexes():
        print(f"{index.table_name}.{index.index_name}")

for edge in backend.introspector.list_object_dependencies("posts"):
    print(f"{edge.dependent} -> {edge.referenced} ({edge.action})")

ddl = backend.introspector.get_ddl_statement("orders")
if ddl is not None:
    print(ddl.native, ddl.ddl)
```

## 数据层家族

三个数据层家族测量行，而不是读目录。MySQL 没有逐列统计目录：`information_schema` 描述一列*声明*了什么，`ANALYZE TABLE` 刷新优化器的索引统计（`STATISTICS.CARDINALITY` 是每个索引前缀的一个估计），并不发布逐列分布。所以这里的每个数字都是在被问时计算出来的——对所看到的行精确，代价与表的大小成正比——并且画像是把 `source='aggregate'` 投影进它返回的每一行，而不是事后盖上去，这样把它与另一个引擎的估计相比较的消费者无需知道问的是哪个引擎就能区分两者。

| 家族 | 方法 | 代价 |
|------|------|------|
| 列画像 | `list_column_data_profiles(table)` | 每一列一次全表扫描 |
| 取值样本 | `sample_column_values(table, column, limit=100)` | 对该列一次分组扫描，再加一次排序 |
| 连接覆盖率 | `estimate_join_coverage(left_table, left_column, right_table, right_column)` | 两侧各读一次取值域，再加交集 |

### 列画像

表的每一列一个 `UNION ALL` 分支，每个分支读表一次：空值计数是对 `CASE` 的 `SUM`，去重计数是 `COUNT(DISTINCT ...)`，端点是引擎自己的 `MIN`/`MAX`，而 `COUNT(*)` 与分母共用同一次扫描。因此十列的表会被读十次——往返次数仍是一次，扫描次数不是。`null_fraction` 在解析器里推导（`null_count / row_count`），这样一个可能为零的行数从不需要在 SQL 里防护。空表回答 `null_fraction = None`，因为对零行求 `SUM` 是 NULL——那是没有测量，而不是"没有空值"——`min_value`/`max_value` 也为 `None`；`distinct_count` 与 `row_count` 是 `0`，那是测量值而非缺失。

复合语句的一个后果只在 Python 类型上看得见。MySQL 在 `UNION ALL` 的所有分支间为每个列位置解析出唯一的结果类型，所以 `min_value`——一个分支里装的是 `code` 的文本、另一个分支里是 `amount` 的小数——会以文本到达：`'1.00'`，而不是 `1.00`。数字是精确的；只有类型是联合的结果。小数端点请经由 `Decimal(str(value))` 读取。若未来某个格式化器改为对列做 CAST，就会为了让数字端点更漂亮而牺牲文本列的端点；每列一条查询能保住各自的本地类型，代价是每列一次往返，而那正是这个家族要避免的循环。

### 取值样本

对该列一次 `GROUP BY` 再加一次分组排序——与画像同一量级的代价，这也是两者分开调用的原因：只要列表的调用者不必为画像的去重计数和端点付费。`ORDER BY COUNT(*) DESC` 才让答案成为"最频繁的取值"而不是"最初的取值"，并列时按取值排序，使同一条查询的两次运行结果一致。上限作为参数绑定，所以调用者的整数永远不会被拼进语句文本。只投影 `value` 与 `count`：`frequency` 保持 `None`，因为引擎报告的是计数，分母由画像携带的行数给出。

`GROUP BY` 会把 NULL 归成一组，所以含 NULL 的列会有一个 `value` 为 `None` 的条目，而且它通常是最频繁的那个。在这个列表里 NULL 是取值域的一员，解析器不会跳过它——不同于别处那些按地址跳过的行。把列表读成"这一列的取值"的调用者不能假定每个条目都是取值；画像的 `null_fraction` 是同一事实的跨引擎度量。

### 连接覆盖率

两个分数来自同一条语句。对每一侧，分子统计同时也出现在另一侧的去重取值——对派生 `DISTINCT` 的 `COUNT(*)`——分母统计该侧去重后的非 NULL 取值。NULL 在两侧都被显式排除：否则 `DISTINCT` 会把 NULL 当作一个值并记下一次永远无法连接的匹配，而 `COUNT(DISTINCT ...)` 会静默跳过它。`NULLIF(..., 0)` 让没有可匹配值的列回答 NULL 而不是 `0.0`，使"什么都没匹配上"与"根本没有可匹配的东西"保持区别。这里没有 `* 1.0`：MySQL 对两个整数计数做除法已经返回带小数的 `DECIMAL`。排序规则不做调和，所以在不匹配的排序规则下这些分数是下界，绝不是上界。代价是两侧各为取值域读一次再加上交集，并且每一侧的分数还要为分母再走一遍——这正是它是独立调用、且从不成为画像一部分的原因。

```python
profiles = backend.introspector.list_column_data_profiles("orders")
for profile in profiles:
    print(profile.column_name, profile.null_fraction, profile.distinct_count,
          profile.row_count, profile.source)

samples = backend.introspector.sample_column_values("orders", "status", limit=20)
for sample in samples:
    print(sample.value, sample.count)    # value is None when NULL is a group

coverage = backend.introspector.estimate_join_coverage(
    "orders", "customer_id",
    "customers", "id",
)
print(coverage.left_coverage, coverage.right_coverage)
```

## 版本兼容性

不同 MySQL 版本的内省行为差异：

| 功能 | MySQL 5.7 | MySQL 8.0+ |
|------|-----------|------------|
| `information_schema` | 完整支持 | 完整支持 |
| `sys.schema_unused_indexes` | 支持 | 支持 |
| 不可见列 | 不支持 | 8.0.23 起支持 |
| 生成式隐藏主键 | 不支持 | 8.0.30 起支持 |
| JSON 表达式提取 | 有限支持 | 完整支持 |

## 版本与可用性下限

两个限制决定一个运行层或数据层家族到底能不能回答，二者都不是查询文本的属性。

| 家族 | 下限 | 缺少下限时的表现 |
|------|------|------------------|
| `unused-indexes` | MySQL 5.7.0，`sys` 模式随之出现 | 探针 `False`；CLI 以退出码 2 结束，不执行查询 |
| `table-stats`、`index-stats`、`runtime` | 安装时启用 `performance_schema` | 探针 `True`，答案为空 |
| 其余所有家族 | 此处未确立下限 | — |

`sys` 模式门槛是本后端唯一的版本门。`unused-indexes` 读取 `sys.schema_unused_indexes`，5.7 之前语句能渲染但服务器回答 `1146`，"table does not exist"——这个缺口就是这样被发现的：CLI 是第一个在 5.6 上到达该家族的调用者，它在执行期失败而不是在能力问题上失败。因此 `supports_unused_indexes_detection()` 返回 `version_at_least((5, 7, 0))` 而不是 `True`，门槛以下 CLI 不碰内省器就拒绝这次运行。未适配的方言同样回答 `False`，因为没人确认过的版本不是被声称的能力。

performance schema 是安装期选项，不是版本下限。`table-stats`、`index-stats` 与 `runtime` 读取它的关系，而收集器是在服务器安装时启用的（`performance_schema=ON`）。三个探针无条件回答 `True`，因为方言看不到服务器的启动选项，而能力确实存在——数据源是一项设置。在收集器关闭的服务器上这些家族返回空，而那个空答案不是对空闲的测量；实机测试在那类服务器上跳过这些家族，而不是把空答案当作缺陷。

探针回答 `False` 意味着"这个问题在这里问不出口"，而不是"什么都没有被使用"。它不表示没有索引被用过、没有表被读过，也不表示数据库没有索引：它表示这台服务器问不了。`False` 让调用者可以知情地走回退路径；空列表留给"问过了、但确实没有可报告的"。

探针不检查授权。这里没有确立任何权限下限：探针回答的是服务器及其设置，不是账号的权限。如果连接所用的账号没有读取 `sys` 或 `performance_schema` 的权限，引擎自己的错误会在执行时到达；探针当时说 `True`，是因为服务器能回答，而不是因为该账号可以问。

## 最佳实践

### 1. 使用缓存

内省操作涉及复杂的 `information_schema` 查询，建议利用缓存：

```python
# 首次查询会缓存结果
tables = backend.introspector.list_tables()

# 后续查询直接从缓存返回
tables_again = backend.introspector.list_tables()

# 只有在表结构变更后才需要清除缓存
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE, name="users")
```

### 2. 使用 SHOW 命令获取详细信息

当需要完整的建表语句时，使用 `SHOW CREATE TABLE`：

```python
# 获取完整建表语句（包含所有选项）
create_table = backend.introspector.show.show_create_table("users")
print(create_table.create_statement)
```

### 3. 批量操作

尽可能使用批量查询方法：

```python
# 好：一次查询获取所有列
columns = backend.introspector.list_columns("users")

# 避免：多次查询单列
for col_name in column_names:
    col = backend.introspector.get_column_info("users", col_name)  # 每次 I/O
```

## API 参考

### 内省方法

| 方法 | 说明 | 参数 |
|------|------|------|
| `get_database_info()` | 获取数据库信息 | 无 |
| `list_tables()` | 列出表 | `include_system`, `table_type`, `schema` |
| `get_table_info(name)` | 获取表详情 | `name`, `schema` |
| `table_exists(name)` | 检查表存在 | `name`, `schema` |
| `list_columns(table_name)` | 列出列 | `table_name`, `schema` |
| `get_column_info(table_name, column_name)` | 获取列详情 | `table_name`, `column_name`, `schema` |
| `get_primary_key(table_name)` | 获取主键 | `table_name`, `schema` |
| `list_indexes(table_name)` | 列出索引 | `table_name`, `schema` |
| `list_foreign_keys(table_name)` | 列出外键 | `table_name`, `schema` |
| `list_views()` | 列出视图 | `schema` |
| `get_view_info(name)` | 获取视图详情 | `name`, `schema` |
| `list_triggers(table_name)` | 列出触发器 | `table_name`, `schema` |
| `list_table_options()` | 所有基表的存储选项 | `schema` |
| `get_table_options(name)` | 单表的存储选项 | `name`, `schema` |
| `list_partitions(table_name)` | 单表的分区 | `table_name`, `schema` |
| `list_unused_indexes()` | 无访问记录的索引 | `schema` |
| `list_table_usage_stats()` | 每表 I/O 计数器 | `schema` |
| `list_runtime_metrics()` | 实时运行事实 | `schema` |
| `list_index_usage_stats()` | 每索引使用计数器 | `schema` |
| `list_object_dependencies(object_name)` | 外键依赖边 | `object_name`, `schema` |
| `get_ddl_statement(object_name, object_type)` | 单表由引擎自身给出的 DDL | `object_name`, `object_type`, `schema` |
| `list_column_data_profiles(table_name)` | 每列装了什么 | `table_name`, `schema` |
| `sample_column_values(table_name, column_name, limit)` | 最频繁的取值 | `table_name`, `column_name`, `limit`, `schema` |
| `estimate_join_coverage(left_table, left_column, right_table, right_column)` | 两列取值域的重叠 | 四个名称, `schema` |
| `clear_cache()` | 清除缓存 | 无 |
| `invalidate_cache(scope, ...)` | 使缓存失效 | `scope`, `name`, `table_name` |

### SHOW 命令方法

| 方法 | 说明 |
|------|------|
| `show_create_table(table_name)` | 获取建表语句 |
| `show_create_view(view_name)` | 获取建视图语句 |
| `show_columns(table_name)` | 显示列信息 |
| `show_index(table_name)` | 显示索引信息 |
| `show_tables()` | 显示表列表 |
| `show_databases()` | 显示数据库列表 |
| `show_table_status(table_name)` | 显示表状态 |
| `show_triggers(table_name)` | 显示触发器 |
| `show_variables(pattern)` | 显示系统变量 |
| `show_status(pattern)` | 显示状态变量 |
| `show_processlist()` | 显示进程列表 |
| `show_engines()` | 显示存储引擎 |
| `show_charset()` | 显示字符集 |
| `show_collation(pattern)` | 显示排序规则 |

## 命令行内省命令

MySQL 后端提供命令行内省命令，无需编写代码即可查询数据库元数据。

### 基本用法

```bash
# 列出所有表
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --host localhost --port 3306 --database mydb --user root --password secret

# 列出所有视图
python -m rhosocial.activerecord.backend.impl.mysql introspect views \
  --database mydb --user root

# 获取数据库信息
python -m rhosocial.activerecord.backend.impl.mysql introspect database \
  --database mydb --user root

# 包含系统表
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root --include-system
```

### 连接参数

支持通过命令行参数或环境变量配置连接：

| 参数 | 环境变量 | 说明 |
|------|----------|------|
| `--host` | `MYSQL_HOST` | 数据库主机（默认 localhost） |
| `--port` | `MYSQL_PORT` | 数据库端口（默认 3306） |
| `--database` | `MYSQL_DATABASE` | 数据库名称（必需） |
| `--user` | `MYSQL_USER` | 用户名（默认 root） |
| `--password` | `MYSQL_PASSWORD` | 密码 |
| `--charset` | `MYSQL_CHARSET` | 字符集（默认 utf8mb4） |

### 查询表详情

```bash
# 描述单个视图
python -m rhosocial.activerecord.backend.impl.mysql introspect views users_v \
  --database mydb --user root

# 仅查询列信息
python -m rhosocial.activerecord.backend.impl.mysql introspect columns users \
  --database mydb --user root

# 仅查询索引信息
python -m rhosocial.activerecord.backend.impl.mysql introspect indexes users \
  --database mydb --user root

# 仅查询外键信息
python -m rhosocial.activerecord.backend.impl.mysql introspect foreign-keys posts \
  --database mydb --user root

# 查询触发器
python -m rhosocial.activerecord.backend.impl.mysql introspect triggers \
  --database mydb --user root

# 查询特定表的触发器
python -m rhosocial.activerecord.backend.impl.mysql introspect triggers users \
  --database mydb --user root
```

### 内省类型

| 类型 | 说明 | 名称参数 |
|------|------|---------|
| `tables` | 列出所有表 | 不接受 |
| `views` | 列出所有视图，或描述单个视图 | 可选（视图名） |
| `database` | 数据库信息 | 不接受 |
| `columns` | 列信息 | 必填（表名） |
| `indexes` | 索引信息 | 必填（表名） |
| `foreign-keys` | 外键信息 | 必填（表名） |
| `triggers` | 触发器信息 | 可选（表名） |
| `table-options` | 单表的引擎、行格式、排序规则与字节数 | 可选（表名） |
| `partitions` | 单表的分区 | 必填（表名） |
| `unused-indexes` | 无访问记录的索引 | 不接受 |
| `table-stats` | 每表 I/O 计数器 | 不接受 |
| `runtime` | 实时运行事实 | 不接受 |
| `index-stats` | 每索引使用计数器 | 不接受 |
| `dependencies` | 外键依赖边 | 可选（表名） |
| `ddl` | 单表由引擎自身给出的 DDL | 必填（表名） |
| `column-profiles` | 表的每一列里装了什么 | 必填（表名） |
| `value-samples` | 单列最频繁的取值 | 必填（表名） |
| `join-coverage` | 两列取值域的重叠 | 不接受 |

类型不接受名称参数时会报错（退出码 2），而不是静默忽略。

上表新增的九个家族只在"问题关于单个对象"时才接受 NAME。`dependencies` 把答案收窄到一张表的被依赖者；`table-stats`、`index-stats`、`runtime` 与 `join-coverage` 回答整个数据库，遇到名称会拒绝（退出码 2），而不是打印一份未收窄的列表。`ddl`、`column-profiles` 与 `value-samples` 需要表名。`value-samples` 还需要 `--column`，`join-coverage` 需要 `--left-table`、`--left-column`、`--right-table` 与 `--right-column`：缺少必需的旗标是不完整的调用（退出码 1），类型不读取的旗标会被拒绝（退出码 2）。`--limit` 只在给出时才转发给 `sample_column_values()`；不给时由内省器自身的默认值回答（`VALUE_SAMPLE_LIMIT`，100），因此这个数字不会写在两个地方。`ddl` 在表格格式下只打印引擎的文本，在供程序解析的格式下打印记录——模式、对象类型、对象名、`native` 与文本。

### 查询运行与数据家族

```bash
# Six operational readings
python -m rhosocial.activerecord.backend.impl.mysql introspect unused-indexes \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect table-stats \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect index-stats \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect runtime \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect dependencies \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect dependencies orders \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect ddl orders \
  --database mydb --user root

# Three data readings
python -m rhosocial.activerecord.backend.impl.mysql introspect column-profiles orders \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect value-samples orders \
  --column status --limit 20 --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect join-coverage \
  --left-table orders --left-column customer_id \
  --right-table customers --right-column id \
  --database mydb --user root
```

### 输出格式

```bash
# 表格格式（默认，需要 rich 库）
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root

# JSON 格式
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root --output json

# CSV 格式
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root --output csv

# TSV 格式
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root --output tsv
```

### 使用异步后端

```bash
# 使用 --async 参数启用异步模式
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root --async
```

### 环境变量配置

可以在环境中设置连接参数，简化命令行调用：

```bash
# 设置环境变量
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=mydb
export MYSQL_USER=root
export MYSQL_PASSWORD=secret

# 直接使用命令
python -m rhosocial.activerecord.backend.impl.mysql introspect tables
```
