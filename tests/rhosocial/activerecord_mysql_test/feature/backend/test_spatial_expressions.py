# tests/rhosocial/activerecord_mysql_test/feature/backend/test_spatial_expressions.py
"""
Tests for MySQL spatial expression classes.

This module tests the following expression classes:
- STGeomFromTextExpression
- STDistanceExpression
- STWithinExpression
- STContainsExpression
"""
import pytest
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    STGeomFromTextExpression,
    STDistanceExpression,
    STWithinExpression,
    STContainsExpression,
)


class TestSTGeomFromTextExpression:
    """Test STGeomFromTextExpression class."""

    def test_st_geom_from_text_basic(self):
        """Test basic geometry from text."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = STGeomFromTextExpression(dialect, 'POINT(1 1)')
        sql, params = expr.to_sql()
        
        assert 'ST_GeomFromText' in sql
        assert 'POINT(1 1)' in params
    
    def test_st_geom_from_text_with_alias(self):
        """Test geometry from text with alias."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = STGeomFromTextExpression(dialect, 'POINT(1 1)').as_('pt')
        sql, params = expr.to_sql()
        
        assert 'ST_GeomFromText' in sql
        assert 'AS `pt`' in sql
    
    def test_st_geom_from_text_linestring(self):
        """Test geometry from text with linestring."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = STGeomFromTextExpression(dialect, 'LINESTRING(0 0, 1 1, 2 2)')
        sql, params = expr.to_sql()
        
        assert 'ST_GeomFromText' in sql
        assert 'LINESTRING' in params[0]


class TestSTDistanceExpression:
    """Test STDistanceExpression class."""

    def test_st_distance_basic(self):
        """Test basic distance calculation."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = STDistanceExpression(dialect, 'pt1', 'pt2')
        sql, params = expr.to_sql()
        
        assert 'ST_Distance' in sql
        assert 'pt1' in sql
        assert 'pt2' in sql
    
    def test_st_distance_with_alias(self):
        """Test distance with alias."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = STDistanceExpression(dialect, 'pt1', 'pt2').as_('dist')
        sql, params = expr.to_sql()
        
        assert 'ST_Distance' in sql
        assert 'AS `dist`' in sql


class TestSTWithinExpression:
    """Test STWithinExpression class."""

    def test_st_within_basic(self):
        """Test basic within check."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = STWithinExpression(dialect, 'geom1', 'geom2')
        sql, params = expr.to_sql()
        
        assert 'ST_Within' in sql
        assert 'geom1' in sql
        assert 'geom2' in sql
    
    def test_st_within_with_alias(self):
        """Test within with alias."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = STWithinExpression(dialect, 'geom1', 'geom2').as_('within')
        sql, params = expr.to_sql()
        
        assert 'ST_Within' in sql
        assert 'AS `within`' in sql


class TestSTContainsExpression:
    """Test STContainsExpression class."""

    def test_st_contains_basic(self):
        """Test basic contains check."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = STContainsExpression(dialect, 'geom1', 'geom2')
        sql, params = expr.to_sql()
        
        assert 'ST_Contains' in sql
        assert 'geom1' in sql
        assert 'geom2' in sql
    
    def test_st_contains_with_alias(self):
        """Test contains with alias."""
        dialect = MySQLDialect(version=(8, 0, 0))
        
        expr = STContainsExpression(dialect, 'geom1', 'geom2').as_('contains')
        sql, params = expr.to_sql()
        
        assert 'ST_Contains' in sql
        assert 'AS `contains`' in sql