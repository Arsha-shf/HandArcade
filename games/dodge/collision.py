import math

from .config import HITBOX_FORGIVENESS, Z_DODGE_THRESHOLD
from .player import player_radius


def check_collision(player, obstacles):
    """True if the player overlaps an obstacle at (roughly) the same depth."""
    px, py, pz = player["x"], player["y"], player["z"]
    pr = player_radius(pz, player["ui"])
    for obs in obstacles:
        if abs(pz - obs["z"]) > Z_DODGE_THRESHOLD:
            continue
        dist = math.hypot(px - obs["x"], py - obs["y"])
        if dist < (pr + obs["radius"]) * HITBOX_FORGIVENESS:
            return True
    return False