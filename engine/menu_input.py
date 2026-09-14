"""
engine/menu_input.py

Mouse handling for the HandArcade menu screen: the raw cv2 mouse callback,
window-to-frame coordinate mapping, and hit-testing against the rects
engine/menu_draw.py records into the shared MenuState each frame.

cv2's mouse callback reports coordinates in *window* pixels, which are not
the same as *frame* pixels once engine.camera.show() has scaled/letterboxed
the frame to fit a fullscreen window. `window_to_frame_coords` converts
between the two using cv2.getWindowImageRect(), assuming show() does the
standard "scale to fit, preserve aspect ratio, center" letterbox -- which
is what the fullscreen setup is documented to do. If engine/camera.py's
`show()` ever uses a different scaling/centering convention, this mapping
(and therefore click/drag accuracy) needs to be updated to match.
"""

import cv2

from engine.audio import set_music_volume, set_sfx_volume
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
    bx, by, bw, bh = state.volume_bar_rects.get(name, (0, 0, 1, 1))
    pct = max(0.0, min(1.0, (fx - bx) / bw))
    if name == "music":
        set_music_volume(pct)
    elif name == "sfx":
        set_sfx_volume(pct)


def game_at(state, fx, fy):
    for i, rect in enumerate(state.game_card_rects):
        if point_in_rect(fx, fy, rect):
            return i
    return None


def make_mouse_callback(window_name, state):
    """Build the cv2 mouse callback for `window_name`, closing over `state`
    so it can be registered with cv2.setMouseCallback without any
    module-level globals."""

    def _on_mouse(event, x, y, flags, param):
        state.mouse_pos = (x, y)

        if event == cv2.EVENT_LBUTTONDOWN:
            state.mouse_click_pending = True
            fx, fy = window_to_frame_coords(window_name, x, y, *state.frame_size)
            state.dragging_slider = slider_at(state, fx, fy)
        elif event == cv2.EVENT_LBUTTONUP:
            state.dragging_slider = None
        elif event == cv2.EVENT_MOUSEMOVE and state.dragging_slider is not None:
            fx, _ = window_to_frame_coords(window_name, x, y, *state.frame_size)
            set_slider_from_x(state, state.dragging_slider, fx)

    return _on_mouse