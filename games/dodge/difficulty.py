"""
games/dodge/difficulty.py

Turns elapsed frame count into "how hard is it right now": spawn rate
and fall speed both ramp up, both capped so it doesn't become
unplayable RNG at the high end.
"""

from .config import (
    DIFFICULTY_RAMP_EVERY_FRAMES,
    OBSTACLE_SPAWN_INTERVAL_MIN,
    OBSTACLE_SPAWN_INTERVAL_START,
    OBSTACLE_SPEED_MAX,
    OBSTACLE_SPEED_START,
)


def get_difficulty(frame_count):
    ramps = frame_count // DIFFICULTY_RAMP_EVERY_FRAMES
    spawn_interval = max(OBSTACLE_SPAWN_INTERVAL_MIN,
                          OBSTACLE_SPAWN_INTERVAL_START - ramps * 3)
    speed = min(OBSTACLE_SPEED_MAX, OBSTACLE_SPEED_START + ramps)
    return spawn_interval, speed