"""
engine/select_screen.py

A simple full-screen "pick one" menu drawn over the live camera feed.
Used for difficulty selection.

    value = select_option(cap, "CHOOSE DIFFICULTY", [
        (ord("1"), "1 - EASY", (100, 220, 100), "easy"),
        (ord("2"), "2 - MEDIUM", (0, 200, 230), "medium"),
    ], notes=["Some helpful line"])

Returns the chosen value, "menu" (ESC), "quit" (q), or None if the camera
failed.
"""

import cv2

from engine.camera import show
from engine.hud import COLOR_SECONDARY, draw_center_text
from engine.layout import ui_scale


def select_option(cap, title, options, notes=(), window_name="HandArcade"):
    key_map = {key: value for key, _label, _color, value in options}

    while True:
        success, frame = cap.read()
        if not success:
            return None
        frame = cv2.flip(frame, 1)

        h = frame.shape[0]
        s = ui_scale(h)
        cv2.convertScaleAbs(frame, dst=frame, alpha=0.5)

        cy = h // 2
        y = cy - 110 * s
        draw_center_text(frame, title, y, scale=1.2, thickness=3)

        y = cy - 45 * s
        for _key, label, color, _value in options:
            draw_center_text(frame, label, y, scale=0.85, color=color)
            y += 50 * s

        y += 15 * s
        for note in notes:
            draw_center_text(frame, note, y, scale=0.6, color=COLOR_SECONDARY, thickness=1)
            y += 30 * s

        draw_center_text(frame, "ESC menu   Q quit", y + 25 * s, scale=0.6,
                         color=COLOR_SECONDARY, thickness=1)

        show(window_name, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in key_map:
            return key_map[key]
        if key == 27:
            return "menu"
        if key == ord("q"):
            return "quit"