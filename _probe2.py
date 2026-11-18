from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

for factory in (lambda: MySQLDialect(), lambda: MySQLDialect(version=(8, 0, 46))):
    d = factory()
    try:
        t = d.suggested_column_types()
        print(type(d).__name__, "ok", len(t))
    except Exception as e:
        print(type(d).__name__, "!!", type(e).__name__, e)