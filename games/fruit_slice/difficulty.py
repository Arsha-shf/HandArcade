"""
games/fruit_slice/difficulty.py

Difficulty presets: spawn timing, concurrent-fruit cap, launch-speed
multiplier, and the mix of edges fruit spawn from. Passed as a dict into
spawner.spawn_fruit / next_spawn_interval so all difficulties share the
same spawn function.
"""

DIFFICULTY_SETTINGS = {
    "easy": {
        "spawn_interval_start": 1.4,
        "spawn_interval_min": 0.75,
        "ramp_time": 50.0,
        "max_simultaneous": 2,
        "speed_mult": 0.85,
        "edge_weights": {"bottom": 0.7, "left": 0.15, "right": 0.15, "top": 0.0},
    },
    "medium": {
        "spawn_interval_start": 1.1,
        "spawn_interval_min": 0.45,
        "ramp_time": 45.0,
        "max_simultaneous": 3,
        "speed_mult": 1.0,
        "edge_weights": {"bottom": 0.5, "left": 0.2, "right": 0.2, "top": 0.1},
    },
    "hard": {
        "spawn_interval_start": 0.7,
        "spawn_interval_min": 0.25,
        "ramp_time": 35.0,
        "max_simultaneous": 5,
        "speed_mult": 1.25,
        "edge_weights": {"bottom": 0.35, "left": 0.25, "right": 0.25, "top": 0.15},
    },
}