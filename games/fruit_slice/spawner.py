"""
games/fruit_slice/spawner.py

Decides when and where new fruit are launched. Spawn rate and origin mix
come from a difficulty settings dict (see difficulty.py) passed in from
game.py, so all three difficulties share this one spawn function instead
of each needing separate spawn logic.
"""

import random

from .fruit import Fruit


def _pick_edge(edge_weights):
    edges = list(edge_weights.keys())
    weights = list(edge_weights.values())
    return random.choices(edges, weights=weights, k=1)[0]


def spawn_fruit(frame_w, frame_h, settings):
    """
    settings is one entry from difficulty.DIFFICULTY_SETTINGS, e.g.
    DIFFICULTY_SETTINGS["hard"]. Picks a spawn edge (bottom/top/left/right)
    according to settings["edge_weights"], then launches the fruit inward
    with velocity scaled by settings["speed_mult"].
    """
    edge = _pick_edge(settings["edge_weights"])
    speed_mult = settings["speed_mult"]

    if edge == "bottom":
        x = random.uniform(frame_w * 0.1, frame_w * 0.9)
        y = frame_h + 40
        vx = random.uniform(-150, 150) * speed_mult
        vy = random.uniform(-1150, -850) * speed_mult

    elif edge == "top":
        x = random.uniform(frame_w * 0.1, frame_w * 0.9)
        y = -40
        vx = random.uniform(-150, 150) * speed_mult
        vy = random.uniform(150, 350) * speed_mult

    elif edge == "left":
        x = -40
        y = random.uniform(frame_h * 0.15, frame_h * 0.85)
        vx = random.uniform(500, 750) * speed_mult
        vy = random.uniform(-500, -200) * speed_mult

    else:  # right
        x = frame_w + 40
        y = random.uniform(frame_h * 0.15, frame_h * 0.85)
        vx = random.uniform(-750, -500) * speed_mult
        vy = random.uniform(-500, -200) * speed_mult

    return Fruit(x, y, vx, vy, frame_w, frame_h)


def next_spawn_interval(elapsed_seconds, settings):
    """Linearly ramps from spawn_interval_start down to spawn_interval_min, then jittered."""
    ramp_time = settings["ramp_time"]
    start = settings["spawn_interval_start"]
    minimum = settings["spawn_interval_min"]
    t = min(elapsed_seconds / ramp_time, 1.0)
    base = start + (minimum - start) * t
    return base * random.uniform(0.7, 1.3)