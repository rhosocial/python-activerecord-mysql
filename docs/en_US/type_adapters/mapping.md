# MySQL to Python Type Mapping

## Overview

The MySQL backend is responsible for converting MySQL database data types to Python objects, and converting Python objects back to MySQL-recognized formats.

## Type Mapping Table

### Numeric Types

| MySQL Type | Python Type | Description |
|-----------|-------------|-------------|
| TINYINT | int | 8-bit integer |
| SMALLINT | int | 16-bit integer |
| MEDIUMINT | int | 24-bit integer |
| INT | int | 32-bit integer |
| BIGINT | int | 64-bit integer |
| FLOAT | float | Single-precision floating point |
| DOUBLE | float | Double-precision floating point |
| DECIMAL | Decimal | Exact numeric |

### String Types

| MySQL Type | Python Type | Description |
|-----------|-------------|-------------|
| CHAR | str | Fixed-length string |
| VARCHAR | str | Variable-length string |
| TINYTEXT | str | Up to 255 bytes |
| TEXT | str | Up to 65535 bytes |
| MEDIUMTEXT | str | Up to 16777215 bytes |
| LONGTEXT | str | Up to 4294967295 bytes |
| JSON | dict/list | JSON document (MySQL 5.7+) |

### Date and Time Types

| MySQL Type | Python Type | Description |
|-----------|-------------|-------------|
| DATE | date | Date |
| TIME | time | Time |
| DATETIME | datetime | Date and time |
| TIMESTAMP | datetime | Timestamp |
| YEAR | int | Year |

### Binary Types

| MySQL Type | Python Type | Description |
|-----------|-------------|-------------|
| BINARY | bytes | Fixed-length binary |
| VARBINARY | bytes | Variable-length binary |
| TINYBLOB | bytes | Up to 255 bytes |
| BLOB | bytes | Up to 65535 bytes |
| MEDIUMBLOB | bytes | Up to 16777215 bytes |
| LONGBLOB | bytes | Up to 4294967295 bytes |

### Special Types

| MySQL Type | Python Type | Description |
|-----------|-------------|-------------|
| ENUM | str | Enumeration value |
| SET | str | Set value |
| BIT | int | Bit field |
| BOOLEAN | bool | Boolean value |

## Usage Example

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, DefaultTimestampMixin
from typing import ClassVar
from decimal import Decimal


class Product(UUIDMixin, DefaultTimestampMixin, ActiveRecord):
    name: str
    price: Decimal  # Automatically maps to DECIMAL
    description: str  # Automatically maps to TEXT
    metadata: dict  # Automatically maps to JSON (MySQL 5.7+) or TEXT (MySQL 5.6)
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return 'products'
```

## dict/list Type Handling (MySQL 5.6 vs 5.7+)

The `MySQLJSONAdapter` handles Python `dict` and `list` types. The storage behavior differs significantly between MySQL versions:

| Feature | MySQL 5.6 | MySQL 5.7+ |
|---------|-----------|------------|
| Column type | TEXT | JSON |
| Storage format | JSON string | Binary JSON |
| Validation | None | Automatic |
| JSON functions | Not available | JSON_EXTRACT, JSON_SET, etc. |
| Indexing | Not supported | Via generated columns |
| Max size | 65,535 bytes | 1 GB |
| Query syntax | String comparison | Native JSON operators |

### MySQL 5.6 Behavior

```python
# MySQL 5.6: dict/list stored as TEXT
# No validation, no JSON functions, limited query capabilities

data = {"name": "Tom", "tags": ["admin", "user"]}

# Storage: TEXT column with JSON string
# '{"name": "Tom", "tags": ["admin", "user"]}'

# Query:只能使用字符串比较
User.query().where(User.c.metadata.like('%admin%')).all()
```

### MySQL 5.7+ Behavior

```python
# MySQL 5.7+: dict/list stored as native JSON type
# Automatic validation, full JSON function support

data = {"name": "Tom", "tags": ["admin", "user"]}

# Storage: Binary JSON format (more efficient)
# Automatic validation ensures valid JSON

# Query: Native JSON operators
User.query().where(User.c.metadata['$.name'] == 'Tom').all()
User.query().where(User.c.metadata['$.tags'].contains('admin')).all()
```

### Version Detection

The adapter automatically handles version differences:

```python
from rhosocial.activerecord.backend.impl.mysql.adapters import MySQLJSONAdapter

adapter = MySQLJSONAdapter()

# Both versions produce the same Python result
db_value = adapter.to_database(data, dict)  # JSON string
python_value = adapter.from_database(db_value, dict)  # Python dict
```

💡 *AI Prompt:* "Why is DECIMAL recommended over FLOAT for storing monetary values?"
