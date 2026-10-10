import math
import os
import random

import cv2
import numpy as np

from engine.layout import ui_scale
from engine.paths import resolve
from engine.sprites import draw_sprite, get_sprite_size

from .config import (
    CHASER_KIND,
    FALLBACK_LOOK,
    GHOST_OPACITY,
    MIN_REACTION_SECONDS,
    NORMAL_KINDS,
    OBSTACLE_ANGLE_SPREAD_DEG,
    OBSTACLE_EDGE_MARGIN,
    OBSTACLE_RADII,
    OBSTACLE_SPIN_DEG,
    OBSTACLE_SPRITES,
    Z_DODGE_THRESHOLD,
)

_exists_cache = {}


def _sprite_exists(path):
    """Checked once per file."""
    if path not in _exists_cache:
        ok = os.path.exists(resolve(path))
        if not ok:
            print(f"[dodge] Missing sprite '{path}', drawing a plain shape instead.")
        _exists_cache[path] = ok
    return _exists_cache[path]


def _spawn_edge_and_velocity(frame_w, frame_h, radius, speed, margin):
    """Pick an edge and a velocity (px/s) that points INTO the screen.

    Screen y grows downward, so the vertical component is +sin(angle):
      top edge    (base 90)  -> moves down
      bottom edge (base -90) -> moves up
    (The old code used -sin, which made top/bottom spawns fly straight OFF
    the screen and count as free "dodged" points.)
    """
    edge = random.choice(["top", "bottom", "left", "right"])

    if edge == "top":
        x = random.randint(radius, frame_w - radius)
        y = -radius - margin
        base_angle = 90
    elif edge == "bottom":
        x = random.randint(radius, frame_w - radius)
        y = frame_h + radius + margin
        base_angle = -90
    elif edge == "left":
        x = -radius - margin
        y = random.randint(radius, frame_h - radius)
        base_angle = 0
    else:
        x = frame_w + radius + margin
        y = random.randint(radius, frame_h - radius)
        base_angle = 180

    spread = random.uniform(-OBSTACLE_ANGLE_SPREAD_DEG, OBSTACLE_ANGLE_SPREAD_DEG)
    angle = math.radians(base_angle + spread)
    vx = math.cos(angle) * speed
    vy = math.sin(angle) * speed
    return x, y, vx, vy


def spawn_obstacle(frame_w, frame_h, speed, player_xy, homing_chance=0.0, turn_rate=0.0,
                   homing_seconds=0.0, force_homing=False):
    """
    speed: pixels per second.
    player_xy: where the player is now. The spawn point is chosen so the
    obstacle can't reach the player faster than MIN_REACTION_SECONDS
    (best of a few tries), so you are never killed by something that
    appeared on top of you.
    """
    ui = ui_scale(frame_h)
    margin = int(OBSTACLE_EDGE_MARGIN * ui)
    radius = int(random.choice(OBSTACLE_RADII) * ui)

    min_dist = min(speed * MIN_REACTION_SECONDS, 0.6 * frame_h)
    best = None
    best_dist = -1.0
    for _ in range(8):
        cand = _spawn_edge_and_velocity(frame_w, frame_h, radius, speed, margin)
        dist = math.hypot(cand[0] - player_xy[0], cand[1] - player_xy[1])
        if dist > best_dist:
            best, best_dist = cand, dist
        if dist >= min_dist:
            break
    x, y, vx, vy = best

    homing = force_homing or random.random() < homing_chance
    kind = CHASER_KIND if homing else random.choice(NORMAL_KINDS)
    shape, color = FALLBACK_LOOK[kind]
    spin = random.uniform(*OBSTACLE_SPIN_DEG[kind]) * random.choice((-1, 1))
    return {
        "x": x,
        "y": y,
        "vx": vx,
        "vy": vy,
        "speed": speed,
        "radius": radius,
        "z": random.random(),
        "kind": kind,
        "shape": shape,
        "color": color,
        "angle": random.uniform(0, 360),
        "spin": spin,
        "homing": homing,
        "turn_rate": turn_rate if homing else 0.0,
        "home_left": homing_seconds if homing else 0.0,
        "seen": False,   # has it been on screen yet? (only then does it count as dodged)
    }


