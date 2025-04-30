"""Entry module for the application."""

import asyncio
import logging
import signal

from app.connectors.rabbitmq import get_rabbitmq_connection
from app.connectors.redis import get_redis_connection
from app.game_event.consumer import start_consumer as start_game_events_consumer
from app.game_state.consumer import start_consumer as start_game_state_consumer

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point for the application."""

    logger.info("Starting application...")

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    consumer_task = asyncio.create_task(start_game_events_consumer())
    worker_task = asyncio.create_task(start_game_state_consumer())

    logger.info("Application started. Waiting for messages...")
    await asyncio.gather(consumer_task, worker_task)


async def shutdown() -> None:
    """Shutdown the application gracefully."""

    logger.info("Shutting down...")
    # Cancel the tasks
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task():
            task.cancel()

    # Close third-party connections
    redis = await get_redis_connection()
    await redis.aclose()
    rabbitmq = await get_rabbitmq_connection()
    await rabbitmq.close()


if __name__ == "__main__":
    asyncio.run(main())
