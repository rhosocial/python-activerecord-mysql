# src/rhosocial/activerecord/backend/impl/mysql/examples/conftest.py
"""
Example metadata configuration.

This file defines metadata for all examples in this directory.
The inspector reads this file to get title, dialect_protocols, and priority.

MySQL Version Support:
- Minimum: 5.6
- Maximum: 9.6

Version-specific features:
- Window Functions: MySQL 8.0+
- Full-Text Search: MySQL 5.6+ (with FULLTEXT index) / 5.7+ (with ngram parser)
- JSON_TABLE: MySQL 8.0+
- JSON data type: MySQL 5.7+
- Auto increment with negative values: MySQL 8.0+
- CTE (WITH clause): MySQL 8.0+
"""

EXAMPLES_META = {
    'transaction/basic.py': {
        'title': 'Transaction Control',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'transaction/for_update.py': {
        'title': 'FOR UPDATE Row Locking',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
        'note': 'SKIP LOCKED and NOWAIT require MySQL 8.0+',
    },
    'query/cte.py': {
        'title': 'CTE (Common Table Expressions)',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '8.0',
        'max_version': '9.6',
        'note': 'Requires MySQL 8.0+. CTE is not available in earlier versions.',
    },
    'connection/quickstart.py': {
        'title': 'Connect to MySQL and Execute Queries',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'ddl/create_index.py': {
        'title': 'Create Index',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'ddl/alter_table.py': {
        'title': 'Alter Table',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'ddl/drop_table.py': {
        'title': 'DROP TABLE using DropTableExpression',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'ddl/view.py': {
        'title': 'CREATE VIEW',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'insert/batch.py': {
        'title': 'Batch Insert',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'delete/basic.py': {
        'title': 'DELETE using DeleteExpression',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'update/basic.py': {
        'title': 'UPDATE using UpdateExpression',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'query/union.py': {
        'title': 'UNION using SetOperationExpression',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'query/distinct.py': {
        'title': 'SELECT DISTINCT using SelectModifier',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'insert/upsert.py': {
        'title': 'UPSERT (INSERT ON DUPLICATE KEY UPDATE)',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'query/basic.py': {
        'title': 'Basic SELECT Query',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'query/join.py': {
        'title': 'JOIN Query',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'query/aggregate.py': {
        'title': 'Aggregate Query',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'query/subquery.py': {
        'title': 'Subquery',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'query/window.py': {
        'title': 'Window Functions (MySQL 8.0+)',
        'dialect_protocols': ['WindowFunctionSupport'],
        'priority': 10,
        'min_version': '8.0',
        'max_version': '9.6',
        'note': 'Use window_mysql57.py for MySQL 5.6/5.7 equivalent',
    },
    'query/window_mysql57.py': {
        'title': 'Window Functions (MySQL 5.6/5.7)',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '5.7',
        'note': 'Use window.py for MySQL 8.0+ native window functions',
    },
    'query/fulltext.py': {
        'title': 'Full-Text Search',
        'dialect_protocols': ['MySQLFullTextSearchSupport'],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
    'query/json_table.py': {
        'title': 'JSON_TABLE',
        'dialect_protocols': ['JSONTableSupport'],
        'priority': 10,
        'min_version': '8.0',
        'max_version': '9.6',
        'note': 'Requires MySQL 8.0+. For older versions, see types/json_basic.py for JSON extraction alternatives',
    },
    'types/json_basic.py': {
        'title': 'JSON Operations (MySQL 5.7+)',
        'dialect_protocols': ['JSONSupport'],
        'priority': 10,
        'min_version': '5.7',
        'max_version': '9.6',
    },
    'types/json_mysql56.py': {
        'title': 'JSON Operations (MySQL 5.6)',
        'dialect_protocols': [],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '5.6',
    },
    'types/fulltext_search.py': {
        'title': 'Full-Text Search (Index)',
        'dialect_protocols': ['MySQLFullTextSearchSupport'],
        'priority': 10,
        'min_version': '5.6',
        'max_version': '9.6',
    },
}
