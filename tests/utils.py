"""Utility functions for testing."""

import asyncio
import json
import os
from typing import Iterator

import aio_pika

from app.connectors.rabbitmq import get_game_events_queue
from app.game_state.services import GameState


async def run_scenario(scenario_name: str, game_id: str) -> GameState:
    """Run a game scenario and return the final game state."""

    await publish_game_events(scenario_name)
    game_state = await get_game_state(game_id)

    return game_state


async def publish_game_events(scenario_name: str) -> None:
    """Publish game events to RabbitMQ from a scenario."""

    game_events_queue = await get_game_events_queue()

    for event in events_for_scenario(scenario_name):
        message = aio_pika.Message(body=json.dumps(event).encode())

        await game_events_queue.channel.default_exchange.publish(
            message,
            routing_key=game_events_queue.name,
        )


async def get_game_state(game_id: str, timeout: int = 10) -> GameState:
    """Get the final game state from Redis."""

    while True:
        try:
            game_state = await GameState.from_database(game_id)
        except Exception as e:
            # probably game state queue is not fully consumed yet
            await asyncio.sleep(1)
            print(f"Error getting game state: {e}")
            timeout -= 1
        else:
            return game_state.to_dict()

        if timeout <= 0:
            raise TimeoutError(f"Timeout while waiting for game state: {game_id}")


def get_scenarios_folder() -> str:
    """Get the path to the scenarios folder."""
    return "tests/data/scenarios"


def events_for_scenario(scenario_name: str) -> Iterator[dict]:
    """Load events from a scenario file."""

    scenario_path = os.path.join(get_scenarios_folder(), scenario_name)
    event_files = sorted(os.listdir(scenario_path))
    start_event_file = event_files[0]
    end_event_file = event_files[-1]

    def load_event(file_name: str) -> dict:
        with open(os.path.join(scenario_path, file_name), "r") as file:
            return json.load(file)

    yield load_event(start_event_file)
    for event_file in event_files[1:-1]:
        yield load_event(event_file)
    yield load_event(end_event_file)
