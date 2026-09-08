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
    homing_chance = min(
        preset["homing_chance_max"],
        preset["homing_chance_start"] + ramps * preset["homing_ramp_step"],
    )
    turn_rate = min(
        preset["turn_rate_max"],
        preset["turn_rate_start"] + ramps * preset["turn_rate_ramp_step"],
    )

    return {
        "spawn_interval": spawn_interval,
        "speed": speed,
        "homing_chance": homing_chance,
        "turn_rate": turn_rate,
        "swarm_interval_frames": preset["swarm_interval_frames"],
        "swarm_size": preset["swarm_size"],
    }