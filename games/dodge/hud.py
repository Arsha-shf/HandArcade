import math
import random
import time

import cv2

from engine.hud import (
    COLOR_ACCENT,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    draw_center_text,
    draw_hints,
    draw_score,
    draw_stats,
)
from engine.hud import draw_game_over as _draw_game_over
from engine.layout import ui_scale

from .config import GAME_OVER_LINES, HARD_MODE_TAUNTS

FONT = cv2.FONT_HERSHEY_SIMPLEX

GAME_OVER_HINT = "SPACE = retry   D = difficulty   ESC = menu   q = quit"


def pick_game_over_line(difficulty):
    pool = GAME_OVER_LINES + HARD_MODE_TAUNTS if difficulty == "hard" else GAME_OVER_LINES
    return random.choice(pool)


def draw_hud(frame, score, dodged, difficulty, best):
    draw_score(frame, score)
    draw_stats(frame, [f"Dodged: {dodged}", f"Mode: {difficulty.upper()}", f"Best: {best}"])
    draw_hints(frame)


def draw_depth_gauge(frame, z):
    """Small vertical gauge on the right edge: where your hand is in depth.
    Top = near the camera (big), bottom = far (small)."""
    h, w = frame.shape[:2]
    s = ui_scale(h)
    x = w - int(40 * s)
    top, bottom = int(h * 0.28), int(h * 0.72)
    cv2.line(frame, (x, top), (x, bottom), (200, 200, 200), max(1, round(2 * s)), cv2.LINE_AA)
    y = int(bottom - z * (bottom - top))
    cv2.circle(frame, (x, y), int(8 * s), COLOR_ACCENT, -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y), int(8 * s), (0, 0, 0), 1, cv2.LINE_AA)
    for label, ly in (("NEAR", top - int(10 * s)), ("FAR", bottom + int(22 * s))):
        (tw, _), _ = cv2.getTextSize(label, FONT, 0.45 * s, 1)
        cv2.putText(frame, label, (x - tw // 2, ly), FONT, 0.45 * s, COLOR_SECONDARY, 1, cv2.LINE_AA)


def draw_swarm_warning(frame, remaining):
    h = frame.shape[0]
    pulse = 0.65 + 0.35 * math.sin(time.time() * 14)
    draw_center_text(frame, "!!! SWARM INCOMING !!!", int(h * 0.13), scale=1.1,
                     color=(0, 0, 255), thickness=3, alpha=pulse)


def draw_status(frame, text):
    """Big centered message (waiting for hand / paused)."""
    h = frame.shape[0]
    draw_center_text(frame, text, int(h * 0.42), scale=1.1, color=COLOR_PRIMARY, thickness=2)


def draw_game_over(frame, score, message, progress=1.0, extra=None):
    _draw_game_over(frame, score, message=message, progress=progress,
                    hint=GAME_OVER_HINT, extra=extra)


def draw_difficulty_select(frame, bests):
    h = frame.shape[0]
    cv2.convertScaleAbs(frame, dst=frame, alpha=0.5)
    cy = h // 2
    s = ui_scale(h)

    def y(offset):
        return cy + int(offset * s)

    draw_center_text(frame, "CHOOSE DIFFICULTY", y(-110), scale=1.2, thickness=3)
    draw_center_text(frame, f"1 - EASY      best {bests['easy']}", y(-45), scale=0.9,
                     color=(100, 220, 100))
    draw_center_text(frame, f"2 - MID       best {bests['mid']}   (some obstacles hunt you)", y(5),
                     scale=0.75, color=(0, 200, 230))
    draw_center_text(frame, f"3 - HARD      best {bests['hard']}   (most obstacles hunt you)", y(55),
                     scale=0.75, color=(60, 60, 230))
    draw_center_text(frame, "Solid shapes can hurt you. Hollow ones pass through.", y(115),
                     scale=0.6, color=COLOR_SECONDARY, thickness=1)
    draw_center_text(frame, "Move your hand closer / farther from the camera to change depth.",
                     y(145), scale=0.6, color=COLOR_SECONDARY, thickness=1)
    draw_center_text(frame, "ESC menu   Q quit", y(195), scale=0.6, color=COLOR_SECONDARY,
                     thickness=1)