"""
games/fruit_slice/hud.py

On-screen score/lives display and the game-over overlay.
"""

import cv2

FONT = cv2.FONT_HERSHEY_SIMPLEX


def _ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def _ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    t = max(0.0, min(1.0, t))
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def draw_hud(frame, score, misses, max_misses, fps=None, difficulty=None):
    h, w = frame.shape[:2]
    cv2.putText(frame, f"Score: {score}", (20, 40),
                FONT, 0.9, (255, 255, 255), 2)

    life_text = "Lives: " + " ".join("X" for _ in range(max_misses - misses))
    cv2.putText(frame, life_text if life_text.strip() != "Lives:" else "Lives:",
                (w - 260, 40), FONT, 0.8, (100, 100, 255), 2)

    if fps is not None:
        cv2.putText(frame, f"FPS: {fps:.0f}", (20, 70),
                    FONT, 0.6, (0, 255, 0), 1)

    if difficulty is not None:
        cv2.putText(frame, difficulty.upper(), (w - 260, 70),
                    FONT, 0.6, (200, 200, 0), 1)

    cv2.putText(frame, "ESC = menu    q = quit", (20, h - 20),
                FONT, 0.55, (200, 200, 200), 1)


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
        (tw, th), _ = cv2.getTextSize(text, FONT, scale, 3)
        y_offset = int((1.0 - min(1.0, title_p * 1.4)) * -80)
        title_layer = frame.copy()
        cv2.putText(title_layer, text, ((w - tw) // 2, h // 2 - 40 + y_offset),
                    FONT, scale, (60, 60, 255), 3)
        alpha = min(1.0, title_p * 2.0)
        cv2.addWeighted(title_layer, alpha, frame, 1 - alpha, 0, frame)

    # Score: counts up from 0 (35% -> 70%)
    score_p = max(0.0, min(1.0, (p - 0.35) / 0.35))
    if score_p > 0.0:
        score_eased = _ease_out_cubic(score_p)
        shown_score = int(score * score_eased) if score_p < 1.0 else score
        rest_layer = frame.copy()
        score_text = f"Final Score: {shown_score}"
        (sw, sh), _ = cv2.getTextSize(score_text, FONT, 1.0, 2)
        cv2.putText(rest_layer, score_text, ((w - sw) // 2, h // 2 + 15),
                    FONT, 1.0, (255, 255, 255), 2)
        cv2.addWeighted(rest_layer, score_eased, frame, 1 - score_eased, 0, frame)

    # Hint: comes in last (60% -> 100%)
    hint_p = max(0.0, min(1.0, (p - 0.6) / 0.4))
    if hint_p > 0.02:
        hint_layer = frame.copy()
        hint = "Press any key for menu, q to quit"
        (hw, hh), _ = cv2.getTextSize(hint, FONT, 0.7, 1)
        cv2.putText(hint_layer, hint, ((w - hw) // 2, h // 2 + 60),
                    FONT, 0.7, (180, 180, 180), 1)
        cv2.addWeighted(hint_layer, hint_p, frame, 1 - hint_p, 0, frame)