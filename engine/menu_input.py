"""
engine/menu_input.py

Mouse handling for the HandArcade menu screen: the raw cv2 mouse callback,
window-to-frame coordinate mapping, and hit-testing against the rects
engine/menu_draw.py records into the shared MenuState each frame.

cv2's mouse callback reports WINDOW pixels. engine.camera.show() fits the
frame inside the window (preserve aspect, centered, black bars), so
window_to_frame_coords() inverts exactly that mapping. If show() ever
changes its scaling convention, update this function to match.
"""

import cv2

from engine.audio import save_settings, set_music_volume, set_sfx_volume
from engine.menu_state import point_in_rect


def window_to_frame_coords(window_name, x, y, frame_w, frame_h):
    try:
        _, _, win_w, win_h = cv2.getWindowImageRect(window_name)
    except Exception:
        return x, y  # best-effort fallback: assume a 1:1 mapping

    if win_w <= 0 or win_h <= 0 or frame_w <= 0 or frame_h <= 0:
        return x, y

    scale = min(win_w / frame_w, win_h / frame_h)
    disp_w, disp_h = frame_w * scale, frame_h * scale
    off_x, off_y = (win_w - disp_w) / 2, (win_h - disp_h) / 2

    return (x - off_x) / scale, (y - off_y) / scale


def slider_at(state, fx, fy):
    for name, (bx, by, bw, bh) in state.volume_bar_rects.items():
        if bx - 6 <= fx <= bx + bw + 6 and by - 10 <= fy <= by + bh + 10:
            return name
    return None


def set_slider_from_x(state, name, fx):
    """Apply the slider value WITHOUT writing to disk (called on every mouse
    move while dragging). The caller saves once on mouse release."""
    bx, by, bw, bh = state.volume_bar_rects.get(name, (0, 0, 1, 1))
    pct = max(0.0, min(1.0, (fx - bx) / max(1, bw)))
    if name == "music":
        set_music_volume(pct, save=False)
    elif name == "sfx":
        set_sfx_volume(pct, save=False)


def game_at(state, fx, fy):
    for i, rect in enumerate(state.game_card_rects):
        if point_in_rect(fx, fy, rect):
            return i
    return None


def make_mouse_callback(window_name, state):
    """Build the cv2 mouse callback for `window_name`, closing over `state`."""

    def _on_mouse(event, x, y, flags, param):
        state.mouse_pos = (x, y)

        if event == cv2.EVENT_LBUTTONDOWN:
            fx, fy = window_to_frame_coords(window_name, x, y, *state.frame_size)
            state.dragging_slider = slider_at(state, fx, fy)
            if state.dragging_slider is not None:
                # a plain click on the bar must set the value too
                set_slider_from_x(state, state.dragging_slider, fx)
            else:
                state.mouse_click_pending = True
        elif event == cv2.EVENT_LBUTTONUP:
            if state.dragging_slider is not None:
                save_settings()
            state.dragging_slider = None
        elif event == cv2.EVENT_MOUSEMOVE and state.dragging_slider is not None:
            fx, _ = window_to_frame_coords(window_name, x, y, *state.frame_size)
            set_slider_from_x(state, state.dragging_slider, fx)

    return _on_mouse