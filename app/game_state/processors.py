"""Module for processing stored game events."""

import json
from datetime import datetime

from app import settings
from app.connectors.redis import get_redis_connection
from app.game_event.models import (
    DragonKillPayload,
    GameEvent,
    MatchEndPayload,
    MatchStartPayload,
    MinionKillPayload,
    PlayerKillPayload,
    TurretDestroyPayload,
)
from app.game_state.utils import (
    PlayerRegistry,
    add_kill_history,
    calculate_kill_streaks,
    calculate_max_killing_spree,
    get_game_state_key,
    get_player_death_history_key,
    get_player_kill_history_key,
    get_player_state_key,
    get_team_state_key,
)


class GameEventProcessor:
    """Class for processing game events."""

    async def process_event(self, event: GameEvent) -> None:
        """Process a game event."""

        raise NotImplementedError("This method should be implemented in subclasses.")


class MatchStartProcessor(GameEventProcessor):
    """Processor for match start events."""

    async def process_event(self, event: GameEvent) -> None:
        """Process a match start event."""

        payload: MatchStartPayload = event.payload
        match_id = event.match_id
        match_metadata = {
            "match_id": match_id,
            "start_time": payload.fixture.start_time,
            "title": payload.fixture.title,
            "series_current": payload.fixture.series_current,
            "series_max": payload.fixture.series_max,
            "series_type": payload.fixture.series_type,
            "teams": json.dumps(
                [
                    {
                        "team_id": team.team_id,
                        "players": [player.player_id for player in team.players],
                    }
                    for team in payload.teams
                ]
            ),
            "first_blood": -1,
        }
        redis = await get_redis_connection()

        # Store the match metadata in Redis
        redis_key = get_game_state_key(match_id)
        await redis.hset(redis_key, mapping=match_metadata)

        # Store each team's state in Redis
        for team in payload.teams:
            team_key = get_team_state_key(team.team_id, match_id)
            team_metadata = {
                "dragon_kills": 0,
                "tower_kills": 0,
            }
            await redis.hset(team_key, mapping=team_metadata)

        # Store each player's state in Redis
        for team in payload.teams:
            for player in team.players:
                # Register the player in the PlayerRegistry
                PlayerRegistry.register_player(player.player_id, match_id, team.team_id)

                player_key = get_player_state_key(player.player_id)
                player_metadata = {
                    "player_id": player.player_id,
                    "gold": player.gold,
                    "alive": int(player.alive),
                    "name": player.name,
                    "minion_kills": 0,
                    "human_kills": 0,
                    "human_kills_assists": 0,
                    "team_members": json.dumps([p.player_id for p in team.players if p.player_id != player.player_id]),
                }
                await redis.hset(player_key, mapping=player_metadata)


class MinionKillProcessor(GameEventProcessor):
    """Processor for minion kill events."""

    async def process_event(self, event: GameEvent) -> None:
        """Process a minion kill event."""

        # Implement the logic to process minion kill events
        payload: MinionKillPayload = event.payload

        if payload.gold_granted is None:
            return

        redis = await get_redis_connection()
        player_key = get_player_state_key(payload.player_id)
        # Increment the player's gold and minion kills
        await redis.hincrby(player_key, "gold", payload.gold_granted)
        await redis.hincrby(player_key, "minion_kills", 1)
        # Add event timestamp to the player's kill history
        player_kill_history_key = get_player_kill_history_key(payload.player_id)
        timestamp = datetime.fromisoformat(event.timestamp).timestamp()
        await add_kill_history(player_kill_history_key, timestamp, kill_type="minion")


class PlayerKillProcessor(GameEventProcessor):
    """Processor for player kill events."""

    async def process_event(self, event: GameEvent) -> None:
        """Process a player kill event."""

        payload: PlayerKillPayload = event.payload
        redis = await get_redis_connection()

        killer_id = payload.killer_id

        if killer_id is not None:
            # Increment the killer's gold, human kills, and add event timestamp to the kill history
            killer_state_key = get_player_state_key(killer_id)

            if payload.gold_granted is not None:
                await redis.hincrby(killer_state_key, "gold", payload.gold_granted)

            await redis.hincrby(killer_state_key, "human_kills", 1)

            # Add event timestamp to the killer's kill history
            killer_kill_history_key = get_player_kill_history_key(killer_id)
            if event.timestamp is not None:
                timestamp = datetime.fromisoformat(event.timestamp).timestamp()
                await add_kill_history(killer_kill_history_key, timestamp, kill_type="human")

        # Update assistants' gold and human kills
        if payload.assistants is not None:
            for assistant_id in payload.assistants:
                assistant_state_key = get_player_state_key(assistant_id)
                await redis.hincrby(assistant_state_key, "gold", payload.assist_gold)
                await redis.hincrby(assistant_state_key, "human_kills_assists", 1)

        # Update the victim's death history
        if payload.victim_id is not None and event.timestamp is not None:
            victim_death_history_key = get_player_death_history_key(payload.victim_id)
            timestamp = datetime.fromisoformat(event.timestamp).timestamp()
            await redis.zadd(victim_death_history_key, {timestamp: timestamp})

        # Update the match's first blood timestamp
        if event.timestamp is not None:
            if payload.killer_id is None and payload.victim_id is None:
                return

            timestamp = datetime.fromisoformat(event.timestamp).timestamp()
            match_id = PlayerRegistry.get_match_id_for_player(killer_id or payload.victim_id)
            match_state_key = get_game_state_key(match_id)
            first_blood = await redis.hget(match_state_key, "first_blood")

            if first_blood == "-1":
                await redis.hset(match_state_key, "first_blood", timestamp)
            elif timestamp < float(first_blood):
                await redis.hset(match_state_key, "first_blood", timestamp)


