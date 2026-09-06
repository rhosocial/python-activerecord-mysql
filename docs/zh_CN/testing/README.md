# 测试

本节介绍 MySQL 后端的测试。

## 内容

- [测试配置](configuration.md)：MySQL 特定的测试设置
- [本地测试](local.md)：基于 Docker 的本地测试环境

## 测试原则

### 同步/异步对等

所有涉及 IO 操作的测试必须为等效场景准备成对的同步和异步测试：

```python
# 同步测试
def test_create_user():
    user = User(name="Alice").create()
    assert user.id is not None

# 异步测试 -- 相同逻辑，异步 API
async def test_async_create_user():
    user = await AsyncUser(name="Alice").create()
    assert user.id is not None
```

### 表达式测试 -- 无 IO

表达式测试不涉及数据库 IO -- 它们只构建 SQL 并验证生成的 SQL：

```python
def test_expression_sql():
    expr = Eq(User.name, "Alice")
    assert expr.to_sql(dialect) == "`name` = %s"
    assert expr.params == ["Alice"]
```

表达式测试不需要异步对应部分。

### ActiveRecord 测试 -- 使用测试套件

ActiveRecord 功能测试（模型 CRUD、关系、查询）使用测试套件：

```bash
cd python-activerecord-mysql
PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/pytest \
    ../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/relation/
```

### 测试类别摘要

| 测试内容 | 方法 | IO？ | 异步？ |
|---------|------|------|--------|
| 表达式类（方言 SQL 生成） | 单元测试，无数据库 | 否 | 否 |
| 类型适配器（类型转换） | 单元测试，无数据库 | 否 | 否 |
| 命名功能（表达式、过程、迁移） | CLI 脚本 | 是 | 支持则为是 |
| ActiveRecord 功能（CRUD、关系、查询） | 测试套件 + provider | 是 | 是 |
| MySQL 特有功能（JSON、空间等） | 项目特定测试 | 是 | 是 |

## MySQL 特定注意事项

### 异步游标清理

在断开连接前未能关闭游标可能导致 `RuntimeError: Set changed size during iteration`。始终确保在异步测试拆解中正确关闭游标。

### 表冲突

测试运行之间不删除表会导致 "table already exists" 错误。在测试设置或夹具中使用 `DROP TABLE IF EXISTS`。

### Provider 实现

Provider 实现指南请参阅[核心测试套件 Provider 指南](provider_guide.md)。

AI 提示: "如何使用 Docker 为 CI 设置 MySQL 测试数据库？"
