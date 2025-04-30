"""Utility functions for game state management."""

import json
from datetime import UTC, datetime

from app import settings
from app.connectors.redis import get_redis_connection


def to_unix_timestamp(iso_string: str) -> int:
    """Convert an ISO 8601 string to a Unix timestamp."""

    dt = datetime.fromisoformat(iso_string)
    return int(dt.timestamp())


def from_unix_timestamp(timestamp: int) -> str:
    """Convert a Unix timestamp to an ISO 8601 string."""

    dt = datetime.fromtimestamp(timestamp, UTC)
    return dt.isoformat()


def get_game_state_key(match_id: str) -> str:
    """Generate a Redis key for the game state."""

    return f"{settings.redis_game_state_namespace}:game:{match_id}"


def get_team_state_key(team_id: str, match_id: str = None) -> str:
    """Generate a Redis key for the team state."""

    if match_id is None:
        match_id = PlayerRegistry.get_match_id_for_team(team_id)

    if match_id is None:
        raise ValueError(f"Team ID {team_id} not found in registry.")

    return f"{settings.redis_game_state_namespace}:game:{match_id}:team:{team_id}"


def get_player_state_key(player_id: str, match_id: str = None) -> str:
    """Generate a Redis key for the player state."""

    if match_id is None:
        match_id = PlayerRegistry.get_match_id_for_player(player_id)

    if match_id is None:
        raise ValueError(f"Player ID {player_id} not found in registry.")

    return f"{settings.redis_game_state_namespace}:game:{match_id}:player:{player_id}"


def get_player_kill_history_key(player_id: str) -> str:
    """Generate a Redis key for the player's kill history."""

    match_id = PlayerRegistry.get_match_id_for_player(player_id)

    if match_id is None:
        raise ValueError(f"Player ID {player_id} not found in registry.")

    return f"{settings.redis_game_state_namespace}:game:{match_id}:player:{player_id}:kill_history"


def get_player_death_history_key(player_id: str) -> str:
    """Generate a Redis key for the player's death history."""

    match_id = PlayerRegistry.get_match_id_for_player(player_id)

    if match_id is None:
        raise ValueError(f"Player ID {player_id} not found in registry.")

    return f"{settings.redis_game_state_namespace}:game:{match_id}:player:{player_id}:death_history"


class PlayerRegistry:
    """In memory registry for matching players to their current game and team."""

    _matches: dict[str, dict[str, str]] = {}
    _teams: dict[str, str] = {}

    @classmethod
    def register_player(cls, player_id: str, match_id: str, team_id: str) -> None:
        """Register a player with their match and team."""

        cls._matches[player_id] = {"match_id": match_id, "team_id": team_id}
        cls._teams[team_id] = match_id

    @classmethod
    def get_match_id_for_player(cls, player_id: str) -> str:
        """Get the match ID for a player."""

        return cls._matches.get(player_id, {}).get("match_id")

    @classmethod
    def get_match_id_for_team(cls, team_id: str) -> str:
        """Get the match ID for a team."""

        return cls._teams.get(team_id)

    @classmethod
    def get_team_id(cls, player_id: str) -> str:
        """Get the team ID for a player."""

        return cls._matches.get(player_id, {}).get("team_id")

    @classmethod
    def players_for_team(cls, team_id: str) -> list[str]:
        """Get all players for a team."""

        return [player_id for player_id, data in cls._matches.items() if data.get("team_id") == team_id]

    @classmethod
    def players_for_match(cls, match_id: str) -> list[str]:
        """Get all players for a match."""

        return [player_id for player_id, data in cls._matches.items() if data.get("match_id") == match_id]

    @classmethod
    def unregister_player(cls, player_id: str) -> None:
        """Unregister a player."""

        cls._matches.pop(player_id, None)

    @classmethod
    def unregister_team(cls, team_id: str) -> None:
        """Unregister a team."""

        cls._teams.pop(team_id, None)


async def add_kill_history(history_key: str, timestamp: float, kill_type: str) -> None:
    """Add a kill timestamp and type to the player's kill history."""

    redis = await get_redis_connection()
    member_data = {"timestamp": timestamp, "kill_type": kill_type}
    member = json.dumps(member_data)
    await redis.zadd(history_key, {member: timestamp})


def calculate_kill_streaks(kill_timestamps: list[float], streak_window: int) -> list[str]:
    """
    Calculates kill streaks (Double, Triple, Quadra, Penta) from a sorted list of timestamps.
    """

    streaks = []
    n = len(kill_timestamps)
    i = 0

    while i < n:
        current_streak = [kill_timestamps[i]]
        j = i + 1

        while j < n and (kill_timestamps[j] - current_streak[-1]) <= streak_window and len(current_streak) < 5:
            current_streak.append(kill_timestamps[j])
            j += 1

        streak_length = len(current_streak)

        if streak_length >= 2:
            last_kill_timestamp = current_streak[-1]
            datetime_object = datetime.fromtimestamp(last_kill_timestamp, UTC)
            formatted_timestamp = datetime_object.strftime("%Y-%m-%d %H:%M:%S")

            if streak_length == 2:
                streaks.append(f"Double Kill at {formatted_timestamp}")
            elif streak_length == 3:
                streaks.append(f"Triple Kill at {formatted_timestamp}")
            elif streak_length == 4:
                streaks.append(f"Quadra Kill at {formatted_timestamp}")
            elif streak_length == 5:
                streaks.append(f"Penta Kill at {formatted_timestamp}")

        i = j

    return streaks


def calculate_max_killing_spree(kill_history: list[dict], death_history: list[float]) -> int:
    """
    Calculates the maximum killing spree for a player, given their kill and death history.
    """

    human_kills = [kill["timestamp"] for kill in kill_history if kill["kill_type"] == "human"]

    streak = 0
    max_streak = 0
    death_index = 0
    num_deaths = len(death_history)

    for kill in human_kills:
        # Move to the next death if current kill is after it
        while death_index < num_deaths and kill >= death_history[death_index]:
            max_streak = max(max_streak, streak)
            streak = 0
            death_index += 1

        if death_index < num_deaths:
            streak += 1

    # In case there are kills after the last death
    max_streak = max(max_streak, streak)

    return max_streak


def max_killing_spree_label(max_killing_spree: int) -> str | None:
    """Returns a label for the maximum."""

    if max_killing_spree > 7:
        max_killing_spree = 7

    label_map = {
        3: "Killing Spree",
        4: "Rampage",
        5: "Unstoppable",
        6: "Dominating",
        7: "Godlike",
    }

    return label_map.get(max_killing_spree)
