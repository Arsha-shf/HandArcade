"""
games/catch/hud.py

All on-screen text/overlay drawing lives here: score, misses, combo,
catch popups, game-over screen, paw rendering, and catch particles.
Kept separate from game.py so tuning the look never touches game logic.
"""

import math
import random

import cv2

from .paw import CATCH_TTL, Paw

FONT = cv2.FONT_HERSHEY_SIMPLEX

PAW_COLORS = [
    (0, 210, 255),
    (255, 90, 180),
]


def _ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def _ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    t = max(0.0, min(1.0, t))
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def draw_hud(frame, score, misses, max_misses, combo):
    h, w = frame.shape[:2]

    cv2.putText(frame, f"Score: {score}", (20, 40), FONT, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"Misses: {misses}/{max_misses}", (20, 75), FONT, 0.7, (0, 120, 255), 2, cv2.LINE_AA)

    if combo >= 3:
        text = f"Combo x{combo}!"
        (tw, _), _ = cv2.getTextSize(text, FONT, 1.1, 3)
        cv2.putText(frame, text, (w - tw - 20, 45), FONT, 1.1, (0, 215, 255), 3, cv2.LINE_AA)

    cv2.putText(frame, "ESC = menu    q = quit", (20, h - 15), FONT, 0.55, (200, 200, 200), 1, cv2.LINE_AA)

def draw_catch_flash(frame, x, y, points):
    color = (0, 220, 0) if points > 0 else (0, 0, 255)
    text = f"+{points}" if points > 0 else str(points)
    cv2.putText(frame, text, (int(x) - 15, int(y) - 30), FONT, 0.9, color, 2, cv2.LINE_AA)

def draw_game_over(frame, score, progress=1.0):
    """
    Game-over overlay. Pass `progress` from 0.0 (just triggered) up to 1.0
    while calling this every frame:
      - background dims in
      - "GAME OVER" drops in from above with a bounce/overshoot
      - final score counts up from 0 to its real value
      - hint fades in last
    progress=1.0 (default) renders fully settled.
    """
    h, w = frame.shape[:2]
    p = max(0.0, min(1.0, progress))

    dim_eased = _ease_out_cubic(min(1.0, p / 0.3))
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55 * dim_eased, frame, 1 - 0.55 * dim_eased, 0, frame)

    # Title: bounces/drops in from above (0% -> 45%)
    title_p = max(0.0, min(1.0, p / 0.45))
    if title_p > 0.0:
        bounce = _ease_out_back(title_p)
        text = "GAME OVER"
        scale = max(0.1, 1.6 * bounce)
        (tw, _), _ = cv2.getTextSize(text, FONT, scale, 3)
        y_offset = int((1.0 - min(1.0, title_p * 1.4)) * -80)
        title_layer = frame.copy()
        cv2.putText(title_layer, text, ((w - tw) // 2, h // 2 - 30 + y_offset), FONT, scale, (0, 0, 255), 3, cv2.LINE_AA)
        alpha = min(1.0, title_p * 2.0)
        cv2.addWeighted(title_layer, alpha, frame, 1 - alpha, 0, frame)

    # Score: counts up from 0 (35% -> 70%)
    score_p = max(0.0, min(1.0, (p - 0.35) / 0.35))
    if score_p > 0.0:
        score_eased = _ease_out_cubic(score_p)
        shown_score = int(score * score_eased) if score_p < 1.0 else score
        rest_layer = frame.copy()
        score_text = f"Final Score: {shown_score}"
        (tw2, _), _ = cv2.getTextSize(score_text, FONT, 1.0, 2)
        cv2.putText(rest_layer, score_text, ((w - tw2) // 2, h // 2 + 20), FONT, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.addWeighted(rest_layer, score_eased, frame, 1 - score_eased, 0, frame)

    # Hint: comes in last (60% -> 100%)
    hint_p = max(0.0, min(1.0, (p - 0.6) / 0.4))
    if hint_p > 0.02:
        hint_layer = frame.copy()
        hint = "r = retry    ESC = menu    q = quit"
        (tw3, _), _ = cv2.getTextSize(hint, FONT, 0.7, 2)
        cv2.putText(hint_layer, hint, ((w - tw3) // 2, h // 2 + 65), FONT, 0.7, (200, 200, 200), 2, cv2.LINE_AA)
        cv2.addWeighted(hint_layer, hint_p, frame, 1 - hint_p, 0, frame)

def draw_paw(frame, paw, base_radius):
    x, y = int(paw.x), int(paw.y)
    color = PAW_COLORS[paw.id % len(PAW_COLORS)]

    if paw.state == Paw.CATCH:
        progress = paw.catch_timer / CATCH_TTL
        r = int(base_radius * 0.5 * (1.0 + 0.5 * progress))
        cv2.circle(frame, (x, y), r, color, -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), r, (255, 255, 255), 2, cv2.LINE_AA)
        for a in range(0, 360, 60):
            rad = math.radians(a)
            x2 = int(x + (r + 14) * math.cos(rad))
            y2 = int(y + (r + 14) * math.sin(rad))
            cv2.line(frame, (x, y), (x2, y2), color, 3, cv2.LINE_AA)

    elif paw.state == Paw.SWIPE:
        speed = min(paw.speed(), 40)
        axis_major = int(base_radius * 0.6 + speed * 0.7)
        axis_minor = max(10, int(base_radius * 0.6 - speed * 0.15))
        cv2.ellipse(frame, (x, y), (axis_major, axis_minor), paw.angle, 0, 360, color, 2, cv2.LINE_AA)
        cv2.line(frame, (int(paw.prev_x), int(paw.prev_y)), (x, y), color, 2, cv2.LINE_AA)

    else:
        cv2.circle(frame, (x, y), int(base_radius * 0.85), color, 2, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 5, color, -1, cv2.LINE_AA)

def spawn_particles(x, y, color, count=10):
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.5, 6.5)
        particles.append({
            "x": float(x), "y": float(y),
            "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
            "ttl": random.randint(10, 18),
            "color": color,
        })
    return particles

def update_and_draw_particles(frame, particles):
    alive = []
    for p in particles:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.15
        p["ttl"] -= 1
        if p["ttl"] > 0:
            cv2.circle(frame, (int(p["x"]), int(p["y"])), 3, p["color"], -1, cv2.LINE_AA)
            alive.append(p)
    return alive