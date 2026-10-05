"""
games/catch/hud.py

Catch-specific drawing: HUD, popups, paw rendering, particles. Score,
stats, hints and the game-over screen come from engine/hud.py so Catch looks
like the rest of the arcade.

`ui` everywhere is engine.layout.ui_scale(frame_h).
"""

import math
import random

import cv2

from engine import hud as engine_hud
from engine.hud import draw_hints, draw_score, draw_stats
from engine.layout import ui_scale

from .paw import CATCH_TTL, Paw

FONT = cv2.FONT_HERSHEY_SIMPLEX

PAW_COLORS = [
    (0, 210, 255),
    (255, 90, 180),
]


def draw_hud(frame, score, misses, max_misses, combo, best):
    h, w = frame.shape[:2]
    s = ui_scale(h)

    draw_score(frame, score)
    draw_stats(frame, [f"Misses: {misses}/{max_misses}", f"Best: {best}"])

    if combo >= 3:
        text = f"Combo x{combo}!"
        scale, th = 1.1 * s, max(1, round(3 * s))
        (tw, _), _ = cv2.getTextSize(text, FONT, scale, th)
        x, y = w - tw - int(20 * s), int(45 * s)
        cv2.putText(frame, text, (x + 2, y + 2), FONT, scale, (0, 0, 0), th + 1, cv2.LINE_AA)
        cv2.putText(frame, text, (x, y), FONT, scale, (0, 215, 255), th, cv2.LINE_AA)

    draw_hints(frame)


def draw_popup(frame, x, y, text, color, life, ui):
    """Floating text that rises and is drawn at its spot. life: 1.0 -> 0.0."""
    rise = (1.0 - life) * 25 * ui
    scale, th = 0.9 * ui, max(1, round(2 * ui))
    px, py = int(x) - int(15 * ui), int(y) - int(30 * ui) - int(rise)
    cv2.putText(frame, text, (px + 2, py + 2), FONT, scale, (0, 0, 0), th + 1, cv2.LINE_AA)
    cv2.putText(frame, text, (px, py), FONT, scale, color, th, cv2.LINE_AA)


def draw_game_over(frame, score, message=None, progress=1.0, extra=None):
    engine_hud.draw_game_over(frame, score, message=message, progress=progress, extra=extra)


def draw_paw(frame, paw, base_radius, ui):
    x, y = int(paw.x), int(paw.y)
    color = PAW_COLORS[paw.id % len(PAW_COLORS)]
    line = max(1, round(2 * ui))

    if paw.state == Paw.CATCH:
        progress = min(1.0, paw.catch_timer / CATCH_TTL)
        r = int(base_radius * 0.5 * (1.0 + 0.5 * progress))
        cv2.circle(frame, (x, y), r, color, -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), r, (255, 255, 255), line, cv2.LINE_AA)
        for a in range(0, 360, 60):
            rad = math.radians(a)
            x2 = int(x + (r + 14 * ui) * math.cos(rad))
            y2 = int(y + (r + 14 * ui) * math.sin(rad))
            cv2.line(frame, (x, y), (x2, y2), color, max(1, round(3 * ui)), cv2.LINE_AA)

    elif paw.state == Paw.SWIPE:
        speed = min(paw.speed(), 40 * ui)
        axis_major = int(base_radius * 0.6 + speed * 0.7)
        axis_minor = max(int(10 * ui), int(base_radius * 0.6 - speed * 0.15))
        cv2.ellipse(frame, (x, y), (axis_major, axis_minor), paw.angle, 0, 360, color, line, cv2.LINE_AA)
        cv2.line(frame, (int(paw.prev_x), int(paw.prev_y)), (x, y), color, line, cv2.LINE_AA)

    else:
        cv2.circle(frame, (x, y), int(base_radius * 0.85), color, line, cv2.LINE_AA)
        cv2.circle(frame, (x, y), max(2, int(5 * ui)), color, -1, cv2.LINE_AA)


def spawn_particles(x, y, color, ui, count=10):
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.5, 6.5) * ui
        particles.append({
            "x": float(x), "y": float(y),
            "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
            "ttl": float(random.randint(10, 18)),
            "color": color,
        })
    return particles


def update_and_draw_particles(frame, particles, dt_scale, ui):
    alive = []
    radius = max(2, int(3 * ui))
    for p in particles:
        p["x"] += p["vx"] * dt_scale
        p["y"] += p["vy"] * dt_scale
        p["vy"] += 0.15 * ui * dt_scale
        p["ttl"] -= dt_scale
        if p["ttl"] > 0:
            cv2.circle(frame, (int(p["x"]), int(p["y"])), radius, p["color"], -1, cv2.LINE_AA)
            alive.append(p)
    return alive