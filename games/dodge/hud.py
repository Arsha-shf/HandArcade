"""
games/dodge/hud.py

All on-screen text/overlays: live score, dodge count, and the game-over
screen. Styling now comes from engine/hud.py so it matches every other
game in the app -- this file just decides WHAT to show, not how it looks.
"""

import random

from engine.hud import draw_game_over as _draw_game_over
from engine.hud import draw_hints, draw_score, draw_stats

from .config import GAME_OVER_LINES


def pick_game_over_line():
    """Kept for backward compat in case game.py calls this directly."""
    return random.choice(GAME_OVER_LINES)


def draw_hud(frame, score, dodged, frame_count):
    draw_score(frame, score)
    draw_stats(frame, [f"Dodged: {dodged}"])
    draw_hints(frame)


def draw_game_over(frame, score, message=None):
    """message kept as an optional override; falls back to a random
    GAME_OVER_LINES pick if not given, same behavior as before."""
    _draw_game_over(frame, score, message=message, lines=GAME_OVER_LINES)