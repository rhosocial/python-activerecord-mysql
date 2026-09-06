# Custom Type Adapters

## Overview

Type adapters convert between Python values and MySQL database values. The MySQL backend provides a type registry for registering custom adapters.

## Type Registry

The type registry manages all type conversions:

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

backend = MySQLBackend(...)
registry = backend.type_registry
```

## Registering Custom Adapters

### Using the @handles Decorator

```python
from rhosocial.activerecord.backend.impl.mysql.types import MySQLDataType

@MySQLDataType.handles(MyClass)
class MyClassAdapter:
    @staticmethod
    def to_sql(value, dialect):
        """Convert Python MyClass to MySQL value."""
        return json.dumps(value.__dict__)

    @staticmethod
    def from_sql(value, dialect):
        """Convert MySQL value to Python MyClass."""
        return MyClass(**json.loads(value))
```

### Manual Registration

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

class MyAdapter:
    @staticmethod
    def to_sql(value, dialect):
        return str(value)

    @staticmethod
    def from_sql(value, dialect):
        return MyClass(value)

backend = MySQLBackend(...)
backend.type_registry.register(MyClass, MyAdapter)
```

## SQLTypeAdapter Protocol

Custom adapters must implement the `SQLTypeAdapter` protocol:

```python
class SQLTypeAdapter(Protocol):
    @staticmethod
    def to_sql(value: Any, dialect: Any) -> Any:
        """Convert Python value to SQL value."""
        ...

    @staticmethod
    def from_sql(value: Any, dialect: Any) -> Any:
        """Convert SQL value to Python value."""
        ...
```

## BaseSQLTypeAdapter

For common patterns, extend `BaseSQLTypeAdapter`:

```python
from rhosocial.activerecord.backend.adapters import BaseSQLTypeAdapter

class DateAdapter(BaseSQLTypeAdapter):
    @staticmethod
    def to_sql(value, dialect):
        if value is None:
            return None
        return value.isoformat()

    @staticmethod
    def from_sql(value, dialect):
        if value is None:
            return None
        return date.fromisoformat(value)
```

## Type Conversion Flow

```
Python Value
    │
    ▼
to_sql(value, dialect)
    │
    ▼
MySQL Database Value
    │
    ▼
from_sql(value, dialect)
    │
    ▼
Python Value
```

## See Also

- [Type Mapping](../type_adapters/mapping.md) — MySQL to Python type conversion table
- [Custom Type Adapters](../type_adapters/custom.md) — extending type support
- [Core Custom Adapters Guide](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/template/customization/custom_adapters.md) — general customization patterns

💡 *AI Prompt:* "How do I register a custom type adapter for MySQL?"
