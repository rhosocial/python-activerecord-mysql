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
