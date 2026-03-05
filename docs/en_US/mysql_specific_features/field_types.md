# MySQL-Specific Field Types

## Overview

MySQL provides various specific field types. This section covers commonly used field types and their use cases.

## Numeric Types

| Type | Range | Description |
|-----|-------|-------------|
| TINYINT | -128 ~ 127 | 1-byte integer |
| SMALLINT | -32768 ~ 32767 | 2-byte integer |
| MEDIUMINT | -8388608 ~ 8388607 | 3-byte integer |
| INT | -2147483648 ~ 2147483647 | 4-byte integer |
| BIGINT | -9223372036854775808 ~ 9223372036854775807 | 8-byte integer |

## String Types

### VARCHAR vs TEXT

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin
from typing import ClassVar
from pydantic import Field


class Article(UUIDMixin, ActiveRecord):
    title: str = Field(max_length=255)  # VARCHAR(255)
    content: str  # TEXT
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return 'articles'
```

### JSON Type (MySQL 5.7+)

```python
from typing import Dict, Any


class Config(UUIDMixin, ActiveRecord):
    name: str
    settings: Dict[str, Any]  # JSON type
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return 'configs'
```

## SET and ENUM

### ENUM

MySQL ENUM is a string object with a value chosen from a list of permitted values. Internally, MySQL stores ENUM values as integers (1, 2, 3, ...) for compact storage.

#### Basic Usage

```python
from enum import Enum
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import UUIDMixin


class Status(str, Enum):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'


class Post(UUIDMixin, ActiveRecord):
    title: str
    status: Status  # ENUM('draft', 'published', 'archived')

    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

#### Performance Optimization

For better performance, you can use MySQL's internal integer representation:

```python
from rhosocial.activerecord.backend.impl.mysql.adapters import MySQLEnumAdapter

# Configure after backend initialization
backend.adapter_registry.register(
    MySQLEnumAdapter(use_int_storage=True),
    Enum,
    int,
    allow_override=True
)
```

This will:
- Store ENUM values as integers (1, 2, 3...) instead of strings
- Reduce storage from ~N bytes to 1-2 bytes
- Maintain the same logical interface in Python

#### Value Validation

You can validate enum values before sending to database:

```python
adapter = MySQLEnumAdapter()

# Validate against allowed values
adapter.to_database(
    Status.DRAFT, 
    str, 
    {'enum_values': ['draft', 'published']}
)
```

#### Important Notes

1. **Value Validation**: MySQL automatically validates ENUM values
2. **Case Sensitivity**: ENUM values are case-insensitive by default (depends on collation)
3. **Storage**: Uses 1 byte for < 256 values, 2 bytes for 256-65535 values
4. **Sorting**: ENUM values sort by index order, not alphabetically

💡 *AI Prompt:* "What are the performance implications of MySQL ENUM vs VARCHAR?"
