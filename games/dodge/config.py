"""
games/dodge/config.py

All tunable numbers for Dodge in one place. Change feel/difficulty here,
not by hunting through logic files.
"""

WINDOW_NAME = "HandArcade"

# --- Player ---
PLAYER_RADIUS = 30
PLAYER_Y_OFFSET_FROM_BOTTOM = 90
PLAYER_SMOOTHING_ALPHA = 0.35        # higher = snappier, lower = floatier
HITBOX_FORGIVENESS = 0.78            # < 1.0 = shrink collision so it feels fair

# --- Obstacles ---
OBSTACLE_SPAWN_INTERVAL_START = 45   # frames between spawns at game start
OBSTACLE_SPAWN_INTERVAL_MIN = 14     # never spawn faster than this
OBSTACLE_SPEED_START = 6
OBSTACLE_SPEED_MAX = 22
OBSTACLE_SHAPES = ["circle", "square", "triangle"]
OBSTACLE_COLORS = [
    (60, 60, 230),   # red
    (60, 200, 230),  # orange-yellow
    (230, 120, 60),  # blue-ish
    (180, 60, 200),  # purple
]

# --- Difficulty ramp ---
DIFFICULTY_RAMP_EVERY_FRAMES = 240   # every ~8s at 30fps, things get worse

# --- Game over lines ---
GAME_OVER_LINES = [
    "RIP. You dodged like a rock.",
    "Skill issue detected.",
    "Bro walked straight into it.",
    "Your hand betrayed you.",
    "F to pay respects.",
    "That box had your name on it.",
    "Physics 1, You 0.",
]