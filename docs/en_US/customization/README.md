# Customization

## Overview

The MySQL backend provides extension points for customizing SQL generation, type handling, and data conversion.

## Contents

- [Custom Expressions](custom_expressions.md): Creating new expression classes for MySQL-specific SQL
- [Custom Data Types](custom_types.md): Defining new DataType subclasses for custom column types
- [Custom Type Adapters](custom_adapters.md): Registering custom converters between Python and MySQL

## Quick Reference

### Custom Expressions

Extend the expression system to add MySQL-specific SQL syntax:

```python
from rhosocial.activerecord.backend.expression.base import BaseExpression

class MySQLOpenTableExpression(BaseExpression):
    def to_sql(self, dialect):
        return "OPEN TABLE ..."
```

### Custom Data Types

Add support for new Python types in MySQL columns:

```python
from rhosocial.activerecord.backend.impl.mysql.types import MySQLDataType

@MySQLDataType.handles(MyClass)
class MyClassAdapter:
    @staticmethod
    def to_sql(value, dialect):
        return json.dumps(value.__dict__)

    @staticmethod
    def from_sql(value, dialect):
        return MyClass(**json.loads(value))
```

### Custom Type Adapters

Register custom type converters:

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

backend = MySQLBackend(...)
backend.type_registry.register(MyClass, MyAdapter)
```

## See Also

- [Core Customization Guide](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/template/customization) -- general customization patterns
- [MySQL Field Types](../backend_specific_features/field_types.md) -- MySQL-specific data types

AI Prompt: "How do I add a custom expression class for MySQL-specific SQL syntax?"
