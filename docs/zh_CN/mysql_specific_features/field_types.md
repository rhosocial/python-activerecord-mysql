# MySQL 特定字段类型

## 概述

MySQL 提供了多种特定字段类型，本节介绍常用的字段类型及其使用场景。

## 数值类型

| 类型 | 范围 | 说明 |
|-----|------|------|
| TINYINT | -128 ~ 127 | 1 字节整数 |
| SMALLINT | -32768 ~ 32767 | 2 字节整数 |
| MEDIUMINT | -8388608 ~ 8388607 | 3 字节整数 |
| INT | -2147483648 ~ 2147483647 | 4 字节整数 |
| BIGINT | -9223372036854775808 ~ 9223372036854775807 | 8 字节整数 |

## 字符串类型

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

### JSON 类型 (MySQL 5.7+)

```python
from typing import Dict, Any


class Config(UUIDMixin, ActiveRecord):
    name: str
    settings: Dict[str, Any]  # JSON 类型
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return 'configs'
```

## SET 和 ENUM

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

💡 *AI 提示词：* "VARCHAR 和 TEXT 有什么区别？何时使用哪个？"
