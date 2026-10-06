"""
games/fruit_slice/difficulty.py

Difficulty presets. Each (start, end) pair is blended along an eased curve
over `ramp_seconds`, then holds at `end` (same idea as Dodge).

  lives            : strikes before game over
  miss_costs_life  : does letting a fruit fall/fly away cost a life?
                     (a sliced bomb ALWAYS costs a life)
  spawn_interval   : seconds between launches
  bomb_chance      : chance each launched object is a bomb (never in the
                     first few seconds, never more than one per burst)
  burst_chance     : chance of adding another fruit to the same launch,
                     up to burst_max fruit per launch
  max_simultaneous : cap on un-sliced objects on screen
  speed_mult       : time scale of the whole flight (1.2 = 20% faster
                     motion, same arc shape, so fruit still tops out on screen)
  edge_weights     : where fruit launch from
"""

DIFFICULTY_SETTINGS = {
    "easy": {
        "lives": 5,
        "miss_costs_life": False,
        "ramp_seconds": 60.0,
        "spawn_interval": (1.4, 0.8),
        "bomb_chance": (0.05, 0.10),
        "burst_chance": (0.0, 0.25),
        "burst_max": 2,
        "max_simultaneous": 3,
        "speed_mult": 0.85,
        "edge_weights": {"bottom": 0.7, "left": 0.15, "right": 0.15, "top": 0.0},
    },
    "medium": {
        "lives": 5,
        "miss_costs_life": True,
        "ramp_seconds": 50.0,
        "spawn_interval": (1.1, 0.5),
        "bomb_chance": (0.10, 0.18),
        "burst_chance": (0.10, 0.40),
        "burst_max": 3,
        "max_simultaneous": 4,
        "speed_mult": 1.0,
        "edge_weights": {"bottom": 0.5, "left": 0.2, "right": 0.2, "top": 0.1},
    },
    "hard": {
        "lives": 3,
        "miss_costs_life": True,
        "ramp_seconds": 40.0,
        "spawn_interval": (0.8, 0.3),
        "bomb_chance": (0.15, 0.28),
        "burst_chance": (0.25, 0.55),
        "burst_max": 4,
        "max_simultaneous": 6,
        "speed_mult": 1.15,
        "edge_weights": {"bottom": 0.35, "left": 0.25, "right": 0.25, "top": 0.15},
    },
}


def _lerp(pair, t):
    a, b = pair
    return a + (b - a) * t


def get_difficulty(elapsed_seconds, level):
    """Parameters in effect `elapsed_seconds` into a round."""
    p = DIFFICULTY_SETTINGS[level]
    x = min(1.0, max(0.0, elapsed_seconds / p["ramp_seconds"]))
    e = 1 - (1 - x) ** 2

    return {
        "lives": p["lives"],
        "miss_costs_life": p["miss_costs_life"],
        "spawn_interval": _lerp(p["spawn_interval"], e),
        "bomb_chance": _lerp(p["bomb_chance"], e),
        "burst_chance": _lerp(p["burst_chance"], e),
        "burst_max": p["burst_max"],
        "max_simultaneous": p["max_simultaneous"],
        "speed_mult": p["speed_mult"],
        "edge_weights": p["edge_weights"],
    }