class DragonKillProcessor(GameEventProcessor):
    """Processor for dragon kill events."""

    async def process_event(self, event: GameEvent) -> None:
        """Process a dragon kill event."""

        payload: DragonKillPayload = event.payload
        redis = await get_redis_connection()

        if payload.gold_granted is None or payload.killer_id is None:
            return

        killer_id = payload.killer_id

        # Increment the killer's gold
        killer_state_key = get_player_state_key(killer_id)
        await redis.hincrby(killer_state_key, "gold", payload.gold_granted)

        # Add event timestamp to the killer's kill history
        killer_kill_history_key = get_player_kill_history_key(killer_id)

        if event.timestamp is not None:
            timestamp = datetime.fromisoformat(event.timestamp).timestamp()
            await add_kill_history(killer_kill_history_key, timestamp, kill_type="dragon")

        # Increment the team's dragon kills
        team_id = PlayerRegistry.get_team_id(killer_id)
        team_state_key = get_team_state_key(team_id)
        await redis.hincrby(team_state_key, "dragon_kills", 1)


class TurretDestroyProcessor(GameEventProcessor):
    """Processor for turret destroy events."""

    async def process_event(self, event: GameEvent) -> None:
        """Process a turret destroy event."""

        payload: TurretDestroyPayload = event.payload
        redis = await get_redis_connection()

        # Increment the team's tower kills
        if payload.killer_id is not None:
            team_state_key = get_team_state_key(payload.killer_team_id)
            await redis.hincrby(team_state_key, "tower_kills", 1)

            # Increment the killer's and teammates' gold
            killer_id = payload.killer_id
            player_ids = PlayerRegistry.players_for_team(payload.killer_team_id)

            for player_id in player_ids:
                if player_id == killer_id:
                    gold_granted = payload.player_gold_granted

                    if gold_granted is not None:
                        player_state_key = get_player_state_key(player_id)
                        await redis.hincrby(player_state_key, "gold", gold_granted)
                else:
                    gold_granted = payload.team_gold_granted

                    if gold_granted is not None:
                        player_state_key = get_player_state_key(player_id)
                        await redis.hincrby(player_state_key, "gold", gold_granted)


class MatchEndProcessor(GameEventProcessor):
    """Processor for match end event."""

    async def process_event(self, event: GameEvent) -> None:
        """Process a match end event."""

        payload: MatchEndPayload = event.payload
        redis = await get_redis_connection()

        # Update the match state with the winning team ID
        match_id = event.match_id
        match_state_key = get_game_state_key(match_id)
        await redis.hset(match_state_key, "winning_team_id", payload.winning_team_id)

        # Update player states with killing streaks
        await self.calculate_kill_streaks(match_id)
        # Update player states with max killing sprees
        await self.calculate_max_killing_sprees(match_id)

    async def calculate_kill_streaks(self, match_id: str) -> None:
        """Calculate kill streaks for players in the match."""

        redis = await get_redis_connection()
        all_players = PlayerRegistry.players_for_match(match_id)

        for player_id in all_players:
            player_kill_history_key = get_player_kill_history_key(player_id)
            kill_history = [json.loads(h) for h in await redis.zrange(player_kill_history_key, 0, -1)]
            kill_timestamps = [h["timestamp"] for h in kill_history]
            kill_streaks = calculate_kill_streaks(kill_timestamps, settings.kill_streak_time_window)

            # Store the kill streaks in Redis
            player_state_key = get_player_state_key(player_id)
            await redis.hset(player_state_key, "kill_streaks", json.dumps(kill_streaks))

    async def calculate_max_killing_sprees(self, match_id: str) -> None:
        """Calculate max killing sprees for players in the match."""

        redis = await get_redis_connection()
        all_players = PlayerRegistry.players_for_match(match_id)

        for player_id in all_players:
            player_kill_history_key = get_player_kill_history_key(player_id)
            player_death_history_key = get_player_death_history_key(player_id)
            kill_history = [json.loads(h) for h in await redis.zrange(player_kill_history_key, 0, -1)]
            death_history = [float(ts) for ts in await redis.zrange(player_death_history_key, 0, -1)]
            max_killing_spree = calculate_max_killing_spree(kill_history, death_history)

            # Store the max killing spree in Redis
            player_state_key = get_player_state_key(player_id)
            await redis.hset(player_state_key, "max_killing_spree", max_killing_spree)
