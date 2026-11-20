<!-- README.md -->
# rhosocial-activerecord-mysql ($\rho_{\mathbf{AR}\text{-mysql}}$)

[![PyPI version](https://badge.fury.io/py/rhosocial-activerecord-mysql.svg)](https://badge.fury.io/py/rhosocial-activerecord-mysql)
[![Python](https://img.shields.io/pypi/pyversions/rhosocial-activerecord-mysql.svg)](https://pypi.org/project/rhosocial-activerecord-mysql/)
[![Tests](https://github.com/rhosocial/python-activerecord-mysql/actions/workflows/test.yml/badge.svg)](https://github.com/rhosocial/python-activerecord-mysql/actions)
[![Coverage Status](https://codecov.io/gh/rhosocial/python-activerecord-mysql/branch/main/graph/badge.svg)](https://app.codecov.io/gh/rhosocial/python-activerecord-mysql/tree/main)
[![Apache 2.0 License](https://img.shields.io/github/license/rhosocial/python-activerecord-mysql.svg)](https://github.com/rhosocial/python-activerecord-mysql/blob/main/LICENSE)
[![Supported MySQL versions](https://img.shields.io/badge/MySQL-5.6%7C5.7%7C8.0%7C8.4%7C9.0%7C9.1%7C9.2%7C9.3%7C9.4%7C9.5%7C9.6%7C9.7%7C26.7-blue?logo=mysql)](docs/en_US/introduction/supported_versions.md)

<div align="center">
    <img src="https://raw.githubusercontent.com/rhosocial/python-activerecord/main/docs/images/logo.svg" alt="rhosocial ActiveRecord Logo" width="200"/>
    <h3>MySQL Backend for rhosocial-activerecord</h3>
    <p><b>Full-text search · JSON functions · DDL expressions · Sync &amp; async</b></p>
</div>

MySQL backend for [rhosocial-activerecord](https://github.com/rhosocial/python-activerecord) — the same standalone ActiveRecord API, backed by MySQL 5.6–26.7 through `mysql-connector-python`.

**Keywords:** mysql, activerecord, orm, pydantic, python, async, type-safe, mysql-connector-python

## Why This Project?

### Bring ActiveRecord to MySQL

A class represents a table; an instance represents a row. Declare a model once and persist it with `save()` — no Session object to manage. This backend binds that model to MySQL, so the same declarative style runs against MySQL 5.6 through 26.7.

### MySQL-native, not a lowest-common-denominator layer

- Full-text search and native JSON operators (`->`, `->>`), rendered by capability version
- Declarative DDL with `.to_sql()` transparency — preview every statement before it runs
- Native sync (`MySQLBackend`) and async (`AsyncMySQLBackend`) with identical method names
- Type-first Pydantic models — `UseSqlType`, mixins, and no `Any` in the public API

Unlike SQLAlchemy's Data Mapper or Django's framework-coupled ORM, this is a standalone ActiveRecord backend you can drop into FastAPI, Flask, or a plain script.

## Quick Start

### Installation

```bash
pip install rhosocial-activerecord-mysql
```

Requires Python 3.8+ (on 3.8, import `Annotated` from `typing_extensions`); the core `rhosocial-activerecord` library is installed as a dependency.

### End-to-End Example

```python
"""Save as demo.py and run against a reachable MySQL server."""
from typing import Annotated, ClassVar

from rhosocial.activerecord.base import FieldProxy, UseSqlType
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.field import DefaultTimestampMixin, IntegerPKMixin
from rhosocial.activerecord.model import ActiveRecord


class User(
    IntegerPKMixin,         # auto-increment integer primary key (`id`)
    DefaultTimestampMixin,  # injects `created_at` / `updated_at` timestamps
    ActiveRecord,           # persistence, query builder, relations
):
    name: Annotated[str, UseSqlType(VarCharType(length=100))]
    email: Annotated[str, UseSqlType(VarCharType(length=255))]
    age: int = 0

    c: ClassVar[FieldProxy] = FieldProxy()  # enables User.c.<field> expressions

    @classmethod
    def table_name(cls) -> str:
        return "users"


User.configure(
    MySQLConnectionConfig(
        host="localhost",
        port=3306,
        database="myapp",
        username="user",
        password="password",
    ),
    MySQLBackend,
)
User.create_table()

alice = User(name="Alice", email="alice@example.com", age=30)
alice.save()
print(alice.id)  # database-assigned AUTO_INCREMENT primary key

adults = User.query().where(User.c.age >= 18).all()
print([user.name for user in adults])

# Inspect the generated SQL without executing it. MySQL uses pyformat
# placeholders, so a literal `%` in a value must be escaped as `%%`.
sql, params = User.query().where(User.c.age >= 18).to_sql()
print(sql, params)
```

> **Async parity:** use `AsyncActiveRecord` with `AsyncMySQLBackend` for the async model — same method names, same patterns, just add `await`.

## Project Architecture

This package is the MySQL dialect and driver adapter layered on the core ActiveRecord library: models and field proxies are declared once, the core builds backend-agnostic statements, and this backend binds them to MySQL SQL and runs them through `mysql-connector-python`.

Start with the [MySQL backend documentation](docs/en_US/README.md) for installation, connection configuration, MySQL-specific field types, DDL, transactions, type adapters, testing, and troubleshooting.

**MySQL-specific highlights.** Full-text search, native JSON operators, storage-engine and indexing support, and schema introspection are first-class. Capabilities are version-gated — JSON needs 8.0, `JSON_TABLE` and CHECK enforcement need 8.4, vector types need 9.0+ — see [Supported Versions](docs/en_US/introduction/supported_versions.md). MySQL 5.6/5.7 run a narrowed test schema because their default `innodb_large_prefix` rejects `VARCHAR(255)` UNIQUE/INDEX columns.

## Backend Support & Progress

This is a separate package built on the core `rhosocial-activerecord` library; it cannot be used standalone. Supported, CI-tested MySQL versions: **5.6, 5.7, 8.0, 8.4, 9.0, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 26.7**. MySQL 8.0+ is recommended for JSON features and 8.4 is the current LTS. Requires Python 3.8+.

> **⚠️ Development Stage:** This project is under active development. APIs may change, and some features are not yet production-ready.

Known limits: connection-pool settings in `MySQLConnectionConfig` are not consumed (`connect()` keeps one persistent connection per backend instance); there is no `RETURNING`, so fetch generated ids with a follow-up `SELECT`; generated columns, `SET`, `ENUM`, spatial types, and storage-engine options need backend-specific DDL. See [connection management](docs/en_US/installation_and_configuration/pool.md).

## Documentation

### Contributing

We welcome contributions! Please see [CONTRIBUTING.md](https://github.com/rhosocial/python-activerecord/blob/main/CONTRIBUTING.md) for guidelines.

### License

[Apache License 2.0](LICENSE) — Copyright © 2026 [vistart](https://github.com/vistart)

### Documentation

* **[MySQL Backend Documentation Home](docs/en_US/README.md)** — the full documentation table of contents
* **[Supported Versions](docs/en_US/introduction/supported_versions.md)** — MySQL, MariaDB, Python, and driver version matrix
* **[Getting Started](docs/en_US/installation_and_configuration/)** — installation, connection configuration, SSL, character set
* **[MySQL Features](docs/en_US/mysql_specific_features/)** — field types, dialect expressions, storage engines, indexing
* **[Type Adapters](docs/en_US/type_adapters/)** — MySQL ↔ Python type mapping, custom adapters, timezones
* **[Transactions](docs/en_US/transaction_support/)** — isolation levels, savepoints, deadlock retry
* **[Troubleshooting](docs/en_US/troubleshooting/)** — connection, performance and character-set issues

---

<div align="center">
    <p><b>Built with ❤️ by the rhosocial team</b></p>
    <p><a href="https://github.com/rhosocial/python-activerecord-mysql">GitHub</a> · <a href="docs/en_US/README.md">Documentation</a> · <a href="https://pypi.org/project/rhosocial-activerecord-mysql/">PyPI</a></p>
</div>
