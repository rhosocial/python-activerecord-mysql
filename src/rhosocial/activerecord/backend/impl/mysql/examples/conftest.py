# src/rhosocial/activerecord/backend/impl/mysql/examples/conftest.py
"""
Example metadata configuration.

This file defines metadata for all examples in this directory.
The inspector reads this file to get title, dialect_protocols, and priority.
"""

EXAMPLES_META = {
    'ddl/create_index.py': {
        'title': 'Create Index',
        'dialect_protocols': [],
        'priority': 10,
    },
    'ddl/alter_table.py': {
        'title': 'Alter Table',
        'dialect_protocols': [],
        'priority': 10,
    },
    'insert/batch.py': {
        'title': 'Batch Insert',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/basic.py': {
        'title': 'Basic SELECT Query',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/join.py': {
        'title': 'JOIN Query',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/aggregate.py': {
        'title': 'Aggregate Query',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/subquery.py': {
        'title': 'Subquery',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/window.py': {
        'title': 'Window Functions',
        'dialect_protocols': ['WindowFunctionSupport'],
        'priority': 10,
    },
    'query/fulltext.py': {
        'title': 'Full-Text Search',
        'dialect_protocols': ['FullTextSearchSupport'],
        'priority': 10,
    },
    'query/json_table.py': {
        'title': 'JSON_TABLE',
        'dialect_protocols': ['JSONTableSupport'],
        'priority': 10,
    },
    'types/json_basic.py': {
        'title': 'JSON Operations',
        'dialect_protocols': ['JSONSupport'],
        'priority': 10,
    },
}
