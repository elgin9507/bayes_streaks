"""Data models for the game state."""

from pydantic import BaseModel, Field


class GameState(BaseModel):
    """Game state from database."""

    match_id: str = Field(..., description="Match ID")
    title: str = Field(..., description="Game title")
    start_time: str = Field(..., description="Game start time")
    series_type: str = Field(..., description="Game series type")
    series_current: int = Field(..., description="Current series number")
    series_max: int = Field(..., description="Maximum series number")
    winning_team_id: str = Field(..., description="Winning team ID")
    first_blood: str = Field(..., description="First blood event")
    teams: dict[str, "TeamState"] = Field(default_factory=dict, description="List of teams in the game")


class TeamState(BaseModel):
    """Team state from database."""

    team_id: str = Field(..., description="Team ID")
    dragon_kills: int = Field(..., description="Number of dragon kills")
    tower_kills: int = Field(..., description="Number of tower kills")
    players: dict[str, "PlayerState"] = Field(default_factory=dict, description="List of players in the team")


class PlayerState(BaseModel):
    """Player state from database."""

    player_id: str = Field(..., description="Player ID")
    name: str = Field(..., description="Player name")
    alive: bool = Field(..., description="Is the player alive")
    gold: int = Field(..., description="Player's gold amount")
    human_kills: int = Field(..., description="Number of human kills")
    human_kills_assists: int = Field(..., description="Number of human kills assists")
    minion_kills: int = Field(..., description="Number of minion kills")
    kill_streaks: list[str] = Field(default_factory=list, description="List of kill streaks")
    max_killing_spree: str | None = Field(None, description="Maximum killing before death streak")
