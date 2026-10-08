# src/rhosocial/activerecord/backend/impl/mysql/mixins/routine.py
from typing import TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.expression.objects import RoutineObject

from .object_kind import require_kind

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mysql.expression.routine import (
        MySQLCallExpression,
        MySQLCreateProcedureExpression,
        MySQLDropProcedureExpression,
        MySQLCreateFunctionExpression,
        MySQLDropFunctionExpression,
    )


class MySQLRoutineMixin:
    """MySQL stored routine (procedure / function / CALL) support."""

    def _format_param(self, param) -> str:
        """Format a stored-routine parameter definition.

        A param may be a plain string (``IN name TYPE``), a tuple
        ``(mode, name, type)``, or ``(name, type)``.
        """
        if isinstance(param, tuple):
            if len(param) == 3:
                mode, name, type_sql = param
                return f"{mode} {self.format_identifier(name)} {type_sql}"
            if len(param) == 2:
                name, type_sql = param
                return f"{self.format_identifier(name)} {type_sql}"
            raise ValueError(f"Invalid parameter definition: {param!r}")
        return str(param)

    def supports_procedure(self) -> bool:
        return True

    def supports_stored_function(self) -> bool:
        return True

    def supports_call(self) -> bool:
        return True

    def format_create_procedure_statement(
        self,
        expr: "MySQLCreateProcedureExpression",
    ) -> Tuple[str, tuple]:
        """Format ``CREATE PROCEDURE name(params) body``.

        Raises:
            TypeError: ``expr.name`` is not a routine object. The check is here
                rather than only in ``expr.validate`` because that runs under
                ``strict_validation`` and can be switched off; a name of the
                wrong kind must not depend on a rendering strictness flag.
        """
        require_kind(expr.name, RoutineObject, "MySQLCreateProcedureExpression.name")
        expr.validate(strict=self.strict_validation)
        parts = ["CREATE PROCEDURE", expr.name.to_sql()[0]]
        params = ", ".join(self._format_param(p) for p in expr.params)
        parts.append(f"({params})")
        if expr.body:
            parts.append(expr.body)
        return " ".join(parts), ()

    def format_drop_procedure_statement(
        self,
        expr: "MySQLDropProcedureExpression",
    ) -> Tuple[str, tuple]:
        """Format ``DROP PROCEDURE [IF EXISTS] name``.

        Raises:
            TypeError: ``expr.name`` is not a routine object.
        """
        require_kind(expr.name, RoutineObject, "MySQLDropProcedureExpression.name")
        expr.validate(strict=self.strict_validation)
        parts = ["DROP PROCEDURE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(expr.name.to_sql()[0])
        return " ".join(parts), ()

    def format_create_function_statement(
        self,
        expr: "MySQLCreateFunctionExpression",
    ) -> Tuple[str, tuple]:
        """Format ``CREATE FUNCTION name(params) RETURNS type body``.

        Raises:
            TypeError: ``expr.name`` is not a routine object.
        """
        require_kind(expr.name, RoutineObject, "MySQLCreateFunctionExpression.name")
        expr.validate(strict=self.strict_validation)
        parts = ["CREATE FUNCTION", expr.name.to_sql()[0]]
        params = ", ".join(self._format_param(p) for p in expr.params)
        parts.append(f"({params})")
        parts.append(f"RETURNS {expr.returns}")
        if expr.deterministic:
            parts.append("DETERMINISTIC")
        if expr.body:
            parts.append(expr.body)
        return " ".join(parts), ()

    def format_drop_function_statement(
        self,
        expr: "MySQLDropFunctionExpression",
    ) -> Tuple[str, tuple]:
        """Format ``DROP FUNCTION [IF EXISTS] name`` (stored function).

        The loadable UDF form ``DROP FUNCTION name`` is syntactically
        identical and shares this method.

        Raises:
            TypeError: ``expr.name`` is not a routine object.
        """
        require_kind(expr.name, RoutineObject, "MySQLDropFunctionExpression.name")
        expr.validate(strict=self.strict_validation)
        parts = ["DROP FUNCTION"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(expr.name.to_sql()[0])
        return " ".join(parts), ()

    def format_call_statement(self, expr: "MySQLCallExpression") -> Tuple[str, tuple]:
        """Format ``CALL name([args])``.

        Raises:
            TypeError: ``expr.name`` is not a routine object.
        """
        require_kind(expr.name, RoutineObject, "MySQLCallExpression.name")
        expr.validate(strict=self.strict_validation)
        params = []
        arg_parts = []
        for arg in expr.args:
            if hasattr(arg, "to_sql"):
                sql, p = arg.to_sql()
                arg_parts.append(sql)
                params.extend(p)
            elif arg is None:
                arg_parts.append("NULL")
            else:
                arg_parts.append(self.get_parameter_placeholder())
                params.append(arg)
        call_name = expr.name.to_sql()[0]
        parts = ["CALL", call_name, f"({', '.join(arg_parts)})"]
        return " ".join(parts), tuple(params)