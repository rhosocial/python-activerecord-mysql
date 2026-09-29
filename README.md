# rhosocial-activerecord-mysql ($\rho_{\mathbf{AR}\text{-mysql}}$)

[![PyPI version](https://badge.fury.io/py/rhosocial-activerecord-mysql.svg)](https://badge.fury.io/py/rhosocial-activerecord-mysql)
[![Python](https://img.shields.io/pypi/pyversions/rhosocial-activerecord-mysql.svg)](https://pypi.org/project/rhosocial-activerecord-mysql/)
[![Tests](https://github.com/rhosocial/python-activerecord-mysql/actions/workflows/test.yml/badge.svg)](https://github.com/rhosocial/python-activerecord-mysql/actions)
[![Coverage Status](https://codecov.io/gh/rhosocial/python-activerecord-mysql/branch/main/graph/badge.svg)](https://app.codecov.io/gh/rhosocial/python-activerecord-mysql/tree/main)
[![Apache 2.0 License](https://img.shields.io/github/license/rhosocial/python-activerecord-mysql.svg)](https://github.com/rhosocial/python-activerecord-mysql/blob/main/LICENSE)

<div align="center">
    <img src="https://raw.githubusercontent.com/rhosocial/python-activerecord/main/docs/images/logo.svg" alt="rhosocial ActiveRecord Logo" width="200"/>
    <h3>MySQL Backend for rhosocial-activerecord</h3>
    <p><b>Full-text search · JSON functions · DDL expressions · Sync &amp; async</b></p>
</div>

This is a backend implementation for [rhosocial-activerecord](https://github.com/rhosocial/python-activerecord).
It cannot be used standalone.

## Requirements

- **Python**: `>=3.8`
- **Core**: `rhosocial-activerecord>=1.0.0.dev0,<2.0.0`
- **Driver**: `mysql-connector-python>=9.0.0`
- **CI-tested server versions**: 5.6, 5.7, 8.0, 8.4, 9.0, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7

> MySQL 5.6 and 5.7 are exercised with a narrowed test schema, because their
> default `innodb_large_prefix` rejects `VARCHAR(255)` UNIQUE/INDEX columns
> (255 × 4 = 1020 bytes, over the 767-byte cap). See the CI matrix in
> `.github/workflows/test.yml`.

## Installation

```bash
pip install rhosocial-activerecord-mysql
```

## Quick Start

```python
from typing import ClassVar, Optional

from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.backend.expression import CreateTableExpression
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    __table_name__ = "users"

    id: Optional[int] = None
    name: str
    email: str
    age: int = 0

    # Required: without this, `User.c.age` does not exist.
    c: ClassVar[FieldProxy] = FieldProxy()


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

# DDL is expressed, not stringified. Note that every node takes the dialect as
# its first argument, and column types are DataType instances, not strings.
dialect = User.__backend__.dialect
create_users = CreateTableExpression(
    dialect,
    "users",
    columns=[
        ColumnDefinition(
            dialect, "id", IntegerType(dialect),
            constraints=[
                ColumnConstraint(
                    dialect,
                    ColumnConstraintType.PRIMARY_KEY,
                    is_auto_increment=True,
                )
            ],
        ),
        ColumnDefinition(dialect, "name", VarCharType(dialect, 100)),
        ColumnDefinition(dialect, "email", VarCharType(dialect, 255)),
        ColumnDefinition(dialect, "age", IntegerType(dialect)),
    ],
)
# execute() takes SQL text, not an expression node: render it first.
# CREATE TABLE `users` (`id` INT PRIMARY KEY AUTO_INCREMENT,
#   `name` VARCHAR(100), `email` VARCHAR(255), `age` INT)
User.__backend__.execute(*create_users.to_sql())

user = User(name="Alice", email="alice@example.com", age=30)
user.save()

adults = User.query().where(User.c.age >= 18).all()

# Inspect the generated SQL without executing it. MySQL placeholders are
# pyformat, so a literal `%` in a value must be escaped as `%%` by the driver.
sql, params = User.query().where(User.c.age >= 18).to_sql()
```

### Async

The same API surface is available on `AsyncActiveRecord` with
`AsyncMySQLBackend`. Method names are identical; add `await`.

```python
from rhosocial.activerecord.backend.impl.mysql.backend import AsyncMySQLBackend
from rhosocial.activerecord.model import AsyncActiveRecord


class User(AsyncActiveRecord):
    ...  # same fields, plus c: ClassVar[FieldProxy] = FieldProxy()


User.configure(config, AsyncMySQLBackend)
adults = await User.query().where(User.c.age >= 18).all()
```

## MySQL-Specific Features

### Full-text search

```python
Article.query().where(
    "MATCH(title, content) AGAINST(? IN BOOLEAN MODE)",
    ("+python -java",),
).all()
```

### JSON operators

The backend renders `->` and `->>` natively on MySQL 8.0+.

```python
User.query().where("settings->>'$.theme' = ?", ("dark",)).all()
Product.query().where("JSON_CONTAINS(tags, ?)", ('"featured"',)).all()
```

## Version Gates

<!-- Generated by tools/gen_backend_matrix.py; do not edit by hand. -->

_reported above from `supports_*` switches probed at 5.6, 5.7, 8.0, 8.4, 9.0, 9.7._

Switches already `True` at the oldest probe carry no gate and are omitted.
Switches `False` at every probe are not supported by this backend.

| Capability | Min version |
|---|---|
| `fulltext_search` | 5.7 |
| `json_type` | 8 |
| `window_functions` | 8 |
| `lateral_join` | 8 |
| `json_table` | 8.4 |
| `check_constraint` | 8.4 |
| `functional_index` | 8.4 |
| `invisible_index` | 8.4 |
| `window_frame_clause` | 8.4 |
| `vector_type` | 9 |
| `vector_index` | 9.7 |

For the full switch list, including capabilities that are `False` at every
version, see `.claude/mysql_backend.md` and the dialect source.

## Known Limitations

- **No connection pooling.** `MySQLConnectionConfig` accepts `pool_size`,
  `pool_timeout`, `pool_name` and friends, but the backend does not consume
  them: `connect()` opens one persistent connection per backend instance.
  See [connection management](docs/en_US/installation_and_configuration/pool.md).
- **No `RETURNING` clause.** `supports_returning_*` are `False` at every
  MySQL version. Fetch the generated id with a follow-up `SELECT`.
- Generated columns, `SET`, `ENUM`, spatial types and storage-engine options
  need backend-specific DDL expressions rather than plain column types.

## Testing

Tests require a reachable MySQL server and must run serially.

```bash
export PYTHONPATH=src:tests
.venv3.14-ubuntu26.04/bin/pytest tests/
```

The shared contract suite lives in
[python-activerecord-testsuite](https://github.com/rhosocial/python-activerecord-testsuite):

```bash
PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/pytest \
  ../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/
```

## Documentation

- **[Getting started](docs/en_US/installation_and_configuration/)** — installation, connection configuration, SSL, character set
- **[MySQL features](docs/en_US/mysql_specific_features/)** — field types, dialect expressions, storage engines, indexing
- **[Type adapters](docs/en_US/type_adapters/)** — MySQL ↔ Python type mapping, custom adapters, timezones
- **[Transactions](docs/en_US/transaction_support/)** — isolation levels, savepoints, deadlock retry
- **[Troubleshooting](docs/en_US/troubleshooting/)** — connection, performance and character-set issues

## Contributing

See [CONTRIBUTING.md](https://github.com/rhosocial/python-activerecord/blob/main/CONTRIBUTING.md).

## License

[Apache License 2.0](LICENSE) — Copyright © 2026 [vistart](https://github.com/vistart)
