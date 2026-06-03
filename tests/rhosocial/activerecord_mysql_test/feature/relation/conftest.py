# tests/rhosocial/activerecord_mysql_test/feature/relation/conftest.py
"""
Pytest configuration for relation feature tests.

This file imports fixtures from the corresponding testsuite, making them
available to the tests in this directory.
"""
from rhosocial.activerecord.testsuite.feature.relation.conftest import *

import pytest_asyncio


@pytest_asyncio.fixture(scope="function", params=SCENARIO_PARAMS)
async def async_user_class(request):
    from rhosocial.activerecord.testsuite.core.registry import get_provider_registry

    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider(PROVIDER_KEY)
    provider = provider_class()
    model = provider.setup_async_user_model(scenario)
    await provider._ensure_user_post_comment_async_schema()
    yield model
    await provider.cleanup_after_test_async(scenario)


@pytest_asyncio.fixture(scope="function", params=SCENARIO_PARAMS)
async def async_post_class(request):
    from rhosocial.activerecord.testsuite.core.registry import get_provider_registry

    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider(PROVIDER_KEY)
    provider = provider_class()
    model = provider.setup_async_post_model(scenario)
    await provider._ensure_user_post_comment_async_schema()
    yield model
    await provider.cleanup_after_test_async(scenario)


@pytest_asyncio.fixture(scope="function", params=SCENARIO_PARAMS)
async def async_comment_class(request):
    from rhosocial.activerecord.testsuite.core.registry import get_provider_registry

    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider(PROVIDER_KEY)
    provider = provider_class()
    model = provider.setup_async_comment_model(scenario)
    await provider._ensure_user_post_comment_async_schema()
    yield model
    await provider.cleanup_after_test_async(scenario)


@pytest_asyncio.fixture(scope="function", params=SCENARIO_PARAMS)
async def async_user_post_comment_classes(request):
    from rhosocial.activerecord.testsuite.core.registry import get_provider_registry

    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider(PROVIDER_KEY)
    provider = provider_class()
    user = provider.setup_async_user_model(scenario)
    post = provider.setup_async_post_model(scenario)
    comment = provider.setup_async_comment_model(scenario)
    await provider._ensure_user_post_comment_async_schema()
    yield user, post, comment
    await provider.cleanup_after_test_async(scenario)


@pytest_asyncio.fixture(scope="function", params=SCENARIO_PARAMS)
async def async_relation_boundary_context(request):
    from rhosocial.activerecord.testsuite.core.registry import get_provider_registry

    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider(PROVIDER_KEY)
    provider = provider_class()
    owner, profile, post = provider.setup_async_relation_boundary_fixtures(scenario)
    yield provider, scenario, owner, profile, post
    await provider.cleanup_after_test_async(scenario)
