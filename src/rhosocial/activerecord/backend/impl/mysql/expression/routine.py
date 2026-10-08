# src/rhosocial/activerecord/backend/impl/mysql/expression/routine.py
"""MySQL stored routine expressions.

MySQL supports:

    CREATE PROCEDURE name ([params]) body
    DROP PROCEDURE [IF EXISTS] name
    CREATE FUNCTION name ([params]) RETURNS type ... (stored function)
    DROP FUNCTION [IF EXISTS] name
    CALL name([args])

Note: ``CREATE FUNCTION ... SONAME 'library.so'`` creates a loadable (UDF)
function and is intentionally NOT represented here because it is an
installation-time administrative action (see admin expressions instead).

Routine names are schema objects (``Procedure`` / ``Function``), so a routine
in a named database is expressible: ``CALL `app`.`do_work`()``. The expression
never renders the name -- the dialect does, through the routine's own
``format_<kind>_object``.
"""

from typing import Any, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import RoutineObject

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MySQLRoutineExpression(BaseExpression):
    """Base class for stored routine DDL / invocation statements.

    Attributes:
        name: The routine, as a
            :class:`~rhosocial.activerecord.backend.expression.objects.RoutineObject`
            (``Procedure`` or ``Function``). An object rather than a string
            because a routine may live in a named database, and a string
            cannot say which one; the expression never renders the name itself.
        params: Parameter definitions list (strings or ``(mode, name, type)`` tuples).
        body: Routine body SQL text (for CREATE statements).
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: "RoutineObject",
        *,
        params: Optional[List[Any]] = None,
        body: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.name: "RoutineObject" = name
        self.params: List[Any] = list(params or [])
        self.body: Optional[str] = body

    def validate(self, strict: bool = True) -> None:
        """Validate the routine name.

        Raises:
            TypeError: ``name`` is not a routine object. The former
                ``(schema, name)`` tuple form is refused rather than unpacked:
                a tuple cannot say which part is the database and which is the
                name, which is the ambiguity a schema object removes.
        """
        if not strict:
            return
        if not isinstance(self.name, RoutineObject):
            raise TypeError(
                f"routine name must be a Procedure or Function object, got "
                f"{type(self.name).__name__}; pass "
                f"Procedure(self.dialect, 'sp', catalog_name='app') to qualify the name"
            )


class MySQLCreateProcedureExpression(MySQLRoutineExpression):
    """Represent ``CREATE PROCEDURE``."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_procedure_statement"



class MySQLDropProcedureExpression(MySQLRoutineExpression):
    """Represent ``DROP PROCEDURE [IF EXISTS]``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: Any,
        *,
        if_exists: bool = False,
    ):
        super().__init__(dialect, name)
        self.if_exists: bool = if_exists

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_procedure_statement"



class MySQLCreateFunctionExpression(MySQLRoutineExpression):
    """Represent ``CREATE FUNCTION`` (stored function)."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: Any,
        *,
        returns: str,
        params: Optional[List[Any]] = None,
        body: Optional[str] = None,
        deterministic: bool = False,
    ):
        super().__init__(
            dialect,
            name,
            params=params,
            body=body,
        )
        self.returns: str = returns
        self.deterministic: bool = deterministic

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_function_statement"



class MySQLDropFunctionExpression(MySQLRoutineExpression):
    """Represent ``DROP FUNCTION [IF EXISTS]`` (stored function)."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: Any,
        *,
        if_exists: bool = False,
    ):
        super().__init__(dialect, name)
        self.if_exists: bool = if_exists

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_function_statement"



class MySQLCallExpression(BaseExpression):
    """Represent ``CALL procedure_name([args])``.

    Attributes:
        name: The procedure, as a
            :class:`~rhosocial.activerecord.backend.expression.objects.Procedure`.
        args: Positional argument list.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: "RoutineObject",
        args: Optional[List[Any]] = None,
    ):
        super().__init__(dialect)
        self.name: "RoutineObject" = name
        self.args: List[Any] = list(args or [])

    def validate(self, strict: bool = True) -> None:
        """Validate the procedure name.

        Raises:
            TypeError: ``name`` is not a routine object. The former
                ``(schema, name)`` tuple form is refused rather than unpacked.
        """
        if not strict:
            return
        if not isinstance(self.name, RoutineObject):
            raise TypeError(
                f"procedure name must be a Procedure or Function object, got "
                f"{type(self.name).__name__}; pass "
                f"Procedure(self.dialect, 'sp', catalog_name='app') to qualify the name"
            )

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_call_statement"
