# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/introspection/test_introspection_data_profile.py
"""The data-profile family, measured against a real server.

Rendering these statements proves only that they are well-formed. What needs
checking is whether MySQL accepts them, and whether the arithmetic the parser
performs -- turning ``null_count / row_count`` into a fraction, reading
``COUNT(DISTINCT ...)`` as a count, and carrying the ``source`` label through --
lands on values a hand count agrees with. That is only answerable against a
server.

The table is a hundred rows, built so every figure is arithmetic rather than
guesswork:

    id      INT PRIMARY KEY       i, unique             -> 100 distinct, no nulls
    code    VARCHAR(8) NOT NULL   "a"/"b"/"c" by i % 3  -> 3 distinct, no nulls
    amount  DECIMAL(10,2)         i, unique             -> 100 distinct, no nulls
    note    VARCHAR(8) NULL       "x" when i % 5 == 0, "y" when i % 5 == 1,
                                  NULL otherwise          -> 2 distinct, 60% null

The size is modest on purpose, and the reason differs from the PostgreSQL test:
MySQL aggregates the rows rather than reading a histogram, so the answer does
not depend on a sample being large. It only has to be big enough that a
duplicate silently dropped by ``COUNT(DISTINCT ...)``, or a NULL miscounted by
the ``SUM(CASE ...)`` arm, would move a number off its hand-counted value --
which a hundred rows does. A thousand would describe exactly the same facts
and cost ten times the setup.

Two shapes differ from PostgreSQL and are pinned here rather than left to be
discovered. First, MySQL aggregates the rows, so the profile is ``AGGREGATE``
and every figure is exact, while PostgreSQL reads ``pg_stats`` and answers
``ESTIMATE``. Second, the value listing is a ``GROUP BY`` over the column, and
MySQL groups NULLs into a real row -- so a column that contains NULLs has a
NULL entry in its listing, and it is usually the most frequent one. PostgreSQL
tracks NULLs in ``null_frac`` and never in its most-common list. Same question,
two engines, two shapes.

A third difference is visible only in the Python types. MySQL resolves one
result type per column position across the arms of a ``UNION ALL``, so the
``min_value`` slot -- which holds ``code``'s text in one arm and ``amount``'s
decimal in another -- comes back as text (``"1.00"``), not as a number. The
figures are exact; only the type is the union's. The test reads the decimal
endpoints through ``Decimal`` and says why, so a future formatter that
"fixes" this by casting would have to disagree with it on purpose.
"""

from decimal import Decimal

import pytest


TABLE = "intro_profile_orders"
CUSTOMERS = "intro_profile_customers"
CODES = ("a", "b", "c")

ROWS = 100

#: ``note`` is NULL on 60 of the 100 rows, "x" on 20 and "y" on 20.
NULL_SHARE = 0.6
NOTE_COUNT = 20


def _rows():
    rows = []
    for i in range(1, ROWS + 1):
        if i % 5 == 0:
            note = "x"
        elif i % 5 == 1:
            note = "y"
        else:
            note = None
        rows.append((i, CODES[i % 3], i, note))
    return rows


