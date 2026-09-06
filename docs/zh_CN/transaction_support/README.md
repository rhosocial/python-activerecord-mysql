# 事务支持

本节介绍 MySQL 事务支持、隔离级别、保存点和死锁处理。

## 内容

- [事务隔离级别](isolation_level.md)：READ COMMITTED、REPEATABLE READ、SERIALIZABLE
- [保存点支持](savepoint.md)：嵌套事务和条件回滚
- [死锁处理](deadlock.md)：自动检测、错误代码和重试策略

## 概述

MySQL 通过 InnoDB 提供完整的事务支持。事务管理器 API 遵循核心库接口：

```python
# 同步
with User.transaction():
    user = User.find_one(1)
    user.name = "updated"
    user.save()

# 异步
async with AsyncUser.transaction():
    user = await AsyncUser.find_one(1)
    user.name = "updated"
    await user.save()
```

事务上下文管理器自动处理 BEGIN、COMMIT 和 ROLLBACK。如果异常从块中传播出来，事务将被回滚。

## 隔离级别

MySQL 默认为 REPEATABLE READ（不同于 SQL 标准的 READ COMMITTED）。后端支持所有标准隔离级别：

| 级别 | MySQL 行为 |
|------|-----------|
| READ UNCOMMITTED | 可能发生脏读 |
| READ COMMITTED | 可能发生不可重复读 |
| REPEATABLE READ | 默认；间隙锁防止幻读 |
| SERIALIZABLE | 最严格；所有读取都获取共享锁 |

## 保存点

MySQL 支持事务内的保存点，实现嵌套回滚模式：

```python
with Order.transaction():
    order = Order.find_one(1)
    order.status = "processing"
    order.save()

    # 嵌套保存点 -- 出错时仅回滚此部分
    with Order.savepoint():
        detail = OrderDetail(order_id=order.id, item="widget", qty=5)
        detail.save()
        # 如果这里抛出异常，只有保存点被回滚
```

## 死锁处理

InnoDB 具有内置的死锁检测功能。当发生死锁时，MySQL 自动回滚开销较低的事务并抛出错误 1213。建议的生产模式是捕获并重试：

```python
import time

def claim_posts(batch_size=5, max_retry=3):
    for attempt in range(max_retry):
        try:
            with Post.transaction():
                pending = Post.query().where(Post.c.status == "draft").limit(batch_size).all()
                for post in pending:
                    post.status = "processing"
                    post.save()
                return pending
        except Exception as e:
            if "1213" in str(e) and attempt < max_retry - 1:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise
    return []
```

详细的预防策略和五个设计原则请参阅[死锁处理](deadlock.md)。

AI 提示: "MySQL 中死锁的原因是什么？如何预防？"
