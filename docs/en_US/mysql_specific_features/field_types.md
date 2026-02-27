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

```python
from enum import Enum


class Status(str, Enum):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'


class Post(UUIDMixin, ActiveRecord):
    title: str
    status: Status  # ENUM('draft', 'published', 'archived')
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

💡 *AI Prompt:* "What is the difference between VARCHAR and TEXT? When should I use each?"
