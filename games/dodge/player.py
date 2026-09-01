"""
games/dodge/player.py

Player blob: position driven by palm x (engine.tracking.get_palm_center),
smoothed with engine.head_tracking.SmoothedValue -- that class is a plain
EMA smoother with nothing face-specific about it, so it's reused here
instead of rewritten.
"""

import cv2

from engine.tracking import get_palm_center
from engine.head_tracking import SmoothedValue

from .config import PLAYER_RADIUS, PLAYER_Y_OFFSET_FROM_BOTTOM, PLAYER_SMOOTHING_ALPHA


def make_player_state(frame_w, frame_h):
    return {
        "smoother": SmoothedValue(alpha=PLAYER_SMOOTHING_ALPHA),
        "x": frame_w // 2,
        "prev_x": frame_w // 2,
        "y": frame_h - PLAYER_Y_OFFSET_FROM_BOTTOM,
        "hand_visible": False,
    }


def update_player(player, results, frame_w, frame_h):
    player["prev_x"] = player["x"]

    if results.multi_hand_landmarks:
        hand = results.multi_hand_landmarks[0]
        raw_x, _raw_y = get_palm_center(hand, (frame_h, frame_w))
        smoothed_x = player["smoother"].update(raw_x)
        player["x"] = int(max(PLAYER_RADIUS, min(frame_w - PLAYER_RADIUS, smoothed_x)))
        player["hand_visible"] = True
    else:
        # No hand this frame: keep last known position, don't snap or reset.
        player["hand_visible"] = False


def draw_player(frame, player):
    x, y = player["x"], player["y"]
    velocity = x - player["prev_x"]
    pupil_shift = max(-6, min(6, velocity))  # eyes glance toward movement

    body_color = (80, 220, 80) if player["hand_visible"] else (80, 120, 220)
    cv2.circle(frame, (x, y), PLAYER_RADIUS, body_color, -1)
    cv2.circle(frame, (x, y), PLAYER_RADIUS, (20, 60, 20), 2)

    # Googly eyes
    eye_offset_x = 11
    eye_offset_y = -8
    for side in (-1, 1):
        eye_x = x + side * eye_offset_x
        eye_y = y + eye_offset_y
        cv2.circle(frame, (eye_x, eye_y), 8, (255, 255, 255), -1)
        cv2.circle(frame, (eye_x + pupil_shift // 2, eye_y), 4, (0, 0, 0), -1)

    if not player["hand_visible"]:
        cv2.putText(frame, "where's your hand??", (x - 90, y + 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 120, 220), 2)