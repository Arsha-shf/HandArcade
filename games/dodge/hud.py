"""
games/dodge/hud.py

All on-screen text/overlays: live score, dodge count, and the game-over
screen with a random dumb death line.
"""

import random

import cv2

from .config import GAME_OVER_LINES


def draw_hud(frame, score, dodged, frame_count):
    cv2.putText(frame, f"Score: {score}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(frame, f"Dodged: {dodged}", (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.putText(frame, "ESC = menu   q = quit", (20, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)


def pick_game_over_line():
    return random.choice(GAME_OVER_LINES)


def draw_game_over(frame, score, message):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    cv2.putText(frame, "GAME OVER", (w // 2 - 150, h // 2 - 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (60, 60, 255), 3)
    cv2.putText(frame, message, (w // 2 - len(message) * 6, h // 2 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Final score: {score}", (w // 2 - 100, h // 2 + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, "SPACE = retry   ESC = menu   q = quit",
                (w // 2 - 220, h // 2 + 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)