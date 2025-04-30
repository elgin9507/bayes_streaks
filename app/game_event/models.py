"""Data models for game events."""

import logging
from typing import Any, Union

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.game_event.enum import EVENT_TYPE

PayloadType = Union[
    "MatchStartPayload",
    "MinionKillPayload",
    "PlayerKillPayload",
    "DragonKillPayload",
    "TurretDestroyPayload",
    "MatchEndPayload",
]
logger = logging.getLogger(__name__)


class GameEvent(BaseModel):
    """Model for game events."""

    match_id: str | None = Field(None, description="Unique identifier for the match", alias="matchID")
    type_: EVENT_TYPE = Field(EVENT_TYPE.UNKNOWN, alias="type", description="Type of the event")
    payload: Any
    timestamp: str | None = Field(None, description="Timestamp of the event")

    @field_validator("type_", mode="before")
    def validate_type(cls, value: str) -> EVENT_TYPE:
        """Validate the event type."""

        try:
            return EVENT_TYPE(value)
        except ValueError:
            return EVENT_TYPE.UNKNOWN

    @model_validator(mode="after")
    def resolve_payload(self) -> PayloadType | None:
        try:
            payload_data = self.payload
            match self.type_:
                case EVENT_TYPE.MATCH_START:
                    payload = MatchStartPayload(**payload_data)
                case EVENT_TYPE.MINION_KILL:
                    payload = MinionKillPayload(**payload_data)
                case EVENT_TYPE.PLAYER_KILL:
                    payload = PlayerKillPayload(**payload_data)
                case EVENT_TYPE.DRAGON_KILL:
                    payload = DragonKillPayload(**payload_data)
                case EVENT_TYPE.TURRET_DESTROY:
                    payload = TurretDestroyPayload(**payload_data)
                case EVENT_TYPE.MATCH_END:
                    payload = MatchEndPayload(**payload_data)
                case EVENT_TYPE.UNKNOWN:
                    logger.warning("Unknown event type: %s", self.type_)
                    logger.debug("Payload data: %s", payload_data)
                    payload = None
        except ValidationError as e:
            logging.error("Validation error while parsing event payload: %s", e)
            raise ValueError("Invalid payload data") from e

        self.payload = payload
        return self


class MatchStartPayload(BaseModel):
    """Payload model for match start event."""

    fixture: "GameMetadata" = Field(..., description="Fixture metadata")
    teams: list["MatchTeam"] = Field(..., description="List of teams in the match")


class MinionKillPayload(BaseModel):
    """Payload model for minion kill event."""

    player_id: str = Field(..., description="Unique identifier for the player", alias="playerID")
    gold_granted: int | None = Field(None, description="Gold granted for the kill", alias="goldGranted")


class PlayerKillPayload(BaseModel):
    """Payload model for player kill event."""

    killer_id: str | None = Field(None, description="Unique identifier for the killer", alias="killerID")
    victim_id: str | None = Field(None, description="Unique identifier for the victim", alias="victimID")
    gold_granted: int | None = Field(None, description="Gold granted for the kill", alias="goldGranted")
    assistants: list[str] | None = Field(
        None, description="List of unique identifiers for the assistants", alias="assistants"
    )
    assist_gold: int | None = Field(None, description="Gold granted for the assist", alias="assistGold")


class DragonKillPayload(BaseModel):
    """Payload model for dragon kill event."""

    killer_id: str = Field(..., description="Unique identifier for the player", alias="killerID")
    dragon_type: str | None = Field(None, description="Type of the dragon", alias="dragonType")
    gold_granted: int | None = Field(None, description="Gold granted for the kill", alias="goldGranted")


class TurretDestroyPayload(BaseModel):
    """Payload model for turret destroy event."""

    killer_id: str | None = Field(None, description="Unique identifier for the killer", alias="killerID")
    killer_team_id: str | None = Field(
        None, description="Unique identifier for the killer's team", alias="killerTeamID"
    )
    turret_tier: int | None = Field(None, description="Tier of the turret", alias="turretTier")
    turret_lane: str | None = Field(None, description="Lane of the turret", alias="turretLane")
    player_gold_granted: int | None = Field(
        None, description="Gold granted to the player for the kill", alias="playerGoldGranted"
    )
    team_gold_granted: int | None = Field(
        None, description="Gold granted to the team for the kill", alias="teamGoldGranted"
    )


class MatchEndPayload(BaseModel):
    """Payload model for match end event."""

    winning_team_id: str = Field(..., description="Unique identifier for the winning team", alias="winningTeamID")


class GameMetadata(BaseModel):
    """Game metadata model."""

    start_time: str = Field(..., description="Start time of the match", alias="startTime")
    title: str = Field(..., description="Title of the match")
    series_current: int = Field(..., description="Current series number", alias="seriesCurrent")
    series_max: int = Field(..., description="Maximum series number", alias="seriesMax")
    series_type: str = Field(..., description="Type of the series", alias="seriesType")


class MatchTeam(BaseModel):
    """Match team model."""

    team_id: str = Field(..., description="Unique identifier for the team", alias="teamID")
    players: list["MatchPlayer"] = Field(..., description="List of players in the team")


class MatchPlayer(BaseModel):
    """Match player model."""

    player_id: str = Field(..., description="Unique identifier for the player", alias="playerID")
    gold: int = Field(..., description="Number of gold coins")
    alive: bool = Field(..., description="Is the player alive?")
    name: str = Field(..., description="Name of the player")
