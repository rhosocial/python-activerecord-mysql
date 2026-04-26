# tests/rhosocial/activerecord_mysql_test/feature/backend/test_vector_expressions.py
"""
Tests for MySQL vector expression classes.

This module tests the following expression classes:
- MySQLVectorExpression
- MySQLDistanceEuclideanExpression
- MySQLDistanceCosineExpression
- MySQLDistanceDotExpression
"""
import pytest
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLVectorExpression,
    MySQLDistanceEuclideanExpression,
    MySQLDistanceCosineExpression,
    MySQLDistanceDotExpression,
)


class TestMySQLVectorExpression:
    """Test MySQLVectorExpression class."""

    def test_vector_expression_basic(self):
        """Test basic vector literal creation."""
        dialect = MySQLDialect(version=(9, 0, 0))
        
        expr = MySQLVectorExpression(dialect, '[1, 2, 3]')
        sql, params = expr.to_sql()
        
        assert 'STRING_TO_VECTOR' in sql
        assert '[' in params[0] or '1' in params[0]
    
    def test_vector_expression_with_alias(self):
        """Test vector expression with alias."""
        dialect = MySQLDialect(version=(9, 0, 0))
        
        expr = MySQLVectorExpression(dialect, '[1, 2, 3]').as_('embedding')
        sql, params = expr.to_sql()
        
        assert 'STRING_TO_VECTOR' in sql
        assert 'AS `embedding`' in sql
    
    def test_vector_expression_version_check(self):
        """Test vector support requires MySQL 9.0+."""
        dialect_old = MySQLDialect(version=(8, 0, 0))
        dialect_new = MySQLDialect(version=(9, 0, 0))
        
        assert not dialect_old.supports_vector_type()
        assert dialect_new.supports_vector_type()


class TestMySQLDistanceEuclideanExpression:
    """Test MySQLDistanceEuclideanExpression class."""

    def test_distance_euclidean_expression(self):
        """Test Euclidean distance calculation."""
        dialect = MySQLDialect(version=(9, 0, 0))
        
        expr = MySQLDistanceEuclideanExpression(dialect, 'vec1', 'vec2')
        sql, params = expr.to_sql()
        
        assert 'DISTANCE_EUCLIDEAN' in sql
        assert 'vec1' in sql
        assert 'vec2' in sql
    
    def test_distance_euclidean_with_alias(self):
        """Test Euclidean distance with alias."""
        dialect = MySQLDialect(version=(9, 0, 0))
        
        expr = MySQLDistanceEuclideanExpression(dialect, 'vec1', 'vec2').as_('dist')
        sql, params = expr.to_sql()
        
        assert 'DISTANCE_EUCLIDEAN' in sql
        assert 'AS `dist`' in sql


class TestMySQLDistanceCosineExpression:
    """Test MySQLDistanceCosineExpression class."""

    def test_distance_cosine_expression(self):
        """Test Cosine distance calculation."""
        dialect = MySQLDialect(version=(9, 0, 0))
        
        expr = MySQLDistanceCosineExpression(dialect, 'vec1', 'vec2')
        sql, params = expr.to_sql()
        
        assert 'DISTANCE_COSINE' in sql
        assert 'vec1' in sql
        assert 'vec2' in sql
    
    def test_distance_cosine_with_alias(self):
        """Test Cosine distance with alias."""
        dialect = MySQLDialect(version=(9, 0, 0))
        
        expr = MySQLDistanceCosineExpression(dialect, 'vec1', 'vec2').as_('cos_dist')
        sql, params = expr.to_sql()
        
        assert 'DISTANCE_COSINE' in sql
        assert 'AS `cos_dist`' in sql


class TestMySQLDistanceDotExpression:
    """Test MySQLDistanceDotExpression class."""

    def test_distance_dot_expression(self):
        """Test Dot product calculation."""
        dialect = MySQLDialect(version=(9, 0, 0))
        
        expr = MySQLDistanceDotExpression(dialect, 'vec1', 'vec2')
        sql, params = expr.to_sql()
        
        assert 'DISTANCE_DOT' in sql
        assert 'vec1' in sql
        assert 'vec2' in sql
    
    def test_distance_dot_with_alias(self):
        """Test Dot product with alias."""
        dialect = MySQLDialect(version=(9, 0, 0))
        
        expr = MySQLDistanceDotExpression(dialect, 'vec1', 'vec2').as_('dot_prod')
        sql, params = expr.to_sql()
        
        assert 'DISTANCE_DOT' in sql
        assert 'AS `dot_prod`' in sql