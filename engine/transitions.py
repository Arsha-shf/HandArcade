"""
engine/transitions.py

Fade to/from black between the menu and a game, so switching screens
feels intentional instead of an abrupt frame swap.

Reuses engine.camera.show() so the fade gets the same fullscreen/
letterbox handling as every other frame -- see engine/camera.py.

Usage (inside engine/menu.py, around a game launch):
    fade_out(cap, WINDOW_NAME)
    result = run_game(cap, tracker)
    fade_in(cap, WINDOW_NAME)
"""

import cv2

from engine.camera import show

_STEPS = 10          # number of frames the fade takes
_STEP_DELAY_MS = 15  # ms per step -> ~150ms total fade, feels snappy not sluggish


def _blend_to_black(frame, alpha):
    """alpha=0 -> original frame, alpha=1 -> fully black."""
    black = frame.copy()
    black[:] = 0
    return cv2.addWeighted(frame, 1 - alpha, black, alpha, 0)


def fade_out(cap, window_name, steps=_STEPS, delay_ms=_STEP_DELAY_MS):
    """
    Grab the current camera frame and fade it to black.
    Call this right before switching away from the current screen
    (menu -> game, or game -> menu).
    """
    success, frame = cap.read()
    if not success:
        return
    frame = cv2.flip(frame, 1)

    for i in range(steps + 1):
        alpha = i / steps
        show(window_name, _blend_to_black(frame, alpha))
        cv2.waitKey(delay_ms)


def fade_in(cap, window_name, steps=_STEPS, delay_ms=_STEP_DELAY_MS):
    """
    Grab a fresh camera frame and fade in from black.
    Call this right after switching to a new screen, before its own loop starts.
    """
    success, frame = cap.read()
    if not success:
        return
    frame = cv2.flip(frame, 1)

    for i in range(steps, -1, -1):
        alpha = i / steps
        show(window_name, _blend_to_black(frame, alpha))
        cv2.waitKey(delay_ms)