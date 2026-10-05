"""
engine/hud.py

Shared HUD styling for every HandArcade game: score, stats, hints,
centered text, and the animated game-over screen.

Everything scales with the frame height (engine/layout.py), so the HUD
looks the same size on a 720p and a 1080p camera.

All alpha blending works on the small region being drawn (ROI), never on
copies of the whole frame.
"""

import random
import time

import cv2

from engine.layout import ui_scale

# --- Shared style constants (sizes are for a 720px-tall frame) ---------------
FONT = cv2.FONT_HERSHEY_SIMPLEX

COLOR_PRIMARY = (255, 255, 255)
COLOR_SECONDARY = (210, 210, 210)
COLOR_HINT = (170, 170, 170)
COLOR_ACCENT = (60, 220, 255)
COLOR_DANGER = (70, 70, 255)
COLOR_PANEL = (20, 20, 20)

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

SCORE_ANIM_DURATION = 0.35
SCORE_PULSE_DURATION = 0.25


def _ui(frame):
    return ui_scale(frame.shape[0])


def _th(thickness, s):
    return max(1, int(round(thickness * s)))


def _ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def _ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    t = max(0.0, min(1.0, t))
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


_score_anim = {}


def reset_score_animation(label="Score"):
    """Call when a game (re)starts."""
    _score_anim.pop(label, None)


# --- ROI helpers ------------------------------------------------------------

def _blend_region(frame, x1, y1, x2, y2, draw, alpha):
    """Draw into a copy of just the region, then blend it back at `alpha`.
    draw(layer, ox, oy) draws using coordinates minus the region origin."""
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
    x, y, w, h, radius = int(x), int(y), int(w), int(h), int(radius)

    def draw(layer, ox, oy):
        _fill_rounded(layer, x - ox, y - oy, w, h, radius, color)

    _blend_region(frame, x, y, x + w + 1, y + h + 1, draw, alpha)


def _put_text_shadow(frame, text, pos, scale, color, thickness, s=1.0, shadow_color=(0, 0, 0)):
    x, y = pos
    off = max(1, int(round(2 * s)))
    cv2.putText(frame, text, (x + off, y + off), FONT, scale, shadow_color,
                thickness + 1, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), FONT, scale, color, thickness, cv2.LINE_AA)


def _put_text_alpha(frame, text, org, scale, color, thickness, alpha):
    """Text at partial opacity, touching only its own bounding box."""
    (tw, th), base = cv2.getTextSize(text, FONT, scale, thickness)
    x, y = org
    pad = 6

    def draw(layer, ox, oy):
        cv2.putText(layer, text, (x - ox, y - oy), FONT, scale, color, thickness, cv2.LINE_AA)

    _blend_region(frame, x - pad, y - th - pad, x + tw + pad, y + base + pad, draw, alpha)


