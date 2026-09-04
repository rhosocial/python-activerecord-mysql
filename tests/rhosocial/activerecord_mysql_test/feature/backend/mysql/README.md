# mysql

MySQL vendor-specific test subjects (`{vendor}/{subject}` per the cross-backend test taxonomy plan §3.4):
- `partition/` — partitioned-table DML/EXPLAIN, partition operations and strategies
- `spatial/` — spatial types, ST_* expressions and live-server integration

Remaining MySQL-only extensions (FULLTEXT, SET, JSON duality view) live in `../extensions/`.
