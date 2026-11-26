# src/rhosocial/activerecord/backend/impl/mysql/mixins/explain.py
"""MySQL EXPLAIN support: four formats, no PostgreSQL-style option words.

MySQL's grammar takes ``EXPLAIN [ANALYZE] [FORMAT=...]`` and nothing else --
``VERBOSE``, ``COSTS``, ``BUFFERS``, ``TIMING``, ``SETTINGS`` and ``WAL`` are
PostgreSQL option words the server does not parse. The per-format switches below
answer which format words this server accepts; the formatter refuses an option
whose switch says no instead of dropping it silently.
"""
from enum import Enum
from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements import ExplainStatement


class MySQLExplainMixin:
    """MySQL EXPLAIN statement support."""

    #: The format words MySQL's grammar accepts, mapped to their switch. A word
    #: absent here (XML, YAML, DOT, ...) is not a spelling this server parses.
    _EXPLAIN_FORMAT_PROBES = {
        "TEXT": "supports_explain_format_text",
        "JSON": "supports_explain_format_json",
        "TREE": "supports_explain_format_tree",
        "TRADITIONAL": "supports_explain_format_traditional",
    }

    def supports_explain_analyze(self) -> bool:
        """Whether EXPLAIN ANALYZE is supported (MySQL 8.0.18+)."""
        return self.version_at_least((8, 0, 18))

    # --- format words ---------------------------------------------------
    def supports_explain_format_text(self) -> bool:
        """Whether FORMAT=TEXT is supported (every MySQL version)."""
        return True

    def supports_explain_format_json(self) -> bool:
        """Whether FORMAT=JSON is supported (MySQL 5.6.5+)."""
        return self.version_at_least((5, 6, 5))

    def supports_explain_format_tree(self) -> bool:
        """Whether FORMAT=TREE is supported (MySQL 8.0.16+)."""
        return self.version_at_least((8, 0, 16))

    def supports_explain_format_traditional(self) -> bool:
        """Whether FORMAT=TRADITIONAL is a spelled-out format (MySQL 8.0.16+).

        Before 8.0.16 the classic table output is the default and cannot be
        named; 8.0.16 added the word, and MySQL 9 changed the default, which is
        why the formatter emits it explicitly there.
        """
        return self.version_at_least((8, 0, 16))

    def supports_explain_format_xml(self) -> bool:
        """MySQL has no FORMAT=XML."""
        return False

    def supports_explain_format_yaml(self) -> bool:
        """MySQL has no FORMAT=YAML."""
        return False

    # --- option words ---------------------------------------------------
    # MySQL's grammar has none of these, on any version. They are declared so
    # the answer is "no" rather than "the attribute is missing", and the
    # formatter refuses a request instead of dropping it.
    def supports_explain_verbose(self) -> bool:
        """Whether EXPLAIN VERBOSE is supported (never on MySQL)."""
        return False

    def supports_explain_costs(self) -> bool:
        """Whether EXPLAIN COSTS is supported (never on MySQL)."""
        return False

    def supports_explain_buffers(self) -> bool:
        """Whether EXPLAIN BUFFERS is supported (never on MySQL)."""
        return False

    def supports_explain_timing(self) -> bool:
        """Whether EXPLAIN TIMING is supported (never on MySQL)."""
        return False

    def supports_explain_settings(self) -> bool:
        """Whether EXPLAIN SETTINGS is supported (never on MySQL)."""
        return False

    def supports_explain_wal(self) -> bool:
        """Whether EXPLAIN WAL is supported (never on MySQL)."""
        return False

    def format_explain_statement(self, expr: "ExplainStatement") -> tuple:
        """Build the MySQL EXPLAIN SQL string and return (sql, params)."""
        from rhosocial.activerecord.backend.expression.statements import ExplainType

        statement_sql, statement_params = expr.statement.to_sql()
        options = expr.options
        parts = ["EXPLAIN"]

        needs_traditional_format = False
        if options is None:
            needs_traditional_format = self.version >= (9, 0, 0)
        else:
            if options.analyze:
                if not self.supports_explain_analyze():
                    raise UnsupportedFeatureError(self.name, "EXPLAIN ANALYZE")
                parts.append("ANALYZE")

            if options.format is not None:
                # ``format`` is the enum member or the word it spells; asking
                # the value whether it carries a ``name`` cannot tell the two
                # apart from anything else.
                fmt = options.format
                fmt_name = fmt.value if isinstance(fmt, Enum) else str(fmt)
                probe = self._EXPLAIN_FORMAT_PROBES.get(fmt_name.upper())
                if probe is None or not getattr(self, probe)():
                    raise UnsupportedFeatureError(
                        self.name, f"EXPLAIN FORMAT={fmt_name.upper()}"
                    )
                parts.append(f"FORMAT={fmt_name.upper()}")
            elif options.type is not None and options.type == ExplainType.QUERY_PLAN:
                pass
            else:
                needs_traditional_format = self.version >= (9, 0, 0)

            # PostgreSQL option words MySQL's grammar does not parse. The
            # caller asked for behaviour this server cannot express, so the
            # request is refused by name rather than rendered without it.
            if not options.costs:
                raise UnsupportedFeatureError(self.name, "EXPLAIN COSTS OFF")
            if options.verbose:
                raise UnsupportedFeatureError(self.name, "EXPLAIN VERBOSE")
            if options.buffers:
                raise UnsupportedFeatureError(self.name, "EXPLAIN BUFFERS")
            if options.timing and options.analyze:
                raise UnsupportedFeatureError(self.name, "EXPLAIN TIMING")
            if options.settings:
                raise UnsupportedFeatureError(self.name, "EXPLAIN SETTINGS")
            if options.wal:
                raise UnsupportedFeatureError(self.name, "EXPLAIN WAL")

        if needs_traditional_format:
            if not self.supports_explain_format_traditional():
                raise UnsupportedFeatureError(self.name, "EXPLAIN FORMAT=TRADITIONAL")
            parts.append("FORMAT=TRADITIONAL")

        return f"{' '.join(parts)} {statement_sql}", statement_params
