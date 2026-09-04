# dialect tests

MySQL dialect behavior: identifier/expression formatting against a real server, SQLFunctionSupport protocol and version-dependent availability, SQL-injection security fixes (escaping, JSON_TABLE validation, comment escaping), MySQL 9.7 negative feature gates, optimizer hint execution, protocol conformance / non-overlap, and SchemaSupport semantics.

## Key files

- `test_dialect_formatting.py` — dialect formatting on a live server (sync/async)
- `test_dialect_function_support.py` — supports_functions() and version gates
- `test_dialect_security.py` — escaping and validation security fixes
- `test_mysql97_feature_gates.py` — older versions reject 9.7-only features
- `test_optimizer_hint_execution.py` — hint syntax execution incl. hypergraph optimizer
- `test_protocol_conformance.py` — protocol conformance, non-overlap, mixin coverage
- `test_schema_support.py` — SchemaSupport capability semantics
