from .config import HITBOX_FORGIVENESS, Z_DODGE_THRESHOLD
from .player import player_radius


def check_collision(player, obstacles):
    px, py, pz = player["x"], player["y"], player["z"]
    pr = player_radius(pz)
    for obs in obstacles:
        dz = abs(pz - obs["z"])
        if dz > Z_DODGE_THRESHOLD:
            continue
        dist = ((px - obs["x"]) ** 2 + (py - obs["y"]) ** 2) ** 0.5
        min_dist = (pr + obs["radius"]) * HITBOX_FORGIVENESS
        if dist < min_dist:
            return True
    return False