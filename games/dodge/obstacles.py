"""
games/dodge/obstacles.py

Falling obstacles: spawn, fall, get drawn, get counted when dodged.
Collision math lives in collision.py, not here -- this file only owns
obstacle lifecycle.
"""

import random

import cv2
import numpy as np

from .config import OBSTACLE_SHAPES, OBSTACLE_COLORS


def spawn_obstacle(frame_w, speed):
    radius = random.randint(16, 34)
    return {
        "x": random.randint(radius, frame_w - radius),
        "y": -radius,
        "radius": radius,
        "speed": speed,
        "shape": random.choice(OBSTACLE_SHAPES),
        "color": random.choice(OBSTACLE_COLORS),
    }


def update_obstacles(obstacles, frame_h):
    """Move obstacles down, return count of obstacles that fell off-screen (dodged)."""
    dodged = 0
    survivors = []
    for obs in obstacles:
        obs["y"] += obs["speed"]
        if obs["y"] - obs["radius"] > frame_h:
            dodged += 1
        else:
            survivors.append(obs)
    obstacles[:] = survivors
    return dodged


def draw_obstacle(frame, obs):
    x, y, r, color = obs["x"], obs["y"], obs["radius"], obs["color"]
    if obs["shape"] == "circle":
        cv2.circle(frame, (x, y), r, color, -1)
        cv2.circle(frame, (x, y), r, (0, 0, 0), 2)
    elif obs["shape"] == "square":
        cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), color, -1)
        cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), (0, 0, 0), 2)
    else:  # triangle
        pts = np.array([(x, y - r), (x - r, y + r), (x + r, y + r)], dtype=np.int32)
        cv2.fillPoly(frame, [pts], color)
        cv2.polylines(frame, [pts], True, (0, 0, 0), 2)