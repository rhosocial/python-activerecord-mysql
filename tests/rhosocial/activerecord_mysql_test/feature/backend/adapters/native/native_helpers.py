# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/native/native_helpers.py
"""Small shared helpers for the native-type tests."""


def mark_for_write(instance, *fields: str) -> None:
    """Mark fields as modified without changing their value.

    ``save()`` only writes tracked (dirty) fields, and change tracking compares
    values, so assigning an equal value does not schedule an update.  Setting a
    field to ``None`` and back marks it dirty while leaving the value intact --
    which is what S2 needs: the *same* value must be written back, so a
    re-encoding bug shows up as a changed stored form.
    """
    for field in fields:
        original = getattr(instance, field)
        setattr(instance, field, None)
        setattr(instance, field, original)
    assert instance.is_dirty, "the row must actually be rewritten"
