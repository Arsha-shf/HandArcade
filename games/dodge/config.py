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

OBSTACLE_SPRITES = {
    "asteroid": "assets/dodge/asteroid.png",
    "meteor": "assets/dodge/meteor.png",
    "crystal": "assets/dodge/crystal.png",
    "mine": "assets/dodge/mine.png",
}
NORMAL_KINDS = ("asteroid", "meteor", "crystal")
CHASER_KIND = "mine"

FALLBACK_LOOK = {
    "asteroid": ("circle", (110, 120, 130)),
    "meteor": ("circle", (40, 110, 230)),
    "crystal": ("triangle", (200, 90, 170)),
    "mine": ("square", (60, 60, 230)),
}

OBSTACLE_RADII = (12, 15, 19, 24, 30, 37, 45, 55)

OBSTACLE_SPIN_DEG = {
    "asteroid": (25, 70),
    "meteor": (20, 60),
    "crystal": (40, 110),
    "mine": (15, 45),
}

GHOST_OPACITY = 0.3
OBSTACLE_EDGE_MARGIN = 10
OBSTACLE_ANGLE_SPREAD_DEG = 35

GRACE_SECONDS = 1.5
HAND_LOST_PAUSE_SECONDS = 0.4
MIN_REACTION_SECONDS = 0.45
SWARM_WARNING_SECONDS = 1.2

""" Difficulty:
 Everything is TIME based and RESOLUTION independent. Each (start, end) pair is 
 blended along an eased curve over `ramp_seconds`, then holds at `end`.
   spawn_interval : seconds between spawns
   speed          : screen-heights per second (1.0 = crosses the screen in 1s)
   homing_chance  : chance a normal obstacle is a chaser
   turn_rate      : how sharply chasers steer (per second)
   homing_seconds : chasers give up after this long and fly straight, so they can always be outlasted
   max_active     : cap on obstacles on screen (stops flooding)
   swarm_every    : seconds between swarms (0 = none); swarm_size obstacles
 """

DIFFICULTY_PRESETS = {
    "easy": {
        "ramp_seconds": 90,
        "spawn_interval": (1.8, 0.95),
        "speed": (0.34, 0.72),
        "homing_chance": (0.0, 0.0),
        "turn_rate": (0.0, 0.0),
        "homing_seconds": 0.0,
        "max_active": 6,
        "swarm_every": 0,
        "swarm_size": 0,
    },
    "mid": {
        "ramp_seconds": 75,
        "spawn_interval": (1.3, 0.6),
        "speed": (0.42, 0.95),
        "homing_chance": (0.25, 0.6),
        "turn_rate": (1.0, 2.2),
        "homing_seconds": 2.5,
        "max_active": 9,
        "swarm_every": 16,
        "swarm_size": 3,
    },
    "hard": {
        "ramp_seconds": 60,
        "spawn_interval": (0.9, 0.38),
        "speed": (0.62, 1.25),
        "homing_chance": (0.5, 0.9),
        "turn_rate": (1.8, 3.5),
        "homing_seconds": 3.5,
        "max_active": 13,
        "swarm_every": 10,
        "swarm_size": 4,
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
    "Hard mode noticed you. That's all it needed.",
    "It was hunting you. It won.",
    "The swarm sends its regards.",
    "Respect for even trying hard mode.",
    "Congrats, you survived longer than most.",
]