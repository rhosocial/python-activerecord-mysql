# MySQL 特有功能

本节介绍扩展核心 ActiveRecord 功能的 MySQL 特有功能。

## 内容

- [字段类型](field_types.md)：SET、ENUM、JSON、TEXT 与 VARCHAR
- [方言表达式](dialect.md)：MySQL 特定的 SQL 语法和函数
- [存储引擎](storage_engine.md)：InnoDB、MyISAM 选择
- [索引](indexing.md)：索引类型和优化策略
- [EXPLAIN](explain.md)：查询执行计划分析
- [自省](introspection.md)：数据库元数据查询
- [分区](partition.md)：表分区策略

## 概述

MySQL 提供了其他后端不具备的多种功能。后端通过专用的表达式类和方言扩展利用这些功能。

### 字段类型

MySQL 支持超出 SQL 标准的丰富列类型：

| 类型 | 描述 | 使用场景 |
|------|------|---------|
| ENUM | 允许值的固定集合（字符串） | 状态字段、分类 |
| SET | 允许值的组合 | 多选标志 |
| JSON | 结构化文档存储 | 灵活属性 |
| TEXT 变体 | TINYTEXT、TEXT、MEDIUMTEXT、LONGTEXT | 不同的文本长度需求 |
| 空间类型 | POINT、LINESTRING、POLYGON、GEOMETRY | 地理数据 |

### 存储引擎

MySQL 允许按表选择存储引擎。后端支持通过 DDL 选项指定引擎：

```python
create_table = CreateTableExpression(
    dialect,
    table_name='logs',
    columns=[...],
    dialect_options={'engine': 'InnoDB'}
)
```

InnoDB 是默认且推荐的引擎。MyISAM 可用于读取密集型工作负载，不需要事务保证时可使用。

### 方言表达式

MySQL 提供特定的 SQL 函数和语法扩展。方言层为 JSON 查询、字符串操作和日期算术等操作生成 MySQL 兼容的 SQL。

### 分区

MySQL 支持 RANGE、LIST、HASH 和 KEY 分区策略。后端为每种策略提供专用的表达式类，通过 DDL 操作实现类型安全的分区管理。

AI 提示: "在 MySQL 中何时应该使用 ENUM 而不是查找表？"
