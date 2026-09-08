from .config import DIFFICULTY_PRESETS, DIFFICULTY_RAMP_EVERY_FRAMES


def get_difficulty(frame_count, level):
    preset = DIFFICULTY_PRESETS[level]
    ramps = frame_count // DIFFICULTY_RAMP_EVERY_FRAMES
    spawn_interval = max(
        preset["spawn_interval_min"],
        preset["spawn_interval_start"] - ramps * preset["spawn_ramp_step"],
    )
    speed = min(
        preset["speed_max"],
        preset["speed_start"] + ramps * preset["speed_ramp_step"],
    )
    return spawn_interval, speed