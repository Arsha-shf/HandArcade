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
        "spawn_interval_min": 24,
        "spawn_ramp_step": 2,
        "speed_start": 7,
        "speed_max": 20,
        "speed_ramp_step": 1,
    },
    "mid": {
        "spawn_interval_start": 38,
        "spawn_interval_min": 14,
        "spawn_ramp_step": 3,
        "speed_start": 10,
        "speed_max": 28,
        "speed_ramp_step": 2,
    },
    "hard": {
        "spawn_interval_start": 24,
        "spawn_interval_min": 8,
        "spawn_ramp_step": 4,
        "speed_start": 14,
        "speed_max": 38,
        "speed_ramp_step": 3,
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