def _steer_toward(obs, target_x, target_y, dt):
    dx = target_x - obs["x"]
    dy = target_y - obs["y"]
    dist = math.hypot(dx, dy)
    if dist < 1:
        return
    desired_vx = dx / dist * obs["speed"]
    desired_vy = dy / dist * obs["speed"]
    blend = 1.0 - math.exp(-obs["turn_rate"] * dt)   # frame-rate independent
    obs["vx"] += (desired_vx - obs["vx"]) * blend
    obs["vy"] += (desired_vy - obs["vy"]) * blend


def update_obstacles(obstacles, frame_w, frame_h, target_x, target_y, dt):
    """Move obstacles by dt seconds. Returns how many were dodged (left the
    screen after having been on it)."""
    ui = ui_scale(frame_h)
    margin = OBSTACLE_EDGE_MARGIN * ui * 3
    dodged = 0
    survivors = []
    for obs in obstacles:
        if obs["homing"] and obs["home_left"] > 0:
            _steer_toward(obs, target_x, target_y, dt)
            obs["home_left"] -= dt
        obs["x"] += obs["vx"] * dt
        obs["y"] += obs["vy"] * dt
        obs["angle"] = (obs["angle"] + obs["spin"] * dt) % 360

        r = obs["radius"]
        if 0 <= obs["x"] <= frame_w and 0 <= obs["y"] <= frame_h:
            obs["seen"] = True

        gone = (obs["x"] < -r - margin or obs["x"] > frame_w + r + margin
                or obs["y"] < -r - margin or obs["y"] > frame_h + r + margin)
        if gone:
            if obs["seen"]:
                dodged += 1
        else:
            survivors.append(obs)
    obstacles[:] = survivors
    return dodged


def is_dangerous(obs, player_z):
    return abs(obs["z"] - player_z) <= Z_DODGE_THRESHOLD


def _draw_fallback(frame, obs, danger, chasing, ui):
    x, y, r = int(obs["x"]), int(obs["y"]), obs["radius"]
    color = obs["color"]
    thick = max(1, int(round(2 * ui)))
    outline = (0, 0, 255) if chasing else ((0, 0, 0) if danger else color)

    if obs["shape"] == "circle":
        if danger:
            cv2.circle(frame, (x, y), r, color, -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), r, outline, thick, cv2.LINE_AA)
    elif obs["shape"] == "square":
        if danger:
            cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), color, -1)
        cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), outline, thick, cv2.LINE_AA)
    else:
        pts = np.array([(x, y - r), (x - r, y + r), (x + r, y + r)], dtype=np.int32)
        if danger:
            cv2.fillPoly(frame, [pts], color)
        cv2.polylines(frame, [pts], True, outline, thick, cv2.LINE_AA)


def draw_obstacle(frame, obs, player_z, ui=1.0):
    """Solid = can hurt you right now (same depth as you). Faded = at a
    different depth, passes through you safely. A red ring = still chasing."""
    x, y, r = int(obs["x"]), int(obs["y"]), obs["radius"]
    danger = is_dangerous(obs, player_z)
    chasing = obs["homing"] and obs["home_left"] > 0

    path = OBSTACLE_SPRITES[obs["kind"]]
    if _sprite_exists(path):
        native = get_sprite_size(path)[0]
        draw_sprite(frame, path, x, y, scale=round(2 * r / native, 2), angle=obs["angle"],
                    opacity=1.0 if danger else GHOST_OPACITY)
        if chasing:
            # bright ring only while it can actually hurt you; dim when ghosted
            ring = max(1, int(round((3 if danger else 1) * ui)))
            ring_color = (0, 0, 255) if danger else (70, 70, 170)
            cv2.circle(frame, (x, y), r + int(4 * ui), ring_color, ring, cv2.LINE_AA)
    else:
        _draw_fallback(frame, obs, danger, chasing, ui)