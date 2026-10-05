"""
engine/hud.py

Shared HUD styling for every HandArcade game: score line, small stat line,
control hints, and the game-over screen.

Public API (unchanged): draw_score, draw_stats, draw_hints, draw_game_over,
reset_score_animation, plus the COLOR_* constants.

Changes in this version:
  - All alpha blending works on the small region being drawn (ROI). The old
    code did frame.copy() of the whole frame for every panel and every
    game-over element (up to 8 full-frame copies per frame at 1080p).
  - Panels are sized from the measured text width instead of guessed
    (long labels no longer overflow the score panel / hint strip).
  - Game-over dimming is done in place.
"""

import random
import time

import cv2

# --- Shared style constants -------------------------------------------------
FONT = cv2.FONT_HERSHEY_SIMPLEX

COLOR_PRIMARY = (255, 255, 255)     # main score text
COLOR_SECONDARY = (210, 210, 210)   # secondary stats
COLOR_HINT = (170, 170, 170)        # bottom control hints
COLOR_ACCENT = (60, 220, 255)       # pulse color when score changes / titles
COLOR_DANGER = (70, 70, 255)        # "GAME OVER" red
COLOR_PANEL = (20, 20, 20)          # backing panel fill (alpha-blended)

SCORE_POS = (30, 55)
SCORE_SCALE = 1.0
SCORE_THICKNESS = 2
SCORE_PANEL_MIN_W = 230

STAT_SCALE = 0.6
STAT_THICKNESS = 1
STAT_LINE_HEIGHT = 30

HINT_SCALE = 0.55
HINT_THICKNESS = 1
HINT_MARGIN_BOTTOM = 20

SCORE_ANIM_DURATION = 0.35   # seconds for the count-up to catch up
SCORE_PULSE_DURATION = 0.25  # seconds the accent-color pulse lasts


def _ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def _ease_out_back(t):
    """Overshoots past 1.0 then settles back -- a noticeable 'pop'."""
    c1 = 1.70158
    c3 = c1 + 1
    t = max(0.0, min(1.0, t))
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


# Per-label animation state so multiple HUD elements don't fight over one value.
_score_anim = {}


def reset_score_animation(label="Score"):
    """Call when a game (re)starts so the new run doesn't animate up from
    the previous run's leftover score."""
    _score_anim.pop(label, None)


# --- ROI helpers ------------------------------------------------------------

def _blend_region(frame, x1, y1, x2, y2, draw, alpha):
    """
    Draw into a copy of just the region (x1,y1)-(x2,y2), then blend that copy
    back at `alpha`. `draw(layer, ox, oy)` must draw using coordinates minus
    the region origin (ox, oy).
    """
    h, w = frame.shape[:2]
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(x2)), min(h, int(y2))
    if x1 >= x2 or y1 >= y2 or alpha <= 0:
        return
    roi = frame[y1:y2, x1:x2]
    layer = roi.copy()
    draw(layer, x1, y1)
    frame[y1:y2, x1:x2] = cv2.addWeighted(layer, alpha, roi, 1 - alpha, 0)


