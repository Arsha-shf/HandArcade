"""
games/fruit_slice/spawner.py

Decides when and where new fruit are launched, and ramps up difficulty
(spawn rate) the longer the round goes on.
"""

import random

from .fruit import Fruit

SPAWN_INTERVAL_START = 1.1   # seconds between spawns at game start
SPAWN_INTERVAL_MIN = 0.45    # fastest spawn rate as difficulty ramps up
DIFFICULTY_RAMP_TIME = 45.0  # seconds to reach fastest spawn rate


def spawn_fruit(frame_w, frame_h):
    x = random.uniform(frame_w * 0.15, frame_w * 0.85)
    y = frame_h + 40  # start just below the visible frame, arc up into view
    vx = random.uniform(-150, 150)
    vy = random.uniform(-1150, -850)  # strong upward launch, gravity brings it back down
    return Fruit(x, y, vx, vy, frame_w, frame_h)


def next_spawn_interval(elapsed_seconds):
    """Linearly ramps from SPAWN_INTERVAL_START down to SPAWN_INTERVAL_MIN, then jittered."""
    t = min(elapsed_seconds / DIFFICULTY_RAMP_TIME, 1.0)
    base = SPAWN_INTERVAL_START + (SPAWN_INTERVAL_MIN - SPAWN_INTERVAL_START) * t
    return base * random.uniform(0.7, 1.3)