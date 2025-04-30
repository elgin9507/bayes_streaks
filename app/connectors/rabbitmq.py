"""RabbitMQ connection manager."""

import aio_pika
import aio_pika.abc

from app import settings

_connection: aio_pika.abc.AbstractRobustConnection = None


async def get_rabbitmq_connection() -> aio_pika.abc.AbstractRobustConnection:
    """Get a connection to RabbitMQ."""
    global _connection

    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    return _connection


async def get_game_events_queue() -> aio_pika.abc.AbstractQueue:
    """Get the game events queue from which we receive all game events."""

    connection = await get_rabbitmq_connection()
    channel: aio_pika.abc.AbstractChannel = await connection.channel()
    queue: aio_pika.abc.AbstractQueue = await channel.declare_queue("game_events", durable=True)

    return queue


async def get_game_state_updates_queue() -> aio_pika.abc.AbstractQueue:
    """Get the game state updates queue to which we publish all game state updates."""

    connection = await get_rabbitmq_connection()
    channel: aio_pika.abc.AbstractChannel = await connection.channel()
    queue: aio_pika.abc.AbstractQueue = await channel.declare_queue("game_state_updates", durable=True)

    return queue
