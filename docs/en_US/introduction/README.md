# Introduction

## MySQL Backend Overview

`rhosocial-activerecord-mysql` is the MySQL database backend implementation for the rhosocial-activerecord core library. It provides complete ActiveRecord pattern support, optimized specifically for MySQL database features.

💡 *AI Prompt:* "What is the ActiveRecord pattern? How does it differ from DataMapper pattern?"

## Synchronous and Asynchronous

The MySQL backend provides both synchronous and asynchronous APIs that are functionally equivalent. The documentation will use synchronous examples throughout, but the asynchronous API usage is identical—just replace method calls with their async equivalents.

For example:

```python
# Synchronous usage
backend = MySQLBackend(...)
backend.connect()
users = backend.find('User')

# Asynchronous usage
backend = AsyncMySQLBackend(...)
await backend.connect()
users = await backend.find('User')
```

## Quick Links

- **[Relationship with Core Library](./relationship.md)**: Learn how the MySQL backend works with the core library
- **[Supported Versions](./supported_versions.md)**: View supported MySQL, Python, and dependency versions

💡 *AI Prompt:* "What are the important new features in MySQL 8.0 compared to 5.7?"
