"""
games/fruit_slice/hud.py

Fruit Slice HUD: score/stats/hints and the game-over screen come from
engine/hud.py; this file adds the heart row for lives.
"""

import math

import cv2
import numpy as np

from engine import hud as engine_hud
from engine.hud import draw_hints, draw_score, draw_stats
from engine.layout import ui_scale

GAME_OVER_HINT = "SPACE = retry   D = difficulty   ESC = menu   q = quit"


def _heart_points(cx, cy, size):
    pts = []
    for i in range(32):
        t = 2 * math.pi * i / 32
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((int(cx + x * size / 34), int(cy - y * size / 34)))
    return np.array(pts, dtype=np.int32)


def draw_lives(frame, lives, max_lives):
    """Row of hearts, top-right. Filled = life left, outline = life lost."""
    h, w = frame.shape[:2]
    s = ui_scale(h)
    size = 30 * s
    spacing = 40 * s
    x0 = w - 30 * s - (max_lives - 1) * spacing
    cy = 38 * s

    for i in range(max_lives):
        pts = _heart_points(x0 + i * spacing, cy, size)
        if i < lives:
            cv2.fillPoly(frame, [pts], (70, 70, 255), cv2.LINE_AA)
            cv2.polylines(frame, [pts], True, (0, 0, 120), max(1, round(2 * s)), cv2.LINE_AA)
        else:
            cv2.polylines(frame, [pts], True, (150, 150, 150), max(1, round(2 * s)), cv2.LINE_AA)


def draw_hud(frame, score, lives, max_lives, best, difficulty, fps=None):
    draw_score(frame, score)
    stats = [f"Mode: {difficulty.upper()}", f"Best: {best}"]
    if fps is not None:
        stats.append(f"FPS: {fps:.0f}")
    draw_stats(frame, stats)
    draw_lives(frame, lives, max_lives)
    draw_hints(frame, "ESC = menu   q = quit   f = fps")


def draw_game_over(frame, score, progress=1.0, extra=None):
    engine_hud.draw_game_over(frame, score, progress=progress, hint=GAME_OVER_HINT,
                              extra=extra)