"""Configuration settings for the application."""

import logging

from pydantic import Field
from pydantic_settings import BaseSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("aiormq").setLevel(logging.WARNING)
logging.getLogger("aio_pika").setLevel(logging.WARNING)


class Settings(BaseSettings):
    """Configuration settings object."""

    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost/",
        env="RABBITMQ_URL",
        description="RabbitMQ connection URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL",
    )
    redis_game_events_namespace: str = Field(
        default="game_events",
        env="REDIS_GAME_EVENTS_NAMESPACE",
        description="Redis namespace for game events",
    )
    redis_game_state_namespace: str = Field(
        default="game_state",
        env="REDIS_GAME_STATE_NAMESPACE",
        description="Redis namespace for game state",
    )
    kill_streak_time_window: int = Field(
        default=10,
        env="KILL_STREAK_TIME_WINDOW",
        description="Time window for kill streaks in seconds",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
