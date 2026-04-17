# tests/rhosocial/activerecord_mysql_test/feature/backend/test_json_expressions.py
"""
Tests for MySQL JSON expression classes.

This module tests the following expression classes:
- JSONExtractExpression
- JSONObjectExpression
- JSONArrayExpression
- JSONContainsExpression
"""
import pytest
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    JSONExtractExpression,
    JSONObjectExpression,
    JSONArrayExpression,
    JSONContainsExpression,
)


class TestJSONExtractExpression:
    """Test JSONExtractExpression class."""

    def test_json_extract_basic(self):
        """Test basic JSON extraction."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = JSONExtractExpression(dialect, 'data', '$.name')
        sql, params = expr.to_sql()
        
        assert 'JSON_EXTRACT' in sql
        assert 'data' in sql
        assert '$.name' in params
    
    def test_json_extract_with_alias(self):
        """Test JSON extraction with alias."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = JSONExtractExpression(dialect, 'data', '$.name').as_('extracted_name')
        sql, params = expr.to_sql()
        
        assert 'JSON_EXTRACT' in sql
        assert 'AS `extracted_name`' in sql
    
    def test_json_extract_array_path(self):
        """Test JSON extraction with array path."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = JSONExtractExpression(dialect, 'data', '$[0]')
        sql, params = expr.to_sql()
        
        assert 'JSON_EXTRACT' in sql
        assert '$[0]' in params


class TestJSONObjectExpression:
    """Test JSONObjectExpression class."""

    def test_json_object_basic(self):
        """Test basic JSON object creation."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = JSONObjectExpression(dialect, data={'name': 'John', 'age': 30})
        sql, params = expr.to_sql()
        
        assert 'JSON_OBJECT' in sql
        assert 'name' in params
        assert 'age' in params
    
    def test_json_object_with_kwargs(self):
        """Test JSON object creation with keyword arguments."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = JSONObjectExpression(dialect, name='John', age=30).as_('obj')
        sql, params = expr.to_sql()
        
        assert 'JSON_OBJECT' in sql
        assert 'AS `obj`' in sql


class TestJSONArrayExpression:
    """Test JSONArrayExpression class."""

    def test_json_array_basic(self):
        """Test basic JSON array creation."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = JSONArrayExpression(dialect, values=[1, 2, 3])
        sql, params = expr.to_sql()
        
        assert 'JSON_ARRAY' in sql
        assert params[0] == 1
    
    def test_json_array_with_args(self):
        """Test JSON array with positional arguments."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = JSONArrayExpression(dialect, 1, 2, 3)
        sql, params = expr.to_sql()
        
        assert 'JSON_ARRAY' in sql
        assert len(params) == 3
    
    def test_json_array_with_alias(self):
        """Test JSON array with alias."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = JSONArrayExpression(dialect, ['a', 'b']).as_('arr')
        sql, params = expr.to_sql()
        
        assert 'JSON_ARRAY' in sql
        assert 'AS `arr`' in sql


class TestJSONContainsExpression:
    """Test JSONContainsExpression class."""

    def test_json_contains_basic(self):
        """Test basic JSON contains check."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = JSONContainsExpression(dialect, 'data', 'John', '$.name')
        sql, params = expr.to_sql()
        
        assert 'JSON_CONTAINS' in sql
        assert 'data' in sql
        assert 'John' in params
    
    def test_json_contains_with_alias(self):
        """Test JSON contains with alias."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = JSONContainsExpression(dialect, 'data', 'value', '$.key').as_('contains')
        sql, params = expr.to_sql()
        
        assert 'JSON_CONTAINS' in sql
        assert 'AS `contains`' in sql