"""
games/fruit_slice/hud.py

On-screen score/lives display and the game-over overlay.
"""

import cv2


def draw_hud(frame, score, misses, max_misses):
    h, w = frame.shape[:2]
    cv2.putText(frame, f"Score: {score}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

    life_text = "Lives: " + " ".join("X" for _ in range(max_misses - misses))
    cv2.putText(frame, life_text if life_text.strip() != "Lives:" else "Lives:",
                (w - 260, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 255), 2)

    cv2.putText(frame, "ESC = menu    q = quit", (20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)


def draw_game_over(frame, score):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    text = "GAME OVER"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.6, 3)
    cv2.putText(frame, text, ((w - tw) // 2, h // 2 - 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.6, (60, 60, 255), 3)

    score_text = f"Final Score: {score}"
    (sw, sh), _ = cv2.getTextSize(score_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
    cv2.putText(frame, score_text, ((w - sw) // 2, h // 2 + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    hint = "Press any key for menu, q to quit"
    (hw, hh), _ = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)
    cv2.putText(frame, hint, ((w - hw) // 2, h // 2 + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1)      