# src/rhosocial/activerecord/backend/impl/mysql/backend/__init__.py
"""Mysql backend implementations.

Every backend keeps both classes in this package: the sync class in
``backend.py`` and the async class in ``async_backend.py``. So the sync class
is at ``impl.mysql.backend.backend`` and the async class at
``impl.mysql.backend.async_backend``.
"""

from .backend import MySQLBackend
