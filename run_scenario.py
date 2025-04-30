"""Run a game scenario for sample game."""

import asyncio
import json
import logging
import os
from pprint import pprint

import aio_pika
import aio_pika.abc

from app.connectors.rabbitmq import get_game_events_queue
from app.connectors.redis import get_redis_connection
from app.game_state.services import GameState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the game scenario."""

    # Flush Redis data
    redis = await get_redis_connection()
    await redis.flushdb()

    # Publish game events to RabbitMQ
    game_events_queue = await get_game_events_queue()
    await publish_game_events(game_events_queue.channel.default_exchange, game_events_queue)

    # Get final game state
    await get_final_game_state()


async def publish_game_events(exchange: aio_pika.abc.AbstractExchange, queue: aio_pika.abc.AbstractQueue):
    """Publish game events to the queue."""

    data_folder = os.path.join(os.path.dirname(__file__), "data")
    event_files = sorted(os.listdir(data_folder))
    match_start_file = os.path.join(data_folder, event_files[0])
    match_end_file = os.path.join(data_folder, event_files[-1])

    await publish_game_event(exchange, queue, match_start_file)

    for event_file in event_files[1:-1]:
        event_file_path = os.path.join(data_folder, event_file)
        await publish_game_event(exchange, queue, event_file_path)

    await publish_game_event(exchange, queue, match_end_file)


async def publish_game_event(
    exchange: aio_pika.abc.AbstractExchange, queue: aio_pika.abc.AbstractQueue, event_file: str
):
    """Publish a single game event to the queue."""

    logger.info("Publishing game event: %s", event_file)
    with open(event_file, "r") as file:
        try:
            data = json.load(file)
        except Exception as e:
            logger.exception("Error decoding JSON File: %s", event_file)
        else:
            message = aio_pika.Message(body=json.dumps(data).encode())
            await exchange.publish(message, routing_key=queue.name)
            logger.info("Published message: %s", message.body.decode())


async def get_final_game_state(timeout: int = 20):
    """Get the final game state from Redis."""

    match_id = "riot:lol:match:f969bd21-4223-4efc-90bd-a4769761f681"

    while True:
        try:
            game_state = await GameState.from_database(match_id)
        except Exception:
            # probably game state queue is not fully consumed yet
            await asyncio.sleep(1)
            timeout -= 1
        else:
            print("======================" * 3)
            print("Game State".center(65))
            print("======================" * 3)
            pprint(game_state.to_dict(), width=200)
            break

        if timeout <= 0:
            print("Timeout reached while waiting for game state.")
            break


if __name__ == "__main__":
    asyncio.run(main())