def _setup(backend):
    backend.execute(f"DROP TABLE IF EXISTS `{TABLE}`")
    backend.execute(f"DROP TABLE IF EXISTS `{CUSTOMERS}`")
    backend.execute(
        f"CREATE TABLE `{TABLE}` ("
        "`id` INT NOT NULL PRIMARY KEY, "
        "`code` VARCHAR(8) NOT NULL, "
        "`amount` DECIMAL(10,2) NOT NULL, "
        "`note` VARCHAR(8) NULL"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    backend.execute_many(
        f"INSERT INTO `{TABLE}` (`id`, `code`, `amount`, `note`) "
        "VALUES (%s, %s, %s, %s)",
        _rows(),
    )
    # The right side of every coverage measurement: four codes and one NULL.
    # The NULL is the point -- it must not be counted as a value of the domain,
    # so right coverage is 3/4 and not 3/5.
    backend.execute(
        f"CREATE TABLE `{CUSTOMERS}` ("
        "`id` INT NOT NULL PRIMARY KEY, "
        "`code` VARCHAR(8) NULL"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    backend.execute_many(
        f"INSERT INTO `{CUSTOMERS}` (`id`, `code`) VALUES (%s, %s)",
        [(1, "a"), (2, "b"), (3, "c"), (4, "d"), (5, None)],
    )


def _teardown(backend):
    backend.execute(f"DROP TABLE IF EXISTS `{TABLE}`")
    backend.execute(f"DROP TABLE IF EXISTS `{CUSTOMERS}`")


class TestColumnDataProfile:
    """What the rows hold, counted by the server rather than read from a catalog."""

    def test_profile_matches_a_hand_count(self, mysql_backend):
        _setup(mysql_backend)
        try:
            profiles = {
                profile.column_name: profile
                for profile in mysql_backend.introspector.list_column_data_profiles(
                    TABLE
                )
            }
            assert set(profiles) == {"id", "code", "amount", "note"}

            # A unique key: 100 distinct values, none of them NULL.
            assert profiles["id"].null_fraction == 0.0
            assert profiles["id"].distinct_count == ROWS
            assert int(profiles["id"].min_value) == 1
            assert int(profiles["id"].max_value) == ROWS

            # Three values, none null. COUNT(DISTINCT ...) ignores NULL on its
            # own, so the count agrees with the listing below.
            assert profiles["code"].null_fraction == 0.0
            assert profiles["code"].distinct_count == len(CODES)
            assert profiles["code"].min_value == "a"
            assert profiles["code"].max_value == "c"

            # DECIMAL arrives as text, because a ``UNION ALL`` resolves *one*
            # result type per column across every arm and the ``min_value``
            # slot also carries ``code``'s and ``note``'s strings. The figure
            # is exact; only the Python type is the union's, which is why this
            # reads it through Decimal rather than comparing the text to "1".
            assert profiles["amount"].null_fraction == 0.0
            assert profiles["amount"].distinct_count == ROWS
            assert Decimal(str(profiles["amount"].min_value)) == Decimal("1")
            assert Decimal(str(profiles["amount"].max_value)) == Decimal(ROWS)

            # 60 of 100 rows are NULL, so a profile that dropped the figure
            # or clamped it would still look plausible.
            assert profiles["note"].null_fraction == pytest.approx(NULL_SHARE)
            assert profiles["note"].distinct_count == 2
            assert profiles["note"].min_value == "x"
            assert profiles["note"].max_value == "y"
        finally:
            _teardown(mysql_backend)

    def test_every_profile_says_it_was_aggregated(self, mysql_backend):
        """The label rides the row, so a consumer never has to guess.

        MySQL has no statistics catalogue to read, so every figure here is an
        exact count of the rows -- and the answer says so in ``source`` rather
        than leaving a caller to infer it from which engine answered. There is
        no ``collected_at``: an aggregate is current by construction, and
        inventing a timestamp would make it look like a stale estimate.
        """
        _setup(mysql_backend)
        try:
            profiles = mysql_backend.introspector.list_column_data_profiles(TABLE)
            assert profiles
            assert {profile.source for profile in profiles} == {"aggregate"}
            for profile in profiles:
                assert profile.collected_at is None
                assert profile.row_count == ROWS
        finally:
            _teardown(mysql_backend)

    def test_empty_table_answers_with_zero_rows_and_no_fraction(self, mysql_backend):
        """A profile of nothing is a row count of zero, not a fabricated 0.0.

        ``SUM`` over no rows is NULL, so ``null_count`` is NULL and the
        fraction is not derived. Saying 0.0 would claim the column holds no
        NULLs, which is not something an empty table establishes.
        """
        mysql_backend.execute(f"DROP TABLE IF EXISTS `{TABLE}`")
        mysql_backend.execute(f"CREATE TABLE `{TABLE}` (`id` INT NULL)")
        try:
            profiles = mysql_backend.introspector.list_column_data_profiles(TABLE)
            assert len(profiles) == 1
            profile = profiles[0]
            assert profile.column_name == "id"
            assert profile.row_count == 0
            assert profile.distinct_count == 0
            assert profile.null_fraction is None
            assert profile.min_value is None
            assert profile.max_value is None
            assert profile.source == "aggregate"
        finally:
            _teardown(mysql_backend)


class TestColumnValueSample:
    """The grouped scan, which unlike PostgreSQL's list can contain NULL."""

    def test_listing_is_ordered_by_frequency(self, mysql_backend):
        _setup(mysql_backend)
        try:
            samples = mysql_backend.introspector.sample_column_values(
                TABLE, "code", limit=10
            )
            # CODES[i % 3] puts "b" on 34 rows (i % 3 == 1) and "a"/"c" on 33
            # each, so the order is frequency first and then the tie-break by
            # value -- which is why "a" precedes "c" despite equal counts.
            assert [item.value for item in samples] == ["b", "a", "c"]
            assert [item.count for item in samples] == [34, 33, 33]
            # The engine reports a count, not a fraction. A formatter that
            # divided for it would have had to assume the row count.
            assert all(item.frequency is None for item in samples)
        finally:
            _teardown(mysql_backend)

    def test_limit_bounds_the_listing(self, mysql_backend):
        _setup(mysql_backend)
        try:
            assert (
                len(
                    mysql_backend.introspector.sample_column_values(
                        TABLE, "code", limit=2
                    )
                )
                == 2
            )
        finally:
            _teardown(mysql_backend)

    def test_null_is_a_value_of_the_domain(self, mysql_backend):
        """MySQL groups NULLs, so the listing has a NULL row -- usually first.

        This is the shape that differs from PostgreSQL, whose most-common list
        never contains NULL because ``null_frac`` holds that fact separately.
        A caller reading a listing for "what is in this column" must therefore
        not assume every entry is a value; the profile's ``null_fraction`` is
        the cross-engine answer, and this test is what says so for MySQL.
        """
        _setup(mysql_backend)
        try:
            samples = mysql_backend.introspector.sample_column_values(
                TABLE, "note", limit=10
            )
            # NULL at 60 rows, then "x" and "y" at 20 each.
            assert samples[0].value is None
            assert samples[0].count == ROWS - 2 * NOTE_COUNT
            assert {item.value for item in samples if item.value is not None} == {
                "x",
                "y",
            }
            assert sum(item.count for item in samples) == ROWS
        finally:
            _teardown(mysql_backend)


class TestJoinCoverage:
    """Overlap measured over distinct values, on both sides."""

    def test_coverage_is_measured_over_distinct_values(self, mysql_backend):
        """3 of orders' 3 codes exist among customers' 4 non-null codes.

        Row counts would say something else entirely: 100 order rows map onto
        4 customer rows. Counting distinct values is what makes the number a
        statement about the domains rather than about repetition.
        """
        _setup(mysql_backend)
        try:
            coverage = mysql_backend.introspector.estimate_join_coverage(
                TABLE, "code", CUSTOMERS, "code"
            )
            assert coverage is not None
            assert coverage.left_coverage == pytest.approx(1.0)
            assert coverage.right_coverage == pytest.approx(0.75)
            assert coverage.left_table == TABLE
            assert coverage.right_table == CUSTOMERS
        finally:
            _teardown(mysql_backend)

    def test_the_measurement_is_not_symmetric(self, mysql_backend):
        """Reversing the sides swaps the fractions, it does not copy them."""
        _setup(mysql_backend)
        try:
            coverage = mysql_backend.introspector.estimate_join_coverage(
                CUSTOMERS, "code", TABLE, "code"
            )
            assert coverage is not None
            assert coverage.left_coverage == pytest.approx(0.75)
            assert coverage.right_coverage == pytest.approx(1.0)
        finally:
            _teardown(mysql_backend)

    def test_an_empty_domain_is_no_measurement_rather_than_zero(self, mysql_backend):
        """``NULLIF(..., 0)`` is the difference between "none" and "unmeasurable".

        With no customer rows there is nothing to divide by, and answering
        ``0.0`` would read as "none of these values join" -- a different claim.
        The left side still has a real denominator, so its 0.0 is a genuine
        zero and must survive.
        """
        _setup(mysql_backend)
        try:
            mysql_backend.execute(f"DELETE FROM `{CUSTOMERS}`")
            coverage = mysql_backend.introspector.estimate_join_coverage(
                TABLE, "code", CUSTOMERS, "code"
            )
            assert coverage is not None
            assert coverage.left_coverage == pytest.approx(0.0)
            assert coverage.right_coverage is None
        finally:
            _teardown(mysql_backend)
