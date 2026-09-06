# 支持版本

## MySQL 版本支持

| MySQL 版本 | 支持状态 | 说明 |
|-----------|---------|------|
| 5.6.x | ❌ 已停止支持 | Oracle 已终止支持 |
| 5.7.x | ❌ 已停止支持 | Oracle 已终止支持 |
| 8.0.x | ⚠️ 扩展支持 | 扩展支持将于 2026 年 4 月结束；建议升级至 8.4 LTS |
| 8.4.x | ✅ 推荐 | 当前 LTS 长期支持版本，处于主动支持期 |
| 9.0.x | ✅ 支持 | Innovation 版本，新增 VECTOR 类型支持 |
| 9.6.x | ✅ 支持 | Innovation 版本 |
| 9.7.x | ✅ 支持 | 最新 LTS 长期支持版本，新增 JSON Duality Views |

> **重要提示**：本后端专为 MySQL 数据库设计，方言行为与 MySQL 版本特性紧密耦合。**请勿将本后端用于其他 MySQL 兼容数据库**，包括但不限于 MariaDB、TiDB、CockroachDB、PlanetScale 或其他任何 MySQL 协议兼容的系统。使用非 MySQL 数据库可能导致 SQL 生成错误、行为异常或数据损坏。

⚠️ **注意**：

- MySQL 5.6 和 5.7 已停止支持，不建议使用
- MySQL 8.0 处于扩展支持阶段；新部署建议升级至 8.4 LTS
- 部分功能在不同版本间可能存在细微差异，具体请参阅各功能文档

## Python 版本要求

| Python 版本 | 支持状态 | 说明 |
|------------|---------|------|
| 3.8 | ✅ 支持 | |
| 3.9 | ✅ 支持 | |
| 3.10 | ✅ 支持 | |
| 3.11 | ✅ 支持 | |
| 3.12 | ✅ 支持 | |
| 3.13 | ✅ 支持 | 支持 free-threaded 构建版本 (3.13t) |
| 3.14 | ✅ 支持 | 支持 free-threaded 构建版本 (3.14t) |
| 3.15 | ✅ 已测试 | 预发布版本；支持 free-threaded 构建版本 (3.15t) |

**Free-Threaded Python**：从 Python 3.13 开始，提供免线程（无 GIL）构建版本，如 `python3.13t`、`python3.14t` 等。本后端兼容 free-threaded Python，但部分线程相关特性可能表现不同，详见文档说明。

## 依赖要求

| 依赖包 | 版本要求 | 说明 |
|-------|---------|------|
| rhosocial-activerecord | >=1.0.0 | 核心库 |
| mysql-connector-python | >=8.0.0 | MySQL 驱动（唯一支持）|

⚠️ **重要**：本后端仅支持 mysql-connector-python 驱动，不支持 mysqlclient、PyMySQL 等其他驱动。

💡 *AI 提示：* "MySQL 8.0 的 JSON_TABLE 函数如何使用？"
