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


#: Directories whose assertions this server's implicit behaviour invalidates.
#:
#: MySQL before 8.0.2 defaults ``explicit_defaults_for_timestamp`` to OFF: the
#: table's first TIMESTAMP column then carries an implicit
#: ``DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP``, so an UPDATE
#: rewrites a column it never names. ``feature/basic/crud`` asserts that a
#: field nobody touched keeps its value. The suite does not bend for one
#: backend, and the server's configuration is the operator's, so the directory
#: is skipped here when the session answers that way.
_IMPLICIT_TIMESTAMP_DIRECTORIES = ("feature/basic/crud",)

#: The session's answer, per scenario name, read once.
_TIMESTAMP_DEFAULTS_ARE_EXPLICIT: dict = {}


def _timestamp_defaults_are_explicit(scenario) -> bool:
    """Whether this scenario's sessions keep TIMESTAMP columns explicit.

    The version is not asked: the setting is what matters, and a server started
    with ``--explicit-defaults-for-timestamp=ON`` answers differently from a
    same-version server that was not. The answer comes from the dialect, which
    records the session's value during adaptation.
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


@pytest.fixture(autouse=True)
def skip_directories_this_server_cannot_satisfy(request):
    """Skip the shared directories whose assertions this server breaks."""
    path = str(getattr(request.node, "path", "")).replace("\\", "/")
    directory = next(
        (name for name in _IMPLICIT_TIMESTAMP_DIRECTORIES if name in path), None
    )
    if directory is None:
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
        "@@SESSION.explicit_defaults_for_timestamp is OFF on this server, so it "
        "rewrites the table's first TIMESTAMP column on UPDATE; {} asserts that "
        "an unmodified field keeps its value".format(directory)
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
