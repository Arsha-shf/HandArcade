import random

import cv2

from engine.hud import draw_game_over as _draw_game_over
from engine.hud import draw_hints, draw_score, draw_stats

from .config import GAME_OVER_LINES, HARD_MODE_TAUNTS


def pick_game_over_line(difficulty):
    pool = GAME_OVER_LINES + HARD_MODE_TAUNTS if difficulty == "hard" else GAME_OVER_LINES
    return random.choice(pool)


def draw_hud(frame, score, dodged, frame_count, difficulty):
    draw_score(frame, score)
    draw_stats(frame, [f"Dodged: {dodged}", f"Mode: {difficulty.upper()}"])
    draw_hints(frame)


def draw_swarm_warning(frame):
    h, w = frame.shape[:2]
    cv2.putText(frame, "!!! SWARM INCOMING !!!", (w // 2 - 260, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)


def draw_game_over(frame, score, message=None):
    _draw_game_over(frame, score, message=message, lines=GAME_OVER_LINES)


def draw_difficulty_select(frame):
    h, w = frame.shape[:2]
    cv2.putText(frame, "CHOOSE DIFFICULTY", (w // 2 - 220, h // 2 - 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    cv2.putText(frame, "1 - EASY", (w // 2 - 220, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (100, 220, 100), 2)
    cv2.putText(frame, "2 - MID  (some obstacles hunt you)", (w // 2 - 220, h // 2 + 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 230), 2)
    cv2.putText(frame, "3 - HARD (most obstacles hunt you, good luck)", (w // 2 - 220, h // 2 + 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 230), 2)
    cv2.putText(frame, "ESC menu   Q quit", (w // 2 - 220, h // 2 + 140),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)