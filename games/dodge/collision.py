"""
games/dodge/collision.py

One job: is the player touching an obstacle right now.
"""

from .config import HITBOX_FORGIVENESS, PLAYER_RADIUS


def check_collision(player, obstacles):
    px, py = player["x"], player["y"]
    for obs in obstacles:
        dist = ((px - obs["x"]) ** 2 + (py - obs["y"]) ** 2) ** 0.5
        min_dist = (PLAYER_RADIUS + obs["radius"]) * HITBOX_FORGIVENESS
        if dist < min_dist:
            return True
    return False