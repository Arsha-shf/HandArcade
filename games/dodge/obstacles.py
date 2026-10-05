import math
import random

import cv2
import numpy as np

from engine.layout import ui_scale

from .config import (
    MIN_REACTION_SECONDS,
    OBSTACLE_ANGLE_SPREAD_DEG,
    OBSTACLE_COLORS,
    OBSTACLE_EDGE_MARGIN,
    OBSTACLE_RADIUS_MAX,
    OBSTACLE_RADIUS_MIN,
    OBSTACLE_SHAPES,
    Z_DODGE_THRESHOLD,
)


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
    radius = random.randint(int(OBSTACLE_RADIUS_MIN * ui), int(OBSTACLE_RADIUS_MAX * ui))

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
    return {
        "x": x,
        "y": y,
        "vx": vx,
        "vy": vy,
        "speed": speed,
        "radius": radius,
        "z": random.random(),
        "shape": random.choice(OBSTACLE_SHAPES),
        "color": random.choice(OBSTACLE_COLORS),
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


def draw_obstacle(frame, obs, player_z, ui=1.0):
    """Solid + thick outline = can hurt you right now (same depth as you).
    Hollow outline = at a different depth, passes through you safely.
    Red outline = still chasing you."""
    x, y, r = int(obs["x"]), int(obs["y"]), obs["radius"]
    chasing = obs["homing"] and obs["home_left"] > 0
    color = obs["color"]
    thin = max(1, int(round(2 * ui)))

    if is_dangerous(obs, player_z):
        fade = 0.5 + 0.5 * obs["z"]
        fill = tuple(int(c * fade) for c in color)
        outline = (0, 0, 255) if chasing else (0, 0, 0)
        thick = max(1, int(round((3 if chasing else 2) * ui)))
    else:
        fill = None
        outline = (60, 60, 200) if chasing else color
        thick = thin

    if obs["shape"] == "circle":
        if fill:
            cv2.circle(frame, (x, y), r, fill, -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), r, outline, thick, cv2.LINE_AA)
    elif obs["shape"] == "square":
        if fill:
            cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), fill, -1)
        cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), outline, thick, cv2.LINE_AA)
    else:
        pts = np.array([(x, y - r), (x - r, y + r), (x + r, y + r)], dtype=np.int32)
        if fill:
            cv2.fillPoly(frame, [pts], fill)
        cv2.polylines(frame, [pts], True, outline, thick, cv2.LINE_AA)