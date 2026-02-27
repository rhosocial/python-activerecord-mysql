# 简介

## MySQL 后端概述

`rhosocial-activerecord-mysql` 是 rhosocial-activerecord 核心库的 MySQL 数据库后端实现。它提供了完整的 ActiveRecord 模式支持，专门针对 MySQL 数据库的特性进行了优化。

💡 *AI 提示词：* "什么是 ActiveRecord 模式？它与 DataMapper 模式有什么区别？"

## 同步与异步

MySQL 后端同时提供同步与异步两套 API，两者在功能上完全对等。本文档后续章节将以同步方式举例说明，异步 API 的使用方式与同步版本一致，只需将方法调用替换为对应的异步版本即可。

例如：

```python
# 同步用法
backend = MySQLBackend(...)
backend.connect()
users = backend.find('User')

# 异步用法
backend = AsyncMySQLBackend(...)
await backend.connect()
users = await backend.find('User')
```

## 快速链接

- **[与核心库的关系](./relationship.md)**：了解 MySQL 后端如何与核心库协同工作
- **[支持版本](./supported_versions.md)**：查看支持的 MySQL、Python 和依赖版本

💡 *AI 提示词：* "MySQL 8.0 相比 5.7 有哪些重要的新特性？"
