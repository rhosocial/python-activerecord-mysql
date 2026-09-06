# Troubleshooting

This section covers common MySQL backend issues and their solutions.

## Contents

- [Connection Errors](connection.md): Error codes, diagnostics, and automatic recovery
- [Performance Issues](performance.md): Slow query analysis and optimization

## Common Issues

### Connection Refused (2003)

```
Can't connect to MySQL server on 'localhost' (111)
```

Verify the MySQL server is running and listening on the expected port. Check `host`, `port`, and `bind-address` settings.

### Access Denied (1045)

```
Access denied for user 'root'@'localhost' (using password: YES)
```

Verify credentials and that the user has permission to connect from your host. MySQL grants are host-specific -- a user allowed from `localhost` may not be allowed from `127.0.0.1`.

### Too Many Connections (1040)

```
Too many connections
```

MySQL has a `max_connections` limit (default 151). Increase it in `my.cnf` or close idle connections. The connect-on-use model means connections are created per `configure()` call -- ensure you disconnect after use.

### Lost Connection (2013)

```
Lost connection to MySQL server during query
```

This often occurs with large result sets or long-running queries. Increase `net_read_timeout` and `net_write_timeout` in MySQL configuration, or break large operations into smaller batches.

### Character Set Issues

If you see garbled Unicode data or `incorrect string value` errors, ensure both the connection charset and the column charset are set to `utf8mb4`:

```python
config = MySQLConnectionConfig(
    ...,
    charset='utf8mb4',
)
```

Also verify the MySQL server default character set:

```sql
SHOW VARIABLES LIKE 'character_set%';
```

### Deadlock (1213)

```
Deadlock found when trying to get lock; try restarting transaction
```

InnoDB automatically detects deadlocks and rolls back the cheaper transaction. Catch the exception and retry with exponential backoff. See [Deadlock Handling](../transaction_support/deadlock.md) for prevention strategies.

### Performance Tips

- Use `EXPLAIN` to analyze slow queries (see [EXPLAIN](../backend_specific_features/explain.md))
- Add appropriate indexes for WHERE, JOIN, and ORDER BY clauses
- Avoid `SELECT *` -- fetch only needed columns
- Use connection timeouts to prevent hanging connections

AI Prompt: "How do I diagnose a MySQL connection timeout in my application?"
