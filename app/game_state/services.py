"""Game state related services."""

import json
import logging

from pydantic import ValidationError

from app import settings
from app.connectors.redis import get_redis_connection
from app.game_event.enum import EVENT_TYPE
from app.game_event.models import GameEvent
from app.game_state import models
from app.game_state.processors import (
    DragonKillProcessor,
    MatchEndProcessor,
    MatchStartProcessor,
    MinionKillProcessor,
    PlayerKillProcessor,
    TurretDestroyProcessor,
)
from app.game_state.utils import (
    from_unix_timestamp,
    get_game_state_key,
    get_player_state_key,
    get_team_state_key,
    max_killing_spree_label,
)

logger = logging.getLogger(__name__)


class GameState:
    """Game state service class.

    Game state is stored in Redis. Data is stored in the following format:

      - game:<match_id> - General game state. Contains the following fields:
        - match_id: Unique identifier for the match
        - start_time: Start time of the match
        - title: Title of the match
        - series_current: Current series number
        - series_max: Maximum series number
        - series_type: Type of the series
        - teams: List of teams in the match and their players as nested JSON objects
        - first_blood: First blood timestamp
      -game:<match_id>:team:<team_id> - Team state. Contains the following fields:
        - dragon_kills: Number of dragon kills
        - tower_kills: Number of tower kills
      - game:<match_id>:player:<player_id> - Player state. Contains the following fields:
        - player_id: Unique identifier for the player
        - gold: Number of gold coins
        - alive: Is the player alive?
        - name: Name of the player
        - minion_kills: Number of minion kills
        - human_kills: Number of human kills
        - human_kills_assists: Number of human kills assists
        - team_members: List of team members in the match
      - game:<match_id>:player:<player_id>:kill_history - Player kill history. Sorted set of player kill timestamps.
      - game:<match_id>:player:<player_id>:death_history - Player death history. Sorted set of player death timestamps.
    """

    def __init__(
        self,
        match_id: str,
        title: str,
        start_time: str,
        series_type: str,
        series_current: int,
        series_max: int,
        winning_team_id: str,
        first_blood: str,
        teams: dict[str, models.TeamState],
    ) -> None:
        self.match_id = match_id
        self.title = title
        self.start_time = start_time
        self.series_type = series_type
        self.series_current = series_current
        self.series_max = series_max
        self.winning_team_id = winning_team_id
        self.first_blood = first_blood
        self.teams = teams

    def to_dict(self) -> dict:
        """Convert the game state to a dictionary."""
        return models.GameState(
            match_id=self.match_id,
            title=self.title,
            start_time=self.start_time,
            series_type=self.series_type,
            series_current=self.series_current,
            series_max=self.series_max,
            winning_team_id=self.winning_team_id,
            first_blood=self.first_blood,
            teams=self.teams,
        ).model_dump()

    @classmethod
    async def from_database(cls, match_id: str) -> "GameState":
        """Initialize the game state from the database."""

        redis = await get_redis_connection()
        game_state_key = get_game_state_key(match_id)
        game_state_data = await redis.hgetall(game_state_key)
        teams_data = json.loads(game_state_data["teams"])
        team_states = {}

        for team_data in teams_data:
            player_states = {}
            team_id = team_data["team_id"]
            team_state_key = get_team_state_key(team_id, match_id)
            team_state_data = await redis.hgetall(team_state_key)

            for player_id in team_data["players"]:
                player_state_key = get_player_state_key(player_id, match_id)
                player_state_data = await redis.hgetall(player_state_key)
                player_state = models.PlayerState(
                    player_id=player_state_data["player_id"],
                    name=player_state_data["name"],
                    alive=player_state_data["alive"],
                    gold=player_state_data["gold"],
                    human_kills=player_state_data["human_kills"],
                    human_kills_assists=player_state_data["human_kills_assists"],
                    minion_kills=player_state_data["minion_kills"],
                    kill_streaks=json.loads(player_state_data["kill_streaks"]),
                    max_killing_spree=max_killing_spree_label(int(player_state_data["max_killing_spree"])),
                )
                player_states[player_id] = player_state

            team_state = models.TeamState(
                team_id=team_id,
                dragon_kills=int(team_state_data["dragon_kills"]),
                tower_kills=int(team_state_data["tower_kills"]),
                players=player_states,
            )
            team_states[team_id] = team_state

        return cls(
            match_id=game_state_data["match_id"],
            title=game_state_data["title"],
            start_time=game_state_data["start_time"],
            series_type=game_state_data["series_type"],
            series_current=game_state_data["series_current"],
            series_max=game_state_data["series_max"],
            winning_team_id=game_state_data["winning_team_id"],
            first_blood=from_unix_timestamp(float(game_state_data["first_blood"])),
            teams=team_states,
        )


async def process_game_event(event_id: str) -> None:
    """Process a game event."""

    # Fetch the event data from Redis
    redis = await get_redis_connection()
    event_data = await redis.hgetall(f"{settings.redis_game_events_namespace}:event:{event_id}")

    if not event_data:
        logger.warning("Event data not found in Redis for event ID: %s", event_id)
        return

    # Deserialize the event payload data
    if "payload" in event_data:
        try:
            event_data["payload"] = json.loads(event_data["payload"])
        except json.JSONDecodeError as e:
            logger.warning("Error decoding JSON payload: %s", e)
            return
    else:
        logger.warning("Payload not found in event data for event ID: %s", event_id)
        return

    # Deserialize the event data
    try:
        event = GameEvent(**event_data)
    except ValidationError as e:
        logger.error("Failed to deserialize event data: %s", e.errors())
    else:
        logger.debug("Successfully deserialized event data: %s", event)

        # Process the event based on its type
        match event.type_:
            case EVENT_TYPE.MATCH_START:
                await MatchStartProcessor().process_event(event)
            case EVENT_TYPE.MINION_KILL:
                await MinionKillProcessor().process_event(event)
            case EVENT_TYPE.PLAYER_KILL:
                await PlayerKillProcessor().process_event(event)
            case EVENT_TYPE.DRAGON_KILL:
                await DragonKillProcessor().process_event(event)
            case EVENT_TYPE.TURRET_DESTROY:
                await TurretDestroyProcessor().process_event(event)
            case EVENT_TYPE.MATCH_END:
                await MatchEndProcessor().process_event(event)
            case _:
                logger.warning("No processor found for event type: %s", event.type_)