def _center_alpha(frame, text, y, scale, color, thickness, alpha):
    w = frame.shape[1]
    (tw, _), _ = cv2.getTextSize(text, FONT, scale, thickness)
    _put_text_alpha(frame, text, ((w - tw) // 2, int(y)), scale, color, thickness, alpha)


# --- public drawing functions ---------------------------------------------------

def draw_score(frame, score, label="Score", animate=True):
    """Main score readout, top-left, with count-up animation and pulse."""
    s = _ui(frame)
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
    scale = SCORE_SCALE * s * (1.15 if pulsing else 1.0)
    th = _th(SCORE_THICKNESS, s)

    text = f"{label}: {shown_int}"
    (tw, _), _ = cv2.getTextSize(text, FONT, scale, th)
    x, y = int(SCORE_POS[0] * s), int(SCORE_POS[1] * s)
    _rounded_panel(frame, x - 15 * s, y - 38 * s, max(SCORE_PANEL_MIN_W * s, tw + 30 * s),
                   52 * s, radius=10 * s)
    _put_text_shadow(frame, text, (x, y), scale, color, th, s)


def draw_stats(frame, stats, start_y=None):
    """Secondary stat lines under the score: draw_stats(frame, ["Dodged: 3"])."""
    s = _ui(frame)
    if start_y is None:
        start_y = int(85 * s)
    for i, line in enumerate(stats):
        y = start_y + int(i * STAT_LINE_HEIGHT * s)
        _put_text_shadow(frame, line, (int(30 * s), y), STAT_SCALE * s,
                         COLOR_SECONDARY, _th(STAT_THICKNESS, s), s)


def draw_hints(frame, text="ESC = menu   q = quit"):
    """Bottom-left control hints on a subtle panel strip."""
    s = _ui(frame)
    h = frame.shape[0]
    scale, th = HINT_SCALE * s, _th(HINT_THICKNESS, s)
    (tw, _), _ = cv2.getTextSize(text, FONT, scale, th)
    y = h - int(HINT_MARGIN_BOTTOM * s)
    _rounded_panel(frame, 10 * s, h - 45 * s, tw + 20 * s, 35 * s, radius=8 * s, alpha=0.35)
    _put_text_shadow(frame, text, (int(20 * s), y), scale, COLOR_HINT, th, s)


def draw_center_text(frame, text, y, scale=1.0, color=COLOR_PRIMARY, thickness=2, alpha=1.0):
    """Horizontally centered text at pixel row `y`. scale/thickness are in
    720p units and scaled automatically."""
    s = _ui(frame)
    sc, th = scale * s, _th(thickness, s)
    if alpha >= 0.999:
        w = frame.shape[1]
        (tw, _), _ = cv2.getTextSize(text, FONT, sc, th)
        _put_text_shadow(frame, text, ((w - tw) // 2, int(y)), sc, color, th, s)
    else:
        _center_alpha(frame, text, y, sc, color, th, alpha)


def draw_game_over(frame, score, message=None, lines=None, retry=True, progress=1.0,
                   hint=None, extra=None):
    """
    Animated game-over overlay. Call every frame while ramping `progress`
    from 0.0 to 1.0.

    message: pick it ONCE when the game ends and pass it in every frame
             (if None and `lines` is given, a random line is picked per call,
             which would change every frame).
    hint:    override the bottom key hint line.
    extra:   optional line under the score (e.g. "NEW BEST!").
    """
    if message is None and lines:
        message = random.choice(lines)

    p = max(0.0, min(1.0, progress))
    h, w = frame.shape[:2]
    s = _ui(frame)
    cy = h // 2

    # Dim background (first 30%)
    dim_eased = _ease_out_cubic(min(1.0, p / 0.3))
    cv2.convertScaleAbs(frame, dst=frame, alpha=1.0 - 0.55 * dim_eased)

    # Title: bounces in from above (0% -> 45%)
    title_p = max(0.0, min(1.0, p / 0.45))
    if title_p > 0.0:
        bounce = _ease_out_back(title_p)
        title_scale = max(0.1, 1.4 * bounce) * s
        y_offset = int((1.0 - min(1.0, title_p * 1.4)) * -80 * s)
        _center_alpha(frame, "GAME OVER", cy - 60 * s + y_offset, title_scale,
                      COLOR_DANGER, _th(3, s), min(1.0, title_p * 2.0))

    # Message (35% -> 60%)
    message_p = max(0.0, min(1.0, (p - 0.35) / 0.25))
    if message and message_p > 0.02:
        _center_alpha(frame, message, cy - 10 * s, 0.7 * s, COLOR_PRIMARY, _th(2, s), message_p)

    # Score counts up (45% -> 80%)
    score_p = max(0.0, min(1.0, (p - 0.45) / 0.35))
    if score_p > 0.0:
        eased = _ease_out_cubic(score_p)
        shown = int(score * eased) if score_p < 1.0 else score
        _center_alpha(frame, f"Final score: {shown}", cy + 30 * s, 0.8 * s,
                      COLOR_PRIMARY, _th(2, s), eased)
        if extra:
            _center_alpha(frame, extra, cy + 66 * s, 0.7 * s, COLOR_ACCENT, _th(2, s), eased)

    # Hint last (75% -> 100%)
    hint_p = max(0.0, min(1.0, (p - 0.75) / 0.25))
    if hint_p > 0.02:
        if hint is None:
            hint = "SPACE = retry   ESC = menu   q = quit" if retry else "ESC = menu   q = quit"
        _center_alpha(frame, hint, cy + 108 * s, 0.6 * s, COLOR_SECONDARY, _th(1, s), hint_p)