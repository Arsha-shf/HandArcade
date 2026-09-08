WINDOW_NAME = "HandArcade"

PLAYER_RADIUS_MIN = 22
PLAYER_RADIUS_MAX = 42
PLAYER_Y_MARGIN_TOP = 70
PLAYER_Y_MARGIN_BOTTOM = 40
PLAYER_SMOOTHING_ALPHA = 0.5
HITBOX_FORGIVENESS = 0.78

HAND_SPAN_MIN = 60
HAND_SPAN_MAX = 260

Z_DODGE_THRESHOLD = 0.38

OBSTACLE_RADIUS_MIN = 12
OBSTACLE_RADIUS_MAX = 55
OBSTACLE_SHAPES = ["circle", "square", "triangle"]
OBSTACLE_COLORS = [
    (60, 60, 230),
    (60, 200, 230),
    (230, 120, 60),
    (180, 60, 200),
]
OBSTACLE_EDGE_MARGIN = 10
OBSTACLE_ANGLE_SPREAD_DEG = 35

DIFFICULTY_RAMP_EVERY_FRAMES = 210

DIFFICULTY_PRESETS = {
    "easy": {
        "spawn_interval_start": 55,
        "spawn_interval_min": 26,
        "spawn_ramp_step": 2,
        "speed_start": 7,
        "speed_max": 18,
        "speed_ramp_step": 1,
        "homing_chance_start": 0.0,
        "homing_chance_max": 0.0,
        "homing_ramp_step": 0.0,
        "turn_rate_start": 0.0,
        "turn_rate_max": 0.0,
        "turn_rate_ramp_step": 0.0,
        "swarm_interval_frames": 0,
        "swarm_size": 0,
    },
    "mid": {
        "spawn_interval_start": 36,
        "spawn_interval_min": 13,
        "spawn_ramp_step": 3,
        "speed_start": 10,
        "speed_max": 26,
        "speed_ramp_step": 2,
        "homing_chance_start": 0.30,
        "homing_chance_max": 0.65,
        "homing_ramp_step": 0.04,
        "turn_rate_start": 0.020,
        "turn_rate_max": 0.050,
        "turn_rate_ramp_step": 0.003,
        "swarm_interval_frames": 420,
        "swarm_size": 3,
    },
    "hard": {
        "spawn_interval_start": 20,
        "spawn_interval_min": 7,
        "spawn_ramp_step": 4,
        "speed_start": 16,
        "speed_max": 70,
        "speed_ramp_step": 4,
        "homing_chance_start": 0.60,
        "homing_chance_max": 1.0,
        "homing_ramp_step": 0.06,
        "turn_rate_start": 0.045,
        "turn_rate_max": 0.110,
        "turn_rate_ramp_step": 0.007,
        "swarm_interval_frames": 180,
        "swarm_size": 5,
    },
}

GAME_OVER_LINES = [
    "RIP. You dodged like a rock.",
    "Skill issue detected.",
    "Bro walked straight into it.",
    "Your hand betrayed you.",
    "F to pay respects.",
    "That box had your name on it.",
    "Physics 1, You 0.",
]

HARD_MODE_TAUNTS = [
    "Yeah, nobody clears this. Nice try.",
    "It was hunting you. It won.",
    "You didn't lose. Hard mode just does this.",
    "The swarm sends its regards.",
    "This mode isn't beatable. You just stall it.",
    "Congrats, you survived longer than most.",
]