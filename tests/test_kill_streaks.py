"""Tests module for kill streaks."""

import pytest

from app.game_state.utils import calculate_kill_streaks


@pytest.mark.asyncio(scope="session")
@pytest.mark.parametrize(
    "scenario_runner",
    [
        ("scenario1", "game_1"),
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    "expected_kill_streaks",
    [
        (
            ("team_1", "player_1", ["Double Kill at 2024-01-01 12:01:05"]),
            ("team_1", "player_2", ["Triple Kill at 2024-01-01 12:01:18"]),
            ("team_2", "player_3", ["Quadra Kill at 2024-01-01 12:04:01"]),
            ("team_2", "player_4", ["Double Kill at 2024-01-01 12:01:45", "Penta Kill at 2024-01-01 12:10:32"]),
        )
    ],
)
async def test_calculate_kill_streaks_end_to_end(scenario_runner, expected_kill_streaks):
    """Test the calculation of kill streaks in an end-to-end scenario."""

    game_state = await scenario_runner()

    for team_id, player_id, expected_kill_streak in expected_kill_streaks:
        actual_streaks = game_state["teams"][team_id]["players"][player_id]["kill_streaks"]
        assert actual_streaks == expected_kill_streak


@pytest.mark.parametrize(
    "kill_timestamps, streak_window, expected_streaks",
    [
        pytest.param([1, 2], 2, ["Double Kill at 1970-01-01 00:00:02"], id="double_kill"),
        pytest.param([1, 2, 3], 2, ["Triple Kill at 1970-01-01 00:00:03"], id="triple_kill"),
        pytest.param([1, 2, 3, 4], 2, ["Quadra Kill at 1970-01-01 00:00:04"], id="quadra_kill"),
        pytest.param([1, 2, 3, 4, 5], 2, ["Penta Kill at 1970-01-01 00:00:05"], id="penta_kill"),
        pytest.param([1, 4], 2, [], id="no_streak_far_apart"),
        pytest.param([1, 3, 5], 1, [], id="no_streak_large_window"),
        pytest.param(
            [1, 2, 5, 6],
            2,
            ["Double Kill at 1970-01-01 00:00:02", "Double Kill at 1970-01-01 00:00:06"],
            id="two_double_kills",
        ),
        pytest.param([1, 2, 3, 4, 5], 1, ["Penta Kill at 1970-01-01 00:00:05"], id="penta_kill_small_window"),
        pytest.param(
            [1, 2, 3, 5, 6, 7],
            1,
            ["Triple Kill at 1970-01-01 00:00:03", "Triple Kill at 1970-01-01 00:00:07"],
            id="two_triple_kills",
        ),
        pytest.param([], 5, [], id="empty_timestamps"),
        pytest.param([1], 5, [], id="single_kill_no_streak"),
        pytest.param([1, 6, 11, 16, 21], 4, [], id="kills_outside_window"),
        pytest.param(
            [1640995200, 1640995201, 1640995202],
            2,
            ["Triple Kill at 2022-01-01 00:00:02"],
            id="triple_kill_real_timestamp",
        ),
        pytest.param([5, 6, 7, 8], 2, ["Quadra Kill at 1970-01-01 00:00:08"], id="quadra_kill_continuous"),
        pytest.param([10, 11, 12, 13, 14], 1, ["Penta Kill at 1970-01-01 00:00:14"], id="penta_kill_continuous"),
        pytest.param([20, 21, 24, 25], 3, ["Quadra Kill at 1970-01-01 00:00:25"], id="quadra_kill_with_gap"),
        pytest.param([30, 31, 32, 34, 35, 37], 2, ["Penta Kill at 1970-01-01 00:00:35"], id="penta_kill_with_gap"),
        pytest.param([60, 61, 62, 63, 64, 66], 2, ["Penta Kill at 1970-01-01 00:01:04"], id="penta_kill_with_gap_end"),
        pytest.param([90, 91, 92, 93], 1, ["Quadra Kill at 1970-01-01 00:01:33"], id="quadra_kill_small_window"),
    ],
)
def test_calculate_kill_streaks(kill_timestamps, streak_window, expected_streaks):
    actual_streaks = calculate_kill_streaks(kill_timestamps, streak_window)
    assert actual_streaks == expected_streaks
