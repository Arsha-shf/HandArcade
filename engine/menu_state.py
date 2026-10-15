"""
engine/menu_state.py

Mutable state shared between engine/menu.py, engine/menu_draw.py, and
engine/menu_input.py, plus the shared color palette. Splitting the menu
into these modules (state / input / draw / orchestration) keeps each file
a readable size; this module exists so they can all see the same live
mouse/animation state without reaching into another module's globals.
"""

import time

ACCENT = (0, 255, 255)
ACCENT_DIM = (0, 150, 150)
PANEL_BG = (24, 24, 24)
TEXT_PRIMARY = (240, 240, 240)
TEXT_MUTED = (170, 170, 170)
TEXT_FAINT = (110, 110, 110)
GOOD = (90, 220, 90)
BAD = (70, 70, 255)


class MenuState:
    def __init__(self):
        self.mouse_pos = (0, 0)
        self.mouse_click_pending = False
        self.dragging_slider = None
        self.frame_size = (1280, 720)
        self.menu_open_time = time.monotonic()
        self.game_card_rects = []
        self.volume_bar_rects = {}
        self.mute_rect = None

    def reset_for_new_session(self):
        self.menu_open_time = time.monotonic()
        self.mouse_click_pending = False
        self.dragging_slider = None

def point_in_rect(x, y, rect):
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2