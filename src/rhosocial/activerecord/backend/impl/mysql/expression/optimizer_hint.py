# src/rhosocial/activerecord/backend/impl/mysql/expression/optimizer_hint.py
"""MySQL optimizer hint expressions.

Supports per-statement optimizer hints using the /*+ ... */ syntax,
including SET_VAR hints for controlling optimizer switches like
the hypergraph optimizer (MySQL 9.7+).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect.base import SQLDialectBase


class OptimizerHintType(Enum):
    """Types of MySQL optimizer hints."""
    SET_VAR = "SET_VAR"


@dataclass
class SetVarHint:
    """A SET_VAR optimizer hint."""
    variable: str
    value: str


class MySQLOptimizerHintExpression(BaseExpression):
    """Expression for MySQL optimizer hints (/*+ ... */ syntax).

    Usage:
        hint = MySQLOptimizerHintExpression(dialect, [
            SetVarHint("optimizer_switch", "hypergraph_optimizer=on")
        ])
        sql, params = hint.to_sql()
        # => ("/*+ SET_VAR(optimizer_switch='hypergraph_optimizer=on') */", ())
    """

    def __init__(self, dialect: "SQLDialectBase", hints: List[SetVarHint]):
        super().__init__(dialect)
        self.hints = hints

    def to_sql(self):
        return self.dialect.format_optimizer_hint(self)
