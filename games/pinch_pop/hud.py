import cv2

from engine import hud as engine_hud
from engine.hud import (
    COLOR_ACCENT,
    COLOR_SECONDARY,
    draw_center_text,
    draw_hints,
    draw_score,
    draw_stats,
    draw_text,
)
from engine.layout import ui_scale

from .score import COMBO_WINDOW

_FONT = cv2.FONT_HERSHEY_SIMPLEX

_COMBO_FLAVOR = [
    (2, "Nice combo!"),
    (4, "ON FIRE!"),
    (7, "UNSTOPPABLE!"),
    (10, "GODLIKE!"),
]

GAME_OVER_HINT = "R / SPACE = play again    ESC = menu    Q = quit"


class Popup:
    __slots__ = ("text", "x", "y", "life", "max_life", "color", "scale")

    def __init__(self, text, x, y, color, scale, lifetime):
        self.text = text
        self.x = x
        self.y = y
        self.life = lifetime
        self.max_life = lifetime
        self.color = color
        self.scale = scale


def spawn_popup(popups, text, x, y, color=(255, 255, 255), scale=0.8, lifetime=0.8):
    popups.append(Popup(text, x, y, color, scale, lifetime))


def update_popups(popups, dt, ui=1.0):
    for p in popups:
        p.y -= 40 * ui * dt
        p.life -= dt
    popups[:] = [p for p in popups if p.life > 0]


def draw_popups(frame, popups):
    for p in popups:
        engine_hud.draw_popup(frame, p.x, p.y, p.text, p.color, scale=p.scale,
                              life=max(0.0, p.life / p.max_life))


def _combo_flavor(combo):
    label = ""
    for threshold, text in _COMBO_FLAVOR:
        if combo >= threshold:
            label = text
    return label


def draw_hud(frame, score, time_left, now, best, shield=None, frenzy=None):
    h, w = frame.shape[:2]
    s = ui_scale(h)

    draw_score(frame, score.total)
    draw_stats(frame, [f"Best: {best}"])

    timer_color = (0, 0, 255) if time_left <= 10 else (255, 255, 255)
    timer_text = f"Time: {int(time_left) + 1}s" if time_left > 0 else "Time: 0s"
    draw_text(frame, timer_text, (w - 30 * s, 45 * s), scale=1.0, color=timer_color,
              thickness=2, align="right")

    # combo: only while it is actually still alive, with a draining timer bar
    if score.combo >= 2 and score.is_combo_active(now):
        flavor = _combo_flavor(score.combo)
        text = f"Combo x{score.current_multiplier()}  ({score.combo} in a row)"
        if flavor:
            text += f"  {flavor}"
        draw_text(frame, text, (20 * s, h - 75 * s), scale=0.7, color=(0, 200, 255),
                  thickness=2)
        frac = score.combo_time_left(now) / COMBO_WINDOW
        bar_w = int(240 * s * frac)
        if bar_w > 0:
            y = h - int(66 * s)
            cv2.rectangle(frame, (int(20 * s), y), (int(20 * s) + bar_w, y + max(2, int(5 * s))),
                          (0, 200, 255), -1)

    draw_hints(frame)

    if shield is not None and shield.has_charge():
        draw_shield_icon(frame, w - 46 * s, 100 * s, s)

    if frenzy is not None and frenzy.is_active:
        draw_frenzy_banner(frame, frenzy)


def draw_shield_icon(frame, x, y, s=1.0):
    size = 16 * s
    pts = [
        (x, y - size),
        (x + size, y - size / 2),
        (x + size * 0.7, y + size),
        (x, y + size * 1.3),
        (x - size * 0.7, y + size),
        (x - size, y - size / 2),
    ]
    pts = [(int(px), int(py)) for px, py in pts]
    for i in range(len(pts)):
        cv2.line(frame, pts[i], pts[(i + 1) % len(pts)], (210, 170, 90),
                 max(1, round(2 * s)), cv2.LINE_AA)
    draw_text(frame, "Shield ready", (x - 24 * s, y + 8 * s), scale=0.5,
              color=(210, 170, 90), thickness=1, align="right")


def draw_frenzy_banner(frame, frenzy):
    h = frame.shape[0]
    s = ui_scale(h)
    wobble = 0.5 + 0.5 * ((frenzy.time_remaining * 6) % 1.0)
    scale = 1.2 + 0.15 * wobble
    draw_center_text(frame, "BUBBLE FRENZY!", 115 * s, scale=scale, color=(0, 120, 255),
                     thickness=3)


def draw_ready_countdown(frame, seconds_left):
    h = frame.shape[0]
    s = ui_scale(h)
    cv2.convertScaleAbs(frame, dst=frame, alpha=0.75)

    label = str(max(1, int(seconds_left) + 1)) if seconds_left > 0 else "POP!"
    draw_center_text(frame, label, h // 2 + 40 * s, scale=3.0, color=(0, 255, 255), thickness=6)
    draw_center_text(frame, "Pinch your thumb and index finger together on a bubble to pop it",
                     h // 2 + 100 * s, scale=0.7, thickness=2)
    draw_center_text(frame, "Avoid the bombs!   Both hands work.", h // 2 + 135 * s,
                     scale=0.7, color=COLOR_ACCENT, thickness=2)
    draw_center_text(frame, "Get your fingers ready...", h // 2 + 175 * s, scale=0.6,
                     color=COLOR_SECONDARY, thickness=1)


def draw_game_over(frame, score, best_line, progress=1.0, extra=None):
    engine_hud.draw_game_over(frame, score.total, message=best_line, progress=progress,
                              hint=GAME_OVER_HINT, extra=extra)