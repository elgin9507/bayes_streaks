"""Enumeration for game events."""

from enum import Enum


class EVENT_TYPE(Enum):
    """Enumeration for game event types."""

    MATCH_START = "MATCH_START"
    MINION_KILL = "MINION_KILL"
    PLAYER_KILL = "PLAYER_KILL"
    DRAGON_KILL = "DRAGON_KILL"
    TURRET_DESTROY = "TURRET_DESTROY"
    MATCH_END = "MATCH_END"
    UNKNOWN = "UNKNOWN"
