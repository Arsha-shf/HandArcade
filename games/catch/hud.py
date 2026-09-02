"""
games/catch/hud.py

All on-screen text/overlay drawing lives here: score, misses, combo,
catch popups, game-over screen. Kept separate from game.py so tuning the
look never touches game logic.
"""

import cv2

FONT = cv2.FONT_HERSHEY_SIMPLEX


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
    """Draws a '+N' / '-N' popup at a catch location. Call this every frame
    while the flash is alive -- game.py owns the timer (a list of
    [x, y, points, ttl]), this function just renders one frame of it."""
    color = (0, 220, 0) if points > 0 else (0, 0, 255)
    text = f"+{points}" if points > 0 else str(points)
    cv2.putText(frame, text, (int(x) - 15, int(y) - 30), FONT, 0.9, color, 2, cv2.LINE_AA)


def draw_game_over(frame, score):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    text = "GAME OVER"
    (tw, _), _ = cv2.getTextSize(text, FONT, 1.6, 3)
    cv2.putText(frame, text, ((w - tw) // 2, h // 2 - 30), FONT, 1.6, (0, 0, 255), 3, cv2.LINE_AA)

    score_text = f"Final Score: {score}"
    (tw2, _), _ = cv2.getTextSize(score_text, FONT, 1.0, 2)
    cv2.putText(frame, score_text, ((w - tw2) // 2, h // 2 + 20), FONT, 1.0, (255, 255, 255), 2, cv2.LINE_AA)

    hint = "r = retry    ESC = menu    q = quit"
    (tw3, _), _ = cv2.getTextSize(hint, FONT, 0.7, 2)
    cv2.putText(frame, hint, ((w - tw3) // 2, h // 2 + 65), FONT, 0.7, (200, 200, 200), 2, cv2.LINE_AA)