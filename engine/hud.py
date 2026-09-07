"""
engine/hud.py

Shared HUD styling for every HandArcade game: score line, small stat line,
control hints, and the game-over screen. Centralizing this means every
game looks like it belongs to the same app instead of whoever wrote that
game's hud.py picking its own font size/color that day.

Each game's own hud.py should call into these instead of calling
cv2.putText directly for score/stats/game-over. Game-specific overlays
(combo meters, bomb warnings, whatever) can still live in the game's own
hud.py using cv2 directly -- this module only owns the parts that should
look identical everywhere.
"""

import random

import cv2

# --- Shared style constants -------------------------------------------------
FONT = cv2.FONT_HERSHEY_SIMPLEX

COLOR_PRIMARY = (255, 255, 255)     # main score text
COLOR_SECONDARY = (200, 200, 200)   # secondary stats
COLOR_HINT = (180, 180, 180)        # bottom control hints
COLOR_ACCENT = (0, 255, 255)        # menu highlights / titles
COLOR_DANGER = (60, 60, 255)        # "GAME OVER" red

SCORE_POS = (20, 40)
SCORE_SCALE = 0.9
SCORE_THICKNESS = 2

STAT_SCALE = 0.6
STAT_THICKNESS = 1
STAT_LINE_HEIGHT = 30  # vertical gap between stacked stat lines

HINT_SCALE = 0.55
HINT_THICKNESS = 1
HINT_MARGIN_BOTTOM = 20


def draw_score(frame, score, label="Score"):
    """Main score readout, top-left, in the shared house style."""
    cv2.putText(frame, f"{label}: {score}", SCORE_POS,
                FONT, SCORE_SCALE, COLOR_PRIMARY, SCORE_THICKNESS)


def draw_stats(frame, stats, start_y=70):
    """
    Secondary stat lines under the score, e.g. draw_stats(frame, ["Dodged: 3"]).
    Pass a list so games can show 0, 1, or several extra stats consistently.
    """
    for i, line in enumerate(stats):
        y = start_y + i * STAT_LINE_HEIGHT
        cv2.putText(frame, line, (20, y),
                    FONT, STAT_SCALE, COLOR_SECONDARY, STAT_THICKNESS)


def draw_hints(frame, text="ESC = menu   q = quit"):
    """Bottom-left control hint line, same spot/style in every game."""
    y = frame.shape[0] - HINT_MARGIN_BOTTOM
    cv2.putText(frame, text, (20, y),
                FONT, HINT_SCALE, COLOR_HINT, HINT_THICKNESS)


def draw_game_over(frame, score, message=None, lines=None, retry=True):
    """
    Standard game-over overlay: dim background, "GAME OVER", an optional
    flavor line (random pick from `lines` if `message` isn't given), final
    score, and the retry/menu/quit hint. Same layout for every game.
    """
    if message is None and lines:
        message = random.choice(lines)

    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    cv2.putText(frame, "GAME OVER", (w // 2 - 150, h // 2 - 60),
                FONT, 1.4, COLOR_DANGER, 3)

    if message:
        cv2.putText(frame, message, (w // 2 - len(message) * 6, h // 2 - 10),
                    FONT, 0.7, COLOR_PRIMARY, 2)

    cv2.putText(frame, f"Final score: {score}", (w // 2 - 100, h // 2 + 30),
                FONT, 0.8, COLOR_PRIMARY, 2)

    hint = "SPACE = retry   ESC = menu   q = quit" if retry else "ESC = menu   q = quit"
    cv2.putText(frame, hint, (w // 2 - len(hint) * 3, h // 2 + 70),
                FONT, 0.6, COLOR_SECONDARY, 1)