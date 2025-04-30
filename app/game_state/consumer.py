"""Game state updates consumer module."""

import logging

from app.connectors.rabbitmq import get_game_state_updates_queue
from app.game_state.services import process_game_event

logger = logging.getLogger(__name__)


async def start_consumer():
    """Start the consumer for game state updates."""

    queue = await get_game_state_updates_queue()

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                event_id = message.body.decode()
                logging.info("Received game event ID: %s", event_id)
                await process_game_event(event_id)
                logging.info("Processed game event ID: %s", event_id)
