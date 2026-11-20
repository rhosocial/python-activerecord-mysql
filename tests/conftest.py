# tests/conftest.py
"""Root configuration for the MySQL backend's test tree.

The backend knows its own classes and how a scenario maps to a connection, so
no declaration table is needed here: the scenario is exposed as a parameterized
pytest fixture that the testsuite environment consumes.
"""
import asyncio

import pytest

import support.mysql

_SCENARIOS = [support.mysql.scenario(name) for name in support.mysql.SCENARIOS]


@pytest.fixture(scope="session", params=_SCENARIOS, ids=lambda scenario: scenario.name)
def backend_scenario(request):
    """Return the scenario the tests run against; its id is the scenario name."""
    return request.param


#: The suite's package prefix: a bridge file imports its tests with ``*``, so the
#: test objects keep this module and identify themselves as suite tests even
#: though the file that re-exports them lives here.
_SUITE_PACKAGE_PREFIX = "rhosocial.activerecord.testsuite."

#: Whether each scenario's sessions keep TIMESTAMP columns explicit, read once.
_TIMESTAMP_DEFAULTS_ARE_EXPLICIT: dict = {}


def _is_shared_suite_test(item) -> bool:
    """Whether this item's test object comes from the shared suite."""
    for owner in (
        getattr(item, "cls", None),
        getattr(item, "function", None),
        getattr(item, "obj", None),
    ):
        module = getattr(owner, "__module__", "")
        if module.startswith(_SUITE_PACKAGE_PREFIX):
            return True
    return False


def _timestamp_defaults_are_explicit(scenario) -> bool:
    """Whether this scenario's sessions keep TIMESTAMP columns explicit.

    The answer comes from the dialect, which records the session's variables
    during adaptation -- so a server started with a different setting answers
    according to what it actually does, not according to its version.
    """
    answer = _TIMESTAMP_DEFAULTS_ARE_EXPLICIT.get(scenario.name)
    if answer is None:
        backend = scenario.backend_class(
            connection_config=scenario.make_config("")
        )
        backend.connect()
        try:
            backend.introspect_and_adapt()
            answer = backend.dialect.explicit_defaults_for_timestamp()
        finally:
            backend.disconnect()
        _TIMESTAMP_DEFAULTS_ARE_EXPLICIT[scenario.name] = answer
    return answer


def pytest_collection_modifyitems(items):
    """Skip shared-suite contracts MySQL's driver cannot honor."""
    reason = (
        "MySQL rejects the neutral Geometry value with errno 1416 "
        "('Cannot get geometry object from data you send to the GEOMETRY field'); "
        "the adapter's wire form is not accepted by this driver version."
    )
    for item in items:
        if _is_shared_suite_test(item) and item.originalname in (
            "test_geometry_roundtrip",
            "test_geometry_roundtrip_async",
        ):
            item.add_marker(pytest.mark.skip(reason=reason))


@pytest.fixture(autouse=True)
def skip_the_shared_suite_when_timestamps_are_implicit(request):
    """Skip the shared suite on a server that rewrites TIMESTAMP columns.

    The suite assumes an UPDATE leaves a TIMESTAMP column it does not name
    alone: one directory asserts it directly, others depend on it (a rewritten
    ``start_at`` breaks the period validator, a rewritten ``created_at`` breaks
    the row comparison). A server reporting ``explicit_defaults_for_timestamp``
    OFF rewrites the table's first TIMESTAMP column, so the suite cannot be
    satisfied there at all. The suite does not bend for one backend, and the
    server's configuration is the operator's, so it is skipped as a whole --
    bridge files included, which is why the test object's module decides.
    """
    if not _is_shared_suite_test(request.node):
        yield
        return
    callspec = getattr(request.node, "callspec", None)
    scenario = getattr(callspec, "params", {}).get("backend_scenario")
    if scenario is None:
        yield
        return
    if _timestamp_defaults_are_explicit(scenario):
        yield
        return
    pytest.skip(
        "explicit_defaults_for_timestamp is OFF on this server, so an "
        "UPDATE rewrites the table's first TIMESTAMP column; the shared suite "
        "assumes it does not"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_asyncio_broken_pipe_handler():
    """
    Set up asyncio event loop exception handler to suppress BrokenPipeError.

    In MySQL 5.6 + Python 3.8 asyncio combination, writes to dead connections
    may raise BrokenPipeError through the asyncio transport layer via the
    event loop's exception handler rather than through normal try/except.

    This fixture sets up the handler at session start and restores it at end.
    """

    def handler(loop, context):
        exc = context.get("exception")
        if isinstance(exc, BrokenPipeError):
            return  # suppress BrokenPipeError
        loop.default_exception_handler(context)

    # Set up handler for any existing loop
    try:
        loop = asyncio.get_running_loop()
        original_handler = loop.get_exception_handler()
        loop.set_exception_handler(handler)
    except RuntimeError:
        # No running loop yet
        original_handler = None

    yield

    # Restore original handler if we modified one
    try:
        loop = asyncio.get_running_loop()
        if original_handler:
            loop.set_exception_handler(original_handler)
    except RuntimeError:
        pass
