# tests/conftest.py
"""
This is the root pytest configuration file for the rhosocial-activerecord-mysql package's test suite.

Its primary responsibility is to configure the environment so that the external
`rhosocial-activerecord-testsuite` can find and use the backend-specific
implementations (Providers) defined within this project.
"""
import os
import asyncio
import pytest

# Set the environment variable that the testsuite uses to locate the provider registry.
# The testsuite is a generic package and doesn't know the specific location of the
# provider implementations for this backend (MySQL). This environment variable
# acts as a bridge, pointing the testsuite to the correct import path.
#
# `setdefault` is used to ensure that this value is set only if it hasn't been
# set already, allowing for overrides in different environments if needed.
os.environ.setdefault(
    'TESTSUITE_PROVIDER_REGISTRY',
    'providers.registry:provider_registry'
)


@pytest.fixture(autouse=True)
def suppress_asyncio_broken_pipe(event_loop):
    """
    Suppress BrokenPipeError in asyncio event loop exception handler.

    In MySQL 5.6 + Python 3.8 asyncio combination, writes to dead connections
    may raise BrokenPipeError through the asyncio transport layer via the
    event loop's exception handler rather than through normal try/except.

    This fixture suppresses BrokenPipeError in the event loop to prevent
    test failures caused by this asyncio-specific behavior.
    """
    original_handler = event_loop.get_exception_handler()

    def handler(loop, context):
        exc = context.get("exception")
        if isinstance(exc, BrokenPipeError):
            return  # suppress BrokenPipeError
        if original_handler:
            original_handler(loop, context)
        else:
            loop.default_exception_handler(context)

    event_loop.set_exception_handler(handler)
    yield
    event_loop.set_exception_handler(original_handler)