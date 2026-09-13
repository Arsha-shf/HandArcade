"""
engine/hud.py

Shared HUD styling for every HandArcade game: score line, small stat line,
control hints, and the game-over screen. Centralizing this means every
game looks like it belongs to the same app instead of whoever wrote that
game's hud.py picking its own font size/color that day.

v2 -- visual polish pass:
  - rounded, alpha-blended panels behind text instead of raw cv2.putText
    on the bare camera feed (much more legible + looks intentional)
  - drop-shadowed text everywhere
  - score now animates: a smooth ease-out count-up toward the target
    value, plus a brief accent-colored "pulse" the instant it changes
  - draw_game_over() takes an optional `progress` (0..1) so games can
    animate the whole game-over screen in over ~0.5s (dim -> title pop
    -> score/hint fade in) instead of it appearing instantly. Passing
    nothing still renders it fully settled, so existing call sites keep
    working unchanged.

v3 -- game-over animation now clearly noticeable:
  - title drops in from above with a bounce/overshoot (ease-out-back)
    instead of a barely-visible scale wobble
  - final score counts up from 0 instead of just fading in at full value
  - message/score/hint are staggered in sequence (title -> message ->
    score -> hint) instead of everything fading in together

Each game's own hud.py should call into these instead of calling
cv2.putText directly for score/stats/game-over. Game-specific overlays
(combo meters, bomb warnings, whatever) can still live in the game's own
hud.py using cv2 directly -- this module only owns the parts that should
look identical everywhere.
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

STAT_SCALE = 0.6
STAT_THICKNESS = 1
STAT_LINE_HEIGHT = 30  # vertical gap between stacked stat lines

HINT_SCALE = 0.55
HINT_THICKNESS = 1
HINT_MARGIN_BOTTOM = 20

SCORE_ANIM_DURATION = 0.35   # seconds for the count-up to catch up
SCORE_PULSE_DURATION = 0.25  # seconds the accent-color pulse lasts


def _ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def _ease_out_back(t):
    """Overshoots past 1.0 then settles back -- gives a noticeable 'pop'/
    bounce instead of a smooth-but-flat arrival."""
    c1 = 1.70158
    c3 = c1 + 1
    t = max(0.0, min(1.0, t))
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


# Per-label animation state so multiple HUD elements (or multiple games
# reusing the default "Score" label) don't fight over one shared value.
_score_anim = {}


def reset_score_animation(label="Score"):
    """Call when a game (re)starts so the new run doesn't animate up from
    the previous run's leftover score state."""
    _score_anim.pop(label, None)


def _rounded_panel(frame, x, y, w, h, radius=10, color=COLOR_PANEL, alpha=0.45):
    """Alpha-blended rounded rectangle behind HUD text, for legibility and
    so the HUD reads as a designed UI layer rather than text stamped onto
    the raw camera feed."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    radius = max(1, min(radius, w // 2, h // 2))
    overlay = frame.copy()
    cv2.rectangle(overlay, (x + radius, y), (x + w - radius, y + h), color, -1)
    cv2.rectangle(overlay, (x, y + radius), (x + w, y + h - radius), color, -1)
    for cx, cy in [(x + radius, y + radius), (x + w - radius, y + radius),
                   (x + radius, y + h - radius), (x + w - radius, y + h - radius)]:
        cv2.circle(overlay, (cx, cy), radius, color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def _put_text_shadow(frame, text, pos, scale, color, thickness, shadow_color=(0, 0, 0)):
    """Text with a soft drop shadow so it stays readable over any background,
    camera feed included."""
    x, y = pos
    cv2.putText(frame, text, (x + 2, y + 2), FONT, scale, shadow_color,
                thickness + 1, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), FONT, scale, color, thickness, cv2.LINE_AA)


def draw_score(frame, score, label="Score", animate=True):
    """
    Main score readout, top-left, on a rounded backing panel.

    When `score` changes from the last call, it eases up to the new value
    over SCORE_ANIM_DURATION instead of snapping, and briefly renders in
    COLOR_ACCENT with a small scale bump -- so gaining points reads as an
    event, not just a number changing.
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

    x, y = SCORE_POS
    _rounded_panel(frame, x - 15, y - 38, 230, 52)
    _put_text_shadow(frame, f"{label}: {shown_int}", (x, y), scale, color, SCORE_THICKNESS)


