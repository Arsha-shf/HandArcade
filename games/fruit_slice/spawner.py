"""
games/fruit_slice/spawner.py

Decides when and where new fruit are launched, and ramps up difficulty
(spawn rate) the longer the round goes on. Difficulty also controls how
aggressive the ramp is, how likely bombs are, how fast fruit move, and
whether fruit can enter from the sides as well as the bottom.
"""

import random

from .fruit import Fruit

DIFFICULTY_CONFIG = {
    "easy": {
        "spawn_interval_start": 1.3,
        "spawn_interval_min": 0.75,
        "ramp_time": 60.0,
        "bomb_chance": 0.08,
        "speed_mult": 0.85,
        "side_spawn_chance": 0.15,
    },
    "medium": {
        "spawn_interval_start": 1.1,
        "spawn_interval_min": 0.45,
        "ramp_time": 45.0,
        "bomb_chance": 0.15,
        "speed_mult": 1.0,
        "side_spawn_chance": 0.30,
    },
    "hard": {
        "spawn_interval_start": 0.75,
        "spawn_interval_min": 0.28,
        "ramp_time": 30.0,
        "bomb_chance": 0.22,
        "speed_mult": 1.25,
        "side_spawn_chance": 0.45,
    },
}


def _config(difficulty):
    return DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["medium"])


def spawn_fruit(frame_w, frame_h, difficulty="medium"):
    cfg = _config(difficulty)
    speed_mult = cfg["speed_mult"]

    if random.random() < cfg["side_spawn_chance"]:
        edge = random.choice(["left", "right"])
    else:
        edge = "bottom"

    if edge == "bottom":
        x = random.uniform(frame_w * 0.15, frame_w * 0.85)
        y = frame_h + 40
        vx = random.uniform(-150, 150) * speed_mult
        vy = random.uniform(-1150, -850) * speed_mult
    elif edge == "left":
        x = -40
        y = random.uniform(frame_h * 0.25, frame_h * 0.75)
        vx = random.uniform(500, 800) * speed_mult
        vy = random.uniform(-750, -450) * speed_mult
    else:
        x = frame_w + 40
        y = random.uniform(frame_h * 0.25, frame_h * 0.75)
        vx = random.uniform(-800, -500) * speed_mult
        vy = random.uniform(-750, -450) * speed_mult

    return Fruit(x, y, vx, vy, frame_w, frame_h, bomb_chance=cfg["bomb_chance"])


def next_spawn_interval(elapsed_seconds, difficulty="medium"):
    """Linearly ramps from start down to min spawn interval, then jittered."""
    cfg = _config(difficulty)
    t = min(elapsed_seconds / cfg["ramp_time"], 1.0)
    base = cfg["spawn_interval_start"] + (cfg["spawn_interval_min"] - cfg["spawn_interval_start"]) * t
    return base * random.uniform(0.7, 1.3)