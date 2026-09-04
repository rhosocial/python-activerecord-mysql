# functions tests

MySQL function coverage: bitwise functions, datetime interval expressions, JSON functions (protocol detection plus real-database integration), enhanced math functions and the SQL:2003 niladic CURRENT_* forms in SELECT and DDL contexts.

## Key files

- `test_bitwise_functions.py` — BIT_AND / BIT_OR / BIT_XOR / bit shifting
- `test_datetime_interval_expressions.py` — datetime interval expressions
- `test_json_functions.py` — JSON function version detection
- `test_json_functions_backend.py` — JSON functions executed on the server
- `test_math_enhanced_functions.py` — enhanced math functions
- `test_niladic_functions.py` — niladic CURRENT_* in select/DDL contexts
