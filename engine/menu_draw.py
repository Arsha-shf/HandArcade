"""
engine/menu_draw.py

All drawing for the HandArcade menu screen: rounded/alpha-blended panels,
the drifting particle backdrop, the title, the game cards (with their
staggered entrance animation and hover glow), the audio control panel, and
the custom cursor.

Everything here is a function of the current frame plus the shared
MenuState (see engine/menu_state.py); drawing functions don't hold their
own state, though draw_game_cards and draw_audio_controls write hit-test
rects back into `state` so engine/menu_input.py can use them next frame.
"""

import time

import cv2
import numpy as np

from engine.audio import get_music_volume, get_sfx_volume, is_muted
from engine.menu_input import window_to_frame_coords
from engine.menu_state import (
    ACCENT,
    ACCENT_DIM,
    BAD,
    GOOD,
    PANEL_BG,
    TEXT_MUTED,
    TEXT_PRIMARY,
    point_in_rect,
)


# --- low-level drawing helpers -------------------------------------------

def rounded_rect(img, pt1, pt2, radius, color, thickness=-1):
    """Draw a rounded rectangle. thickness=-1 fills it, otherwise outlines it."""
    x1, y1 = pt1
    x2, y2 = pt2
    radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))

    if thickness < 0:
        cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, -1)
        cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, -1)
        for cx, cy in (
            (x1 + radius, y1 + radius),
            (x2 - radius, y1 + radius),
            (x1 + radius, y2 - radius),
            (x2 - radius, y2 - radius),
        ):
            cv2.circle(img, (cx, cy), radius, color, -1, cv2.LINE_AA)
    else:
        cv2.line(img, (x1 + radius, y1), (x2 - radius, y1), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x1 + radius, y2), (x2 - radius, y2), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x1, y1 + radius), (x1, y2 - radius), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x2, y1 + radius), (x2, y2 - radius), color, thickness, cv2.LINE_AA)
        cv2.ellipse(img, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(img, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(img, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(img, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness, cv2.LINE_AA)


def draw_panel(frame, pt1, pt2, radius=14, color=PANEL_BG, alpha=0.55,
               border_color=None, border_thickness=1):
    """Alpha-blended rounded panel, optionally with a thin border on top."""
    overlay = frame.copy()
    rounded_rect(overlay, pt1, pt2, radius, color, thickness=-1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    if border_color is not None:
        rounded_rect(frame, pt1, pt2, radius, border_color, thickness=border_thickness)


def draw_text_shadow(frame, text, org, font=cv2.FONT_HERSHEY_SIMPLEX, scale=0.9,
                      color=TEXT_PRIMARY, thickness=2, shadow_color=(0, 0, 0), offset=2):
    x, y = org
    cv2.putText(frame, text, (x + offset, y + offset), font, scale, shadow_color,
                thickness + 1, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


# --- background animation ---------------------------------------------------

def draw_particles(frame, t):
    """Soft drifting specks behind everything else -- purely decorative."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    n = 18
    for i in range(n):
        speed = 30 + (i % 5) * 14
        phase = i * 53.0
        y = h - ((t * speed + phase) % (h + 40)) + 20
        x = int(w * ((i * 0.61803398875) % 1.0))
        radius = 3 + (i % 4)
        mix = 0.5 + 0.5 * np.sin(t * 0.6 + i)
        color = (int(60 + 40 * mix), int(180 + 60 * mix), int(180 + 60 * (1 - mix)))
        cv2.circle(overlay, (x, int(y)), radius, color, -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)


def draw_cursor(frame, pos):
    x, y = int(pos[0]), int(pos[1])
    h, w = frame.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return
    cv2.circle(frame, (x, y), 10, ACCENT, 1, cv2.LINE_AA)
    cv2.circle(frame, (x, y), 2, ACCENT, -1, cv2.LINE_AA)


# --- menu drawing ----------------------------------------------------------

def draw_menu(window_name, frame, state, games):
    h, w = frame.shape[:2]
    state.frame_size = (w, h)
    t = time.monotonic()

    draw_particles(frame, t)

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

    hover = window_to_frame_coords(window_name, *state.mouse_pos, w, h)

    draw_title(frame, t)
    draw_game_cards(frame, t, hover, state, games)
    draw_audio_controls(frame, hover, state)
    draw_cursor(frame, hover)


def draw_title(frame, t):
    w = frame.shape[1]
    pt1, pt2 = (20, 20), (min(600, w - 20), 100)
    draw_panel(frame, pt1, pt2, radius=18, alpha=0.6, border_color=ACCENT_DIM)
    draw_text_shadow(frame, "HandArcade", (40, 68), scale=1.3, color=ACCENT, thickness=3)
    cv2.putText(frame, "Click or press 1-4 to play  -  'q' to quit", (40, 92),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_MUTED, 1, cv2.LINE_AA)

    # slow glow sweeping under the title -- purely cosmetic
    bar_x1, bar_x2 = 40, pt2[0] - 20
    sweep = (np.sin(t * 1.4) + 1) / 2
    glow_x = int(bar_x1 + sweep * max(0, (bar_x2 - bar_x1 - 60)))
    cv2.line(frame, (bar_x1, 96), (bar_x2, 96), (50, 50, 50), 1, cv2.LINE_AA)
    cv2.line(frame, (glow_x, 96), (glow_x + 60, 96), ACCENT, 2, cv2.LINE_AA)


def draw_game_cards(frame, t, hover, state, games):
    state.game_card_rects = []
    w = frame.shape[1]
    card_x, card_w = 40, min(440, w - 80)
    card_h, gap = 62, 14
    start_y = 130
    hx, hy = hover

    since_open = t - state.menu_open_time
    pulse = 0.5 + 0.5 * np.sin(t * 2.5)

    for i, (name, _) in enumerate(games):
        y = start_y + i * (card_h + gap)

        # staggered slide-and-fade entrance each time the menu appears
        local_t = max(0.0, min(1.0, (since_open - i * 0.07) / 0.25))
        eased = 1 - (1 - local_t) ** 3
        x = card_x + int((1 - eased) * 80)
        pt1, pt2 = (x, y), (x + card_w, y + card_h)
        state.game_card_rects.append((x, y, x + card_w, y + card_h))

        if eased < 0.05:
            continue  # nothing worth drawing while still off-screen

        hovering = eased > 0.99 and point_in_rect(hx, hy, (x, y, x + card_w, y + card_h))
        border = ACCENT if hovering else ACCENT_DIM
        draw_panel(frame, pt1, pt2, radius=14, alpha=0.55 * eased,
                   border_color=border, border_thickness=2 if hovering else 1)

        badge_center = (x + 34, y + card_h // 2)
        glow = 1.0 if hovering else pulse
        badge_color = tuple(int(c * (0.6 + 0.4 * glow)) for c in ACCENT)
        badge_r = 22 if hovering else 20
        cv2.circle(frame, badge_center, badge_r, badge_color, -1, cv2.LINE_AA)
        cv2.circle(frame, badge_center, badge_r, (0, 0, 0), 1, cv2.LINE_AA)

        label = str(i + 1)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.putText(frame, label, (badge_center[0] - tw // 2, badge_center[1] + th // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (15, 15, 15), 2, cv2.LINE_AA)

        name_color = (255, 255, 255) if hovering else TEXT_PRIMARY
        draw_text_shadow(frame, name, (x + 66, y + card_h // 2 + 8),
                          scale=0.78 if hovering else 0.75, color=name_color, thickness=2)

        if hovering:
            cv2.putText(frame, "click to play", (x + card_w - 130, y + card_h - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, ACCENT, 1, cv2.LINE_AA)


def draw_audio_controls(frame, hover, state):
    h, w = frame.shape[:2]
    hx, hy = hover
    panel_w = min(320, w - 40)
    pt1, pt2 = (20, h - 130), (20 + panel_w, h - 20)
    draw_panel(frame, pt1, pt2, radius=14, alpha=0.55, border_color=ACCENT_DIM)

    mute_rect = (pt1[0] + 8, pt1[1] + 8, pt1[0] + 160, pt1[1] + 34)
    state.mute_rect = mute_rect
    if point_in_rect(hx, hy, mute_rect):
        rounded_rect(frame, (mute_rect[0] - 4, mute_rect[1] - 2),
                     (mute_rect[2] + 4, mute_rect[3] + 2), 8, (55, 55, 55), thickness=-1)
    mute_text = "MUTED  (click)" if is_muted() else "Sound ON  (click)"
    mute_color = BAD if is_muted() else GOOD
    cv2.putText(frame, mute_text, (36, h - 102), cv2.FONT_HERSHEY_SIMPLEX, 0.55, mute_color, 2, cv2.LINE_AA)

    music_pct = int(round(get_music_volume() * 100))
    sfx_pct = int(round(get_sfx_volume() * 100))
    bar_x, bar_w, bar_h = 110, panel_w - 130, 10

    cv2.putText(frame, "Music", (36, h - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.48, TEXT_MUTED, 1, cv2.LINE_AA)
    music_y = h - 79
    state.volume_bar_rects["music"] = (bar_x, music_y, bar_w, bar_h)
    draw_volume_bar(frame, bar_x, music_y, music_pct, bar_w, bar_h,
                     dragging=state.dragging_slider == "music",
                     hover=point_in_rect(hx, hy, (bar_x - 6, music_y - 10, bar_x + bar_w + 6, music_y + bar_h + 10)))

    cv2.putText(frame, "SFX", (36, h - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.48, TEXT_MUTED, 1, cv2.LINE_AA)
    sfx_y = h - 47
    state.volume_bar_rects["sfx"] = (bar_x, sfx_y, bar_w, bar_h)
    draw_volume_bar(frame, bar_x, sfx_y, sfx_pct, bar_w, bar_h,
                     dragging=state.dragging_slider == "sfx",
                     hover=point_in_rect(hx, hy, (bar_x - 6, sfx_y - 10, bar_x + bar_w + 6, sfx_y + bar_h + 10)))


def draw_volume_bar(frame, x, y, pct, width=100, height=10, dragging=False, hover=False):
    rounded_rect(frame, (x, y), (x + width, y + height), height // 2, (70, 70, 70), thickness=-1)
    fill_w = int(width * max(0, min(100, pct)) / 100)
    if fill_w >= height:
        rounded_rect(frame, (x, y), (x + fill_w, y + height), height // 2, ACCENT, thickness=-1)

    knob_r = 8 if (dragging or hover) else 6
    knob_color = (255, 255, 255) if dragging else ACCENT
    cv2.circle(frame, (x + fill_w, y + height // 2), knob_r, knob_color, -1, cv2.LINE_AA)
    cv2.circle(frame, (x + fill_w, y + height // 2), knob_r, (0, 0, 0), 1, cv2.LINE_AA)

    cv2.putText(frame, f"{pct}%", (x + width + 10, y + height), cv2.FONT_HERSHEY_SIMPLEX,
                0.45, TEXT_MUTED, 1, cv2.LINE_AA)