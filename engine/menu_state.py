"""
engine/menu_state.py

Mutable state shared between engine/menu.py, engine/menu_draw.py, and
engine/menu_input.py, plus the shared color palette. Splitting the menu
into these modules (state / input / draw / orchestration) keeps each file
a readable size; this module exists so they can all see the same live
mouse/animation state without reaching into another module's globals.
"""

import time

# --- palette (BGR, since that's what cv2 wants) --------------------------
ACCENT = (0, 255, 255)        # yellow
ACCENT_DIM = (0, 150, 150)
PANEL_BG = (24, 24, 24)
TEXT_PRIMARY = (240, 240, 240)
TEXT_MUTED = (170, 170, 170)
TEXT_FAINT = (110, 110, 110)
GOOD = (90, 220, 90)
BAD = (70, 70, 255)


class MenuState:
    """One instance is created per menu session (see engine/menu.py's
    run_menu) and passed to the drawing and input-handling functions."""

    def __init__(self):
        self.mouse_pos = (0, 0)          # raw window coords, set by menu_input's callback
        self.mouse_click_pending = False
        self.dragging_slider = None      # None | "music" | "sfx"
        self.frame_size = (1280, 720)    # updated each frame in menu_draw.draw_menu

        self.menu_open_time = time.monotonic()
        self.game_card_rects = []        # [(x1, y1, x2, y2), ...], index-aligned with GAMES
        self.volume_bar_rects = {}       # "music"/"sfx" -> (x, y, w, h)
        self.mute_rect = None            # (x1, y1, x2, y2)

    def reset_for_new_session(self):
        """Call each time the menu (re)appears, so the entrance animation
        replays and stale clicks/drags from a previous visit don't leak in."""
        self.menu_open_time = time.monotonic()
        self.mouse_click_pending = False
        self.dragging_slider = None


def point_in_rect(x, y, rect):
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2