def _fill_rounded(img, x, y, w, h, radius, color):
    radius = max(1, min(radius, w // 2, h // 2))
    cv2.rectangle(img, (x + radius, y), (x + w - radius, y + h), color, -1)
    cv2.rectangle(img, (x, y + radius), (x + w, y + h - radius), color, -1)
    for cx, cy in [(x + radius, y + radius), (x + w - radius, y + radius),
                   (x + radius, y + h - radius), (x + w - radius, y + h - radius)]:
        cv2.circle(img, (cx, cy), radius, color, -1)


def _rounded_panel(frame, x, y, w, h, radius=10, color=COLOR_PANEL, alpha=0.45):
    """Alpha-blended rounded rectangle behind HUD text."""
    x, y, w, h = int(x), int(y), int(w), int(h)

    def draw(layer, ox, oy):
        _fill_rounded(layer, x - ox, y - oy, w, h, radius, color)

    _blend_region(frame, x, y, x + w + 1, y + h + 1, draw, alpha)


def _put_text_shadow(frame, text, pos, scale, color, thickness, shadow_color=(0, 0, 0)):
    x, y = pos
    cv2.putText(frame, text, (x + 2, y + 2), FONT, scale, shadow_color,
                thickness + 1, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), FONT, scale, color, thickness, cv2.LINE_AA)


def _put_text_alpha(frame, text, org, scale, color, thickness, alpha):
    """Text drawn at partial opacity, touching only its own bounding box."""
    (tw, th), base = cv2.getTextSize(text, FONT, scale, thickness)
    x, y = org
    pad = 6

    def draw(layer, ox, oy):
        cv2.putText(layer, text, (x - ox, y - oy), FONT, scale, color, thickness, cv2.LINE_AA)

    _blend_region(frame, x - pad, y - th - pad, x + tw + pad, y + base + pad, draw, alpha)


# --- public drawing functions ---------------------------------------------------

def draw_score(frame, score, label="Score", animate=True):
    """
    Main score readout, top-left, on a rounded backing panel.

    When `score` changes, it eases to the new value over SCORE_ANIM_DURATION
    and briefly renders in COLOR_ACCENT with a small scale bump.
    """
    now = time.time()
    state = _score_anim.setdefault(label, {
        "shown": float(score), "start": float(score), "target": score,
        "t0": now, "pulse_until": 0.0,
    })

    if score != state["target"]:
        state["start"] = state["shown"]
        state["target"] = score
        state["t0"] = now
        state["pulse_until"] = now + SCORE_PULSE_DURATION

    if animate and SCORE_ANIM_DURATION > 0:
        t = min(1.0, (now - state["t0"]) / SCORE_ANIM_DURATION)
        state["shown"] = state["start"] + (state["target"] - state["start"]) * _ease_out_cubic(t)
    else:
        state["shown"] = score

    shown_int = round(state["shown"])
    pulsing = now < state["pulse_until"]
    color = COLOR_ACCENT if pulsing else COLOR_PRIMARY
    scale = SCORE_SCALE * (1.15 if pulsing else 1.0)

    text = f"{label}: {shown_int}"
    (tw, _), _ = cv2.getTextSize(text, FONT, scale, SCORE_THICKNESS)
    x, y = SCORE_POS
    _rounded_panel(frame, x - 15, y - 38, max(SCORE_PANEL_MIN_W, tw + 30), 52)
    _put_text_shadow(frame, text, (x, y), scale, color, SCORE_THICKNESS)


def draw_stats(frame, stats, start_y=85):
    """Secondary stat lines under the score, e.g. draw_stats(frame, ["Dodged: 3"])."""
    for i, line in enumerate(stats):
        y = start_y + i * STAT_LINE_HEIGHT
        _put_text_shadow(frame, line, (30, y), STAT_SCALE, COLOR_SECONDARY, STAT_THICKNESS)


def draw_hints(frame, text="ESC = menu   q = quit"):
    """Bottom-left control hint line, on a subtle panel strip."""
    h = frame.shape[0]
    (tw, _), _ = cv2.getTextSize(text, FONT, HINT_SCALE, HINT_THICKNESS)
    y = h - HINT_MARGIN_BOTTOM
    _rounded_panel(frame, 10, h - 45, tw + 20, 35, radius=8, alpha=0.35)
    _put_text_shadow(frame, text, (20, y), HINT_SCALE, COLOR_HINT, HINT_THICKNESS)


def draw_game_over(frame, score, message=None, lines=None, retry=True, progress=1.0):
    """
    Game-over overlay with an animated entrance.

    Call every frame while ramping `progress` from 0.0 to 1.0: background
    dims in, "GAME OVER" drops in with a bounce, the score counts up, then
    message and hint fade in. At 1.0 it is fully settled.

    NOTE: `message` is chosen at random from `lines` when it is None, so pass
    a fixed `message` (pick it once when the game ends) -- otherwise the text
    changes every frame while animating.
    """
    if message is None and lines:
        message = random.choice(lines)

    p = max(0.0, min(1.0, progress))
    h, w = frame.shape[:2]

    # --- Dim background (first 30%) ------------------------------------------
    dim_eased = _ease_out_cubic(min(1.0, p / 0.3))
    cv2.convertScaleAbs(frame, dst=frame, alpha=1.0 - 0.55 * dim_eased)

    # --- Title: bounces in from above (0% -> 45%) -----------------------------
    title_p = max(0.0, min(1.0, p / 0.45))
    if title_p > 0.0:
        bounce = _ease_out_back(title_p)
        title_scale = max(0.1, 1.4 * bounce)
        y_offset = int((1.0 - min(1.0, title_p * 1.4)) * -80)
        (tw, _), _ = cv2.getTextSize("GAME OVER", FONT, title_scale, 3)
        _put_text_alpha(frame, "GAME OVER", (w // 2 - tw // 2, h // 2 - 60 + y_offset),
                        title_scale, COLOR_DANGER, 3, min(1.0, title_p * 2.0))

    # --- Message: fades in after the title (35% -> 60%) -----------------------
    message_p = max(0.0, min(1.0, (p - 0.35) / 0.25))
    if message and message_p > 0.02:
        (mw, _), _ = cv2.getTextSize(message, FONT, 0.7, 2)
        _put_text_alpha(frame, message, (w // 2 - mw // 2, h // 2 - 10),
                        0.7, COLOR_PRIMARY, 2, message_p)

    # --- Score: counts up from 0 (45% -> 80%) -------------------------------------
    score_p = max(0.0, min(1.0, (p - 0.45) / 0.35))
    if score_p > 0.0:
        score_eased = _ease_out_cubic(score_p)
        shown_score = int(score * score_eased) if score_p < 1.0 else score
        score_text = f"Final score: {shown_score}"
        (sw, _), _ = cv2.getTextSize(score_text, FONT, 0.8, 2)
        _put_text_alpha(frame, score_text, (w // 2 - sw // 2, h // 2 + 30),
                        0.8, COLOR_PRIMARY, 2, score_eased)

    # --- Hint: last (75% -> 100%) ------------------------------------------------------
    hint_p = max(0.0, min(1.0, (p - 0.75) / 0.25))
    if hint_p > 0.02:
        hint = "SPACE = retry   ESC = menu   q = quit" if retry else "ESC = menu   q = quit"
        (hw, _), _ = cv2.getTextSize(hint, FONT, 0.6, 1)
        _put_text_alpha(frame, hint, (w // 2 - hw // 2, h // 2 + 70),
                        0.6, COLOR_SECONDARY, 1, hint_p)