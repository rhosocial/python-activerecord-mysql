# Transaction Support

This section covers MySQL transaction support, isolation levels, savepoints, and deadlock handling.

## Contents

- [Transaction Isolation Levels](isolation_level.md): READ COMMITTED, REPEATABLE READ, SERIALIZABLE
- [Savepoint Support](savepoint.md): Nested transactions and conditional rollback
- [Deadlock Handling](deadlock.md): Auto-detection, error codes, and retry strategies

## Overview

MySQL provides full transaction support through InnoDB. The transaction manager API follows the core library interface:

```python
# Synchronous
with User.transaction():
    user = User.find_one(1)
    user.name = "updated"
    user.save()

# Asynchronous
async with AsyncUser.transaction():
    user = await AsyncUser.find_one(1)
    user.name = "updated"
    await user.save()
```

The transaction context manager handles BEGIN, COMMIT, and ROLLBACK automatically. If an exception propagates out of the block, the transaction is rolled back.

## Isolation Levels

MySQL defaults to REPEATABLE READ (unlike SQL standard's READ COMMITTED). The backend supports all standard isolation levels:

| Level | MySQL Behavior |
|-------|---------------|
| READ UNCOMMITTED | Dirty reads possible |
| READ COMMITTED | Non-repeatable reads possible |
| REPEATABLE READ | Default; gap locking prevents phantom reads |
| SERIALIZABLE | Strictest; all reads acquire shared locks |

## Savepoints

MySQL supports savepoints within transactions, enabling nested rollback patterns:

```python
with Order.transaction():
    order = Order.find_one(1)
    order.status = "processing"
    order.save()

    # Nested savepoint -- rollback only this portion on error
    with Order.savepoint():
        detail = OrderDetail(order_id=order.id, item="widget", qty=5)
        detail.save()
        # If this raises, only the savepoint is rolled back
```

## Deadlock Handling

InnoDB has built-in deadlock detection. When a deadlock occurs, MySQL automatically rolls back the transaction with lower cost and raises error 1213. The recommended production pattern is to catch and retry:

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

See [Deadlock Handling](deadlock.md) for detailed prevention strategies and five design principles.

AI Prompt: "What causes deadlocks in MySQL and how can I prevent them?"
