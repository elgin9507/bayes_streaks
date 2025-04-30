"""Pytest configuration for the tests."""

import pytest_asyncio

from app.connectors.redis import get_redis_connection
from tests.utils import run_scenario


@pytest_asyncio.fixture(scope="session")
async def flush_redis():
    """Fixture to flush Redis database before each test."""
    redis = await get_redis_connection()
    await redis.flushdb()
    yield
    await redis.flushdb()


@pytest_asyncio.fixture(scope="session")
async def scenario_runner(request, flush_redis):
    """Fixture to run a scenario."""

    scenario_name, game_id = request.param

    async def run_scenario_fixture():
        """Run the scenario and return the final game state."""
        return await run_scenario(scenario_name, game_id)

    return run_scenario_fixture