def draw_stats(frame, stats, start_y=85):
    """
    Secondary stat lines under the score, e.g. draw_stats(frame, ["Dodged: 3"]).
    Pass a list so games can show 0, 1, or several extra stats consistently.
    """
    for i, line in enumerate(stats):
        y = start_y + i * STAT_LINE_HEIGHT
        _put_text_shadow(frame, line, (30, y), STAT_SCALE, COLOR_SECONDARY, STAT_THICKNESS)


def draw_hints(frame, text="ESC = menu   q = quit"):
    """Bottom-left control hint line, on a subtle panel strip, same spot/
    style in every game."""
    h, w = frame.shape[:2]
    y = h - HINT_MARGIN_BOTTOM
    _rounded_panel(frame, 10, h - 45, len(text) * 10 + 20, 35, radius=8, alpha=0.35)
    _put_text_shadow(frame, text, (20, y), HINT_SCALE, COLOR_HINT, HINT_THICKNESS)


def draw_game_over(frame, score, message=None, lines=None, retry=True, progress=1.0):
    """
    Game-over overlay with an animated entrance.

    Call this every frame while ramping `progress` from 0.0 (just
    triggered) up to 1.0: the background dims in, "GAME OVER" drops in
    from above with a bounce/overshoot, the score counts up from 0 to
    its final value, and the message/hint fade in last, staggered after
    everything else. Once `progress` reaches 1.0 it renders fully
    settled -- identical to the old, non-animated version.
    """
    if message is None and lines:
        message = random.choice(lines)

    p = max(0.0, min(1.0, progress))
    h, w = frame.shape[:2]

    # --- Dim background (first 30% of the animation) -----------------------
    dim_eased = _ease_out_cubic(min(1.0, p / 0.3))
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55 * dim_eased, frame, 1 - 0.55 * dim_eased, 0, frame)

    # --- Title: bounces/drops in from above (0% -> 45%) ---------------------
    title_p = max(0.0, min(1.0, p / 0.45))
    if title_p > 0.0:
        bounce = _ease_out_back(title_p)
        title_scale = max(0.1, 1.4 * bounce)
        y_offset = int((1.0 - min(1.0, title_p * 1.4)) * -80)
        title_layer = frame.copy()
        (tw, _), _ = cv2.getTextSize("GAME OVER", FONT, title_scale, 3)
        cv2.putText(title_layer, "GAME OVER", (w // 2 - tw // 2, h // 2 - 60 + y_offset),
                    FONT, title_scale, COLOR_DANGER, 3, cv2.LINE_AA)
        alpha = min(1.0, title_p * 2.0)
        cv2.addWeighted(title_layer, alpha, frame, 1 - alpha, 0, frame)

    # --- Message line: fades in right after the title (35% -> 60%) ---------
    message_p = max(0.0, min(1.0, (p - 0.35) / 0.25))
    if message and message_p > 0.02:
        msg_layer = frame.copy()
        (mw, _), _ = cv2.getTextSize(message, FONT, 0.7, 2)
        cv2.putText(msg_layer, message, (w // 2 - mw // 2, h // 2 - 10),
                    FONT, 0.7, COLOR_PRIMARY, 2, cv2.LINE_AA)
        cv2.addWeighted(msg_layer, message_p, frame, 1 - message_p, 0, frame)

    # --- Score: counts up from 0 to final value (45% -> 80%) ----------------
    score_p = max(0.0, min(1.0, (p - 0.45) / 0.35))
    if score_p > 0.0:
        score_eased = _ease_out_cubic(score_p)
        shown_score = int(score * score_eased) if score_p < 1.0 else score
        score_layer = frame.copy()
        score_text = f"Final score: {shown_score}"
        (sw, _), _ = cv2.getTextSize(score_text, FONT, 0.8, 2)
        cv2.putText(score_layer, score_text, (w // 2 - sw // 2, h // 2 + 30),
                    FONT, 0.8, COLOR_PRIMARY, 2, cv2.LINE_AA)
        cv2.addWeighted(score_layer, score_eased, frame, 1 - score_eased, 0, frame)

    # --- Hint: comes in last (75% -> 100%) -----------------------------------
    hint_p = max(0.0, min(1.0, (p - 0.75) / 0.25))
    if hint_p > 0.02:
        hint_layer = frame.copy()
        hint = "SPACE = retry   ESC = menu   q = quit" if retry else "ESC = menu   q = quit"
        (hw, _), _ = cv2.getTextSize(hint, FONT, 0.6, 1)
        cv2.putText(hint_layer, hint, (w // 2 - hw // 2, h // 2 + 70),
                    FONT, 0.6, COLOR_SECONDARY, 1, cv2.LINE_AA)
        cv2.addWeighted(hint_layer, hint_p, frame, 1 - hint_p, 0, frame)