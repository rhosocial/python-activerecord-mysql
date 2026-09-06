# Type Adapters

This section covers type conversion between MySQL data types and Python types.

## Contents

- [Type Mapping](mapping.md): MySQL to Python type conversion table
- [Custom Adapters](custom.md): Extending type support with custom adapters
- [Timezone Handling](timezone.md): Timestamp and timezone configuration

## Overview

The MySQL backend maps MySQL column types to Python types automatically:

| MySQL Type | Python Type | Notes |
|-----------|-------------|-------|
| TINYINT, SMALLINT, MEDIUMINT, INT, BIGINT | int | |
| FLOAT, DOUBLE | float | |
| DECIMAL | Decimal | From `decimal` module |
| CHAR, VARCHAR | str | |
| TEXT, TINYTEXT, MEDIUMTEXT, LONGTEXT | str | |
| BINARY, VARBINARY | bytes | |
| BLOB, TINYBLOB, MEDIUMBLOB, LONGBLOB | bytes | |
| DATE | date | From `datetime` module |
| TIME | time | From `datetime` module |
| DATETIME | datetime | |
| TIMESTAMP | datetime | With timezone conversion |
| YEAR | int | |
| ENUM | str | |
| SET | str | Comma-separated values |
| JSON | dict/list | Parsed from JSON string |

## Custom Adapters

You can register custom type adapters for application-specific types:

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

class MyClass:
    def __init__(self, value):
        self.value = value

class MyClassAdapter:
    @staticmethod
    def to_sql(value, dialect):
        return json.dumps({"value": value.value})

    @staticmethod
    def from_sql(value, dialect):
        data = json.loads(value)
        return MyClass(data["value"])

backend = MySQLBackend(config)
backend.type_registry.register(MyClass, MyClassAdapter)
```

## Timezone Handling

MySQL TIMESTAMP columns store values in UTC and convert to the session timezone on retrieval. The backend handles this conversion automatically. For DATETIME columns (which have no timezone awareness), configure the session timezone explicitly if needed.

See [Timezone Handling](timezone.md) for detailed configuration.

AI Prompt: "How does MySQL handle timezone conversion for TIMESTAMP columns?"
