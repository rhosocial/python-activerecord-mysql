# named_connection tests

Named connection support: NamedConnectionResolver unit and integration tests with the MySQL backend and CLI parameter-resolution priority; example connections load from tests/config/mysql_scenarios.yaml.

## Key files

- `example_connections.py` — scenario-based example connections
- `test_named_connection_cli.py` — CLI connection parameter priority
- `test_resolver.py` — resolver unit + integration tests
