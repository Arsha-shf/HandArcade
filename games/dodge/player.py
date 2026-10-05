import math

import cv2

from engine.layout import ui_scale
from engine.smoothing import SmoothedValue
from engine.tracking import get_palm_center

from .config import (
    HAND_SPAN_MAX,
    HAND_SPAN_MIN,
    PLAYER_RADIUS_MAX,
    PLAYER_RADIUS_MIN,
    PLAYER_SMOOTHING_ALPHA,
    PLAYER_Y_MARGIN_BOTTOM,
    PLAYER_Y_MARGIN_TOP,
)


def make_player_state(frame_w, frame_h):
    return {
        "smoother_x": SmoothedValue(alpha=PLAYER_SMOOTHING_ALPHA),
        "smoother_y": SmoothedValue(alpha=PLAYER_SMOOTHING_ALPHA),
        "smoother_z": SmoothedValue(alpha=PLAYER_SMOOTHING_ALPHA * 0.7),
        "ui": ui_scale(frame_h),
        "x": frame_w // 2,
        "y": frame_h // 2,
        "z": 0.5,
        "prev_x": frame_w // 2,
        "prev_y": frame_h // 2,
        "hand_visible": False,
    }


def get_hand_span(hand, frame_w, frame_h):
    """Wrist -> middle-knuckle distance in pixels: a proxy for how close the
    hand is to the camera."""
    wrist = hand.landmark[0]
    middle_mcp = hand.landmark[9]
    dx = (middle_mcp.x - wrist.x) * frame_w
    dy = (middle_mcp.y - wrist.y) * frame_h
    return math.hypot(dx, dy)


def player_radius(z, ui=1.0):
    return int((PLAYER_RADIUS_MIN + (PLAYER_RADIUS_MAX - PLAYER_RADIUS_MIN) * z) * ui)


def update_player(player, results, frame_w, frame_h, dt):
    """dt: seconds since the last frame."""
    ui = player["ui"]
    dt_scale = dt * 30.0

    player["prev_x"] = player["x"]
    player["prev_y"] = player["y"]

    if results.multi_hand_landmarks:
        hand = results.multi_hand_landmarks[0]
        raw_x, raw_y = get_palm_center(hand, (frame_h, frame_w))

        # normalize to 720p so the near/far range doesn't depend on resolution
        span = get_hand_span(hand, frame_w, frame_h) / ui
        raw_z = (span - HAND_SPAN_MIN) / (HAND_SPAN_MAX - HAND_SPAN_MIN)
        raw_z = max(0.0, min(1.0, raw_z))

        smoothed_x = player["smoother_x"].update(raw_x, dt_scale)
        smoothed_y = player["smoother_y"].update(raw_y, dt_scale)
        smoothed_z = player["smoother_z"].update(raw_z, dt_scale)

        radius = player_radius(smoothed_z, ui)
        top = int(PLAYER_Y_MARGIN_TOP * ui) + radius
        bottom = frame_h - int(PLAYER_Y_MARGIN_BOTTOM * ui) - radius
        player["x"] = int(max(radius, min(frame_w - radius, smoothed_x)))
        player["y"] = int(max(top, min(bottom, smoothed_y)))
        player["z"] = smoothed_z
        player["hand_visible"] = True
    else:
        player["hand_visible"] = False


def draw_player(frame, player):
    ui = player["ui"]
    x, y, z = player["x"], player["y"], player["z"]
    radius = player_radius(z, ui)
    vx = x - player["prev_x"]
    vy = y - player["prev_y"]
    shift_max = 6 * ui
    pupil_shift_x = max(-shift_max, min(shift_max, vx))
    pupil_shift_y = max(-shift_max, min(shift_max, vy))

    body_color = (80, 220, 80) if player["hand_visible"] else (80, 120, 220)
    cv2.circle(frame, (x, y), radius, body_color, -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y), radius, (20, 60, 20), max(1, round(2 * ui)), cv2.LINE_AA)

    eye_offset_x = int(radius * 0.36)
    eye_offset_y = int(-radius * 0.27)
    eye_r = max(4, int(radius * 0.27))
    pupil_r = max(2, int(radius * 0.13))
    for side in (-1, 1):
        eye_x = x + side * eye_offset_x
        eye_y = y + eye_offset_y
        cv2.circle(frame, (eye_x, eye_y), eye_r, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (eye_x + int(pupil_shift_x / 2), eye_y + int(pupil_shift_y / 2)),
                   pupil_r, (0, 0, 0), -1, cv2.LINE_AA)

    if not player["hand_visible"]:
        cv2.putText(frame, "where's your hand??", (x - int(90 * ui), y + radius + int(25 * ui)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55 * ui, (80, 120, 220), max(1, round(2 * ui)),
                    cv2.LINE_AA)