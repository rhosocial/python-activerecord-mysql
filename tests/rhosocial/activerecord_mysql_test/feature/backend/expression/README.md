# expression tests

MySQL expression classes: functional serialization round trips over every expression class, transaction expressions (SET TRANSACTION before START TRANSACTION), JSON arrow/function expressions, JSON duality view expressions (9.7+), optimizer hints, vector distance expressions, and broad mixin coverage.

## Key files

- `test_expression_roundtrip_all.py` — serialization round trip for all MySQL expressions
- `test_expressions_transaction.py` — BEGIN/SET TRANSACTION/COMMIT/ROLLBACK/SAVEPOINT
- `test_json_arrow_expression.py` — -> / ->> and function-based JSON expressions
- `test_json_duality_view_expressions.py` — JSON duality view DDL/DML expressions
- `test_json_expressions.py` — JSON_EXTRACT / JSON_OBJECT / JSON_ARRAY / JSON_CONTAINS
- `test_mixin_expressions.py` — mixin-level expression coverage incl. guards
- `test_optimizer_hint_expressions.py` — SET_VAR and hypergraph hints
- `test_vector_expressions.py` — vector and distance expressions
