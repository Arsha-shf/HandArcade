import math
import random

import cv2
import numpy as np

from .config import (
    OBSTACLE_ANGLE_SPREAD_DEG,
    OBSTACLE_COLORS,
    OBSTACLE_EDGE_MARGIN,
    OBSTACLE_RADIUS_MAX,
    OBSTACLE_RADIUS_MIN,
    OBSTACLE_SHAPES,
)


def _spawn_edge_and_velocity(frame_w, frame_h, radius, speed):
    edge = random.choice(["top", "bottom", "left", "right"])

    if edge == "top":
        x = random.randint(radius, frame_w - radius)
        y = -radius - OBSTACLE_EDGE_MARGIN
        base_angle = 90
    elif edge == "bottom":
        x = random.randint(radius, frame_w - radius)
        y = frame_h + radius + OBSTACLE_EDGE_MARGIN
        base_angle = -90
    elif edge == "left":
        x = -radius - OBSTACLE_EDGE_MARGIN
        y = random.randint(radius, frame_h - radius)
        base_angle = 0
    else:
        x = frame_w + radius + OBSTACLE_EDGE_MARGIN
        y = random.randint(radius, frame_h - radius)
        base_angle = 180

    spread = random.uniform(-OBSTACLE_ANGLE_SPREAD_DEG, OBSTACLE_ANGLE_SPREAD_DEG)
    angle = math.radians(base_angle + spread)
    vx = math.cos(angle) * speed
    vy = -math.sin(angle) * speed
    return x, y, vx, vy


def spawn_obstacle(frame_w, frame_h, speed):
    radius = random.randint(OBSTACLE_RADIUS_MIN, OBSTACLE_RADIUS_MAX)
    x, y, vx, vy = _spawn_edge_and_velocity(frame_w, frame_h, radius, speed)
    return {
        "x": x,
        "y": y,
        "vx": vx,
        "vy": vy,
        "radius": radius,
        "z": random.random(),
        "shape": random.choice(OBSTACLE_SHAPES),
        "color": random.choice(OBSTACLE_COLORS),
    }


def update_obstacles(obstacles, frame_w, frame_h):
    dodged = 0
    survivors = []
    for obs in obstacles:
        obs["x"] += obs["vx"]
        obs["y"] += obs["vy"]
        r = obs["radius"]
        off_left = obs["x"] < -r - OBSTACLE_EDGE_MARGIN * 3
        off_right = obs["x"] > frame_w + r + OBSTACLE_EDGE_MARGIN * 3
        off_top = obs["y"] < -r - OBSTACLE_EDGE_MARGIN * 3
        off_bottom = obs["y"] > frame_h + r + OBSTACLE_EDGE_MARGIN * 3
        if off_left or off_right or off_top or off_bottom:
            dodged += 1
        else:
            survivors.append(obs)
    obstacles[:] = survivors
    return dodged


def draw_obstacle(frame, obs):
    x, y, r, color = int(obs["x"]), int(obs["y"]), obs["radius"], obs["color"]
    fade = 0.5 + 0.5 * obs["z"]
    faded_color = tuple(int(c * fade) for c in color)
    if obs["shape"] == "circle":
        cv2.circle(frame, (x, y), r, faded_color, -1)
        cv2.circle(frame, (x, y), r, (0, 0, 0), 2)
    elif obs["shape"] == "square":
        cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), faded_color, -1)
        cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), (0, 0, 0), 2)
    else:
        pts = np.array([(x, y - r), (x - r, y + r), (x + r, y + r)], dtype=np.int32)
        cv2.fillPoly(frame, [pts], faded_color)
        cv2.polylines(frame, [pts], True, (0, 0, 0), 2)