from .config import DIFFICULTY_PRESETS


def _lerp(pair, t):
    a, b = pair
    return a + (b - a) * t


def get_difficulty(elapsed_seconds, level):
    """
    Difficulty at `elapsed_seconds` into a run. A smooth, continuous ramp
    (no sudden jumps every few seconds), eased so it gets tough early and
    then levels off at the preset's maximum.

    Returns a dict; `speed` is in screen-heights per second.
    """
    preset = DIFFICULTY_PRESETS[level]
    x = min(1.0, max(0.0, elapsed_seconds / preset["ramp_seconds"]))
    e = 1 - (1 - x) ** 2

    return {
        "progress": e,
        "spawn_interval": _lerp(preset["spawn_interval"], e),
        "speed": _lerp(preset["speed"], e),
        "homing_chance": _lerp(preset["homing_chance"], e),
        "turn_rate": _lerp(preset["turn_rate"], e),
        "homing_seconds": preset["homing_seconds"],
        "max_active": preset["max_active"],
        "swarm_every": preset["swarm_every"],
        "swarm_size": preset["swarm_size"],
    }