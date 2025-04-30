"""Game events consumer module."""

import json
import logging
import uuid

import aio_pika

from app import settings
from app.connectors.rabbitmq import get_game_events_queue, get_game_state_updates_queue
from app.connectors.redis import get_redis_connection

logger = logging.getLogger(__name__)


async def start_consumer():
    """Start the consumer for game events."""

    events_queue = await get_game_events_queue()
    state_updates_queue = await get_game_state_updates_queue()
    redis = await get_redis_connection()

    async with events_queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                logging.info(f"Received message: {message.body.decode()}")

                try:
                    data = json.loads(message.body.decode())
                except json.JSONDecodeError as e:
                    logger.warning("Error decoding JSON: %s", e)
                else:
                    event_id = str(uuid.uuid4())
                    data["payload"] = json.dumps(data["payload"])
                    name = f"{settings.redis_game_events_namespace}:event:{event_id}"
                    await redis.hset(name=name, mapping=data)
                    await state_updates_queue.channel.default_exchange.publish(
                        aio_pika.Message(body=event_id.encode()),
                        routing_key=state_updates_queue.name,
                